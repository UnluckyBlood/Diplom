from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timedelta
import json
import sqlite3
import uvicorn
import sys
import os

app = FastAPI(title="Arduino Monitoring System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI модуль
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'AI'))
    from simple_ai import get_recommendation
    AI_AVAILABLE = True
    print("✅ AI модуль загружен")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI модуль недоступен: {e}")

# Менеджер WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
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

# БД
def get_db_connection():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            hit_count INTEGER DEFAULT 0,
            hits_per_minute REAL DEFAULT 0,
            ai_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            type TEXT,
            parameters TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_recommendations_timestamp ON ai_recommendations(timestamp)')
    
    conn.commit()
    conn.close()
    print("✅ БД инициализирована")

@app.on_event("startup")
async def startup_event():
    init_database()
    print("🚀 Система мониторинга запущена")

@app.get("/")
async def get_dashboard():
    """Главная страница"""
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except:
        return HTMLResponse("""
        <html><body><h1>Arduino Monitoring System</h1>
        <p>Дашборд загружается...</p>
        <script>setTimeout(() => location.reload(), 2000);</script>
        </body></html>
        """)

@app.post("/api/data")
async def receive_data(data: dict):
    """Прием данных от Arduino"""
    try:
        if data.get('type') == 'realtime':
            sensor_data = data.get('data', {})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sensor_data 
                (timestamp, temperature, humidity, hit_count, hits_per_minute)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                sensor_data.get('timestamp'),
                sensor_data.get('temperature'),
                sensor_data.get('humidity'),
                sensor_data.get('hit_count', 0),
                sensor_data.get('hits_per_minute', 0)
            ))
            
            conn.commit()
            conn.close()
            
            # Рассылаем через WebSocket
            await manager.broadcast(json.dumps({
                'type': 'realtime',
                'data': sensor_data,
                'timestamp': datetime.now().isoformat()
            }))
            
            return {"status": "success", "message": "Data received"}
        
        return {"status": "error", "message": "Invalid format"}
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/add_recommendation")
async def add_ai_recommendation(data: dict):
    """Добавление AI рекомендации"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_recommendations 
            (timestamp, message, type, parameters)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get("timestamp", datetime.now().isoformat()),
            data.get("message", ""),
            data.get("type", "info"),
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
        
        return {"status": "success", "message": "Recommendation added"}
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/current")
async def get_current_data():
    """Текущие данные"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, temperature, humidity, hit_count, hits_per_minute
            FROM sensor_data 
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "timestamp": row["timestamp"],
                "temperature": row["temperature"] or 0,
                "humidity": row["humidity"] or 0,
                "hit_count": row["hit_count"] or 0,
                "hits_per_minute": row["hits_per_minute"] or 0
            }
        else:
            return {
                "message": "No data",
                "timestamp": datetime.now().isoformat(),
                "temperature": 0,
                "humidity": 0,
                "hit_count": 0,
                "hits_per_minute": 0
            }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/history")
async def get_history(hours: int = 1):
    """История"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, temperature, humidity, hits_per_minute
            FROM sensor_data 
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (f'-{hours} hours',))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"] or 0,
                "humidity": row["humidity"] or 0,
                "hits_per_minute": row["hits_per_minute"] or 0
            })
        
        return history
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

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
            await websocket.receive_text()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
        manager.disconnect(websocket)

@app.get("/api/ai/recommendations")
async def get_ai_recommendations(limit: int = 5):
    """AI рекомендации (последние 5)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, message, type, parameters
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
                "parameters": json.loads(row["parameters"]) if row["parameters"] else {}
            })
        
        return recommendations
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

@app.get("/api/status")
async def get_status():
    """Статус системы"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "websocket_connections": len(manager.active_connections),
        "ai_available": AI_AVAILABLE
    }

if __name__ == "__main__":
    print("🚀 Запуск системы...")
    print("🌐 http://localhost:8000")
    print("⚡ WebSocket: ws://localhost:8000/ws")
    print(f"🤖 AI: {'✅ Доступен' if AI_AVAILABLE else '❌ Недоступен'}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)