from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import json
import sqlite3
import uvicorn
import sys
import os

app = FastAPI(title="Arduino Monitoring System")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавьте путь к AI модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'AI'))

try:
    from simple_ai import get_recommendation
    AI_AVAILABLE = True
    print("✅ AI модуль загружен")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI модуль недоступен: {e}")

# Менеджер WebSocket подключений
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket подключен. Всего: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WebSocket отключен. Осталось: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Подключение к БД
def get_db_connection():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            hit_detected INTEGER DEFAULT 0,
            hit_interval INTEGER,
            hit_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS five_min_avg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            avg_temperature REAL,
            avg_humidity REAL,
            total_hits INTEGER,
            ai_recommendation TEXT,
            ai_confidence REAL,
            ai_class INTEGER
        )
    ''')
    
    # НОВАЯ ТАБЛИЦА для AI рекомендаций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            type TEXT,
            confidence REAL,
            parameters TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

@app.on_event("startup")
async def startup_event():
    init_database()
    print("🚀 Система мониторинга запущена")

@app.get("/")
async def get_dashboard():
    """Главная страница дашборда"""
    try:
        # dashboard.html в той же папке
        dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(html_content)
    except Exception as e:
        print(f"❌ Ошибка загрузки dashboard: {e}")
        # Fallback на простую страницу
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Arduino Monitoring</title>
        </head>
        <body>
            <h1>Arduino Monitoring System</h1>
            <p>Dashboard загружается...</p>
            <script>
                setTimeout(() => location.reload(), 2000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html_content)

@app.post("/api/data")
async def receive_data(data: dict):
    """Прием данных от Arduino"""
    print(f"📥 Получены данные: {data}")
    
    try:
        # Сохраняем в БД
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if data.get('type') == 'realtime':
            sensor_data = data.get('data', {})
            cursor.execute('''
                INSERT INTO sensor_data 
                (timestamp, temperature, humidity, hit_detected, hit_interval, hit_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                sensor_data.get('timestamp'),
                sensor_data.get('temperature'),
                sensor_data.get('humidity'),
                sensor_data.get('hit_detected', 0),
                sensor_data.get('hit_interval', 0),
                sensor_data.get('hit_count', 0)
            ))
        
        conn.commit()
        conn.close()
        
        # Рассылаем через WebSocket
        await manager.broadcast(json.dumps(data))
        
        return {"status": "success", "message": "Data received"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/current")
async def get_current_data():
    """Получение текущих данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, temperature, humidity, hit_count
            FROM sensor_data 
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "timestamp": row["timestamp"],
                "temperature": row["temperature"],
                "humidity": row["humidity"],
                "hit_count": row["hit_count"]
            }
        else:
            return {"message": "No data available"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/history")
async def get_history(hours: int = 1):
    """Получение истории данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, temperature, humidity
            FROM sensor_data 
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{hours} hours',))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected",
            "timestamp": datetime.now().isoformat()
        }))
        
        while True:
            data = await websocket.receive_text()
            # Эхо-ответ
            await websocket.send_text(json.dumps({
                "type": "echo",
                "message": f"Received: {data}",
                "timestamp": datetime.now().isoformat()
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/status")
async def get_status():
    """Получение статуса системы"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "websocket_connections": len(manager.active_connections),
        "version": "2.0"
    }

@app.get("/api/ai/recommendations")
async def get_ai_recommendations(limit: int = 10):
    """Получение AI рекомендаций"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, message, type, confidence, parameters
            FROM ai_recommendations
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        recommendations = []
        for row in rows:
            recommendations.append({
                "timestamp": row["timestamp"],
                "message": row["message"],
                "type": row["type"],
                "confidence": row["confidence"],
                "parameters": json.loads(row["parameters"]) if row["parameters"] else {}
            })
        
        return recommendations
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/add_recommendation")
async def add_ai_recommendation(data: dict):
    """Добавление AI рекомендации"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_recommendations 
            (timestamp, message, type, confidence, parameters)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get("timestamp", datetime.now().isoformat()),
            data.get("message", ""),
            data.get("type", "info"),
            data.get("confidence", 0.5),
            json.dumps(data.get("parameters", {}))
        ))
        
        conn.commit()
        conn.close()
        
        # Рассылаем через WebSocket
        await manager.broadcast(json.dumps({
            "type": "ai_recommendation",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ai/analyze")
async def analyze_current():
    """Анализ текущих данных с помощью AI"""
    try:
        if not AI_AVAILABLE:
            return {"status": "error", "message": "AI module not available"}
        
        # Получаем последние данные
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT temperature, humidity, hit_count
            FROM sensor_data 
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            temperature = row["temperature"] or 0
            humidity = row["humidity"] or 0
            hits = row["hit_count"] or 0
            
            # Получаем рекомендации от AI
            result = get_recommendation(temperature, humidity, hits)
            
            # Сохраняем в БД
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ai_recommendations 
                (timestamp, message, type, confidence, parameters)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                " | ".join(result['recommendations'][:2]),
                "warning" if result['prediction_class'] > 0 else "info",
                result['confidence'],
                json.dumps({
                    "temperature": temperature,
                    "humidity": humidity,
                    "hits": hits,
                    "failure_risk": result['failure_risk']
                })
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "status": "success",
                "analysis": result,
                "current_data": {
                    "temperature": temperature,
                    "humidity": humidity,
                    "hits": hits
                }
            }
        else:
            return {"status": "error", "message": "No data available"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("🚀 Запуск Arduino Monitoring System...")
    print("🌐 Веб-интерфейс: http://localhost:8000")
    print("⚡ WebSocket: ws://localhost:8000/ws")
    print("🤖 AI анализ доступен")
    print("\nДля остановки нажмите Ctrl+C\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)