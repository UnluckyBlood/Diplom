from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import json
import sqlite3
import uvicorn

app = FastAPI(title="Arduino Monitoring System")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            ai_recommendation TEXT
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
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Arduino Monitoring</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            .card { background: #f0f0f0; padding: 20px; margin: 10px; border-radius: 10px; }
            .value { font-size: 36px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Arduino Monitoring System</h1>
        <div class="card">
            <div>Температура:</div>
            <div class="value" id="temp">-- °C</div>
        </div>
        <div class="card">
            <div>Влажность:</div>
            <div class="value" id="hum">-- %</div>
        </div>
        <div>Статус: <span id="status">Подключение...</span></div>
        <script>
            async function updateData() {
                try {
                    const response = await fetch('/api/current');
                    const data = await response.json();
                    
                    if (data.temperature) {
                        document.getElementById('temp').textContent = data.temperature + ' °C';
                    }
                    if (data.humidity) {
                        document.getElementById('hum').textContent = data.humidity + ' %';
                    }
                    document.getElementById('status').textContent = 'Обновлено: ' + new Date().toLocaleTimeString();
                } catch (e) {
                    document.getElementById('status').textContent = 'Ошибка подключения';
                }
            }
            
            // Обновляем каждые 2 секунды
            setInterval(updateData, 2000);
            updateData();
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

if __name__ == "__main__":
    print("🚀 Запуск Arduino Monitoring System...")
    print("🌐 Веб-интерфейс: http://localhost:8000")
    print("⚡ WebSocket: ws://localhost:8000/ws")
    print("\nДля остановки нажмите Ctrl+C\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
