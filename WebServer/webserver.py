from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import json
import sqlite3
import asyncio
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
        print(f"WebSocket подключен. Всего: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket отключен. Осталось: {len(self.active_connections)}")
    
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

@app.get("/")
async def get_dashboard():
    """Главная страница дашборда"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Arduino Monitoring</title>
        <script>
            let ws;
            
            function initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    console.log('WebSocket подключен');
                    document.getElementById('status').textContent = 'Подключено';
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        updateDashboard(data);
                    } catch (e) {
                        console.error('Ошибка парсинга:', e);
                    }
                };
                
                ws.onclose = function() {
                    console.log('WebSocket отключен');
                    document.getElementById('status').textContent = 'Отключено';
                    setTimeout(initWebSocket, 3000);
                };
            }
            
            function updateDashboard(data) {
                if (data.type === 'realtime' && data.data.temperature) {
                    document.getElementById('temp').textContent = data.data.temperature.toFixed(1);
                    document.getElementById('hum').textContent = data.data.humidity?.toFixed(1) || '--';
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                }
            }
            
            window.onload = function() {
                initWebSocket();
                setInterval(updateTime, 1000);
            };
            
            function updateTime() {
                document.getElementById('currentTime').textContent = new Date().toLocaleTimeString();
            }
        </script>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .card {
                background: white;
                padding: 20px;
                margin: 10px 0;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .value {
                font-size: 2em;
                font-weight: bold;
                color: #333;
            }
            .label {
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Arduino Monitoring System</h1>
        
        <div class="card">
            <div class="label">Статус:</div>
            <div id="status">Подключение...</div>
            <div class="label">Текущее время:</div>
            <div id="currentTime">--:--:--</div>
        </div>
        
        <div class="card">
            <div class="label">Температура:</div>
            <div class="value" id="temp">--</div>
            <div class="label">°C</div>
        </div>
        
        <div class="card">
            <div class="label">Влажность:</div>
            <div class="value" id="hum">--</div>
            <div class="label">%</div>
        </div>
        
        <div class="card">
            <div class="label">Последнее обновление:</div>
            <div id="lastUpdate">--:--:--</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.post("/api/data")
async def receive_data(data: dict):
    """Прием данных от Python-скрипта"""
    try:
        # Сохранение в БД
        conn = get_db_connection()
        cursor = conn.cursor()
        
        data_type = data.get('type')
        
        if data_type == 'realtime':
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
        
        elif data_type == '5min_avg':
            cursor.execute('''
                INSERT INTO five_min_avg 
                (timestamp, avg_temperature, avg_humidity, total_hits, ai_recommendation)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('avg_temperature'),
                data.get('avg_humidity'),
                data.get('total_hits'),
                json.dumps({
                    'recommendations': data.get('ai_recommendations', []),
                    'confidence': data.get('ai_confidence', 0)
                })
            ))
        
        conn.commit()
        conn.close()
        
        # Рассылка через WebSocket
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
            WHERE temperature IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
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
        # Отправляем начальные данные
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Ожидание сообщений
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
        "websocket_connections": len(manager.active_connections)
    }

if __name__ == "__main__":
    print("🚀 Запуск Arduino Monitoring System...")
    print("🌐 Веб-интерфейс: http://localhost:8000")
    print("⚡ WebSocket: ws://localhost:8000/ws")
    print("\nДля остановки нажмите Ctrl+C\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
