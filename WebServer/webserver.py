from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import json
import sqlite3
import asyncio
import uvicorn
from typing import List, Optional
import os

app = FastAPI(title="Arduino Monitoring System with AI")

# Подключаем статические файлы
os.makedirs("WebServer/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="WebServer/static"), name="static")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище AI рекомендаций для чата
ai_recommendations_history = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
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
    """Инициализация базы данных с таблицами для истории"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица для реальных данных
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
    
    # Таблица для 5-минутных средних
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS five_min_avg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            avg_temperature REAL,
            avg_humidity REAL,
            total_hits INTEGER,
            ai_recommendation TEXT,
            ai_confidence REAL
        )
    ''')
    
    # Таблица для AI рекомендаций (чат)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            message_type TEXT, -- 'warning', 'info', 'danger', 'recommendation'
            parameters TEXT  -- JSON с данными на момент рекомендации
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
    return HTMLResponse(open("WebServer/dashboard.html", encoding="utf-8").read())

# API endpoints остаются примерно такими же, но добавляем новые

@app.get("/api/ai/recommendations")
async def get_ai_recommendations(limit: int = 20):
    """Получение истории AI рекомендаций"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, message, message_type, parameters
        FROM ai_chat
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
            "type": row["message_type"],
            "parameters": json.loads(row["parameters"]) if row["parameters"] else {}
        })
    
    return recommendations

@app.post("/api/ai/add_recommendation")
async def add_ai_recommendation(recommendation: dict):
    """Добавление AI рекомендации в чат"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_chat (timestamp, message, message_type, parameters)
            VALUES (?, ?, ?, ?)
        ''', (
            recommendation.get("timestamp", datetime.now().isoformat()),
            recommendation.get("message", ""),
            recommendation.get("type", "info"),
            json.dumps(recommendation.get("parameters", {}))
        ))
        
        conn.commit()
        conn.close()
        
        # Рассылаем через WebSocket
        await manager.broadcast(json.dumps({
            "type": "ai_recommendation",
            "data": recommendation
        }))
        
        return {"status": "success"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Остальные endpoints (api/data, api/current, api/history, /ws) остаются

if __name__ == "__main__":
    print("🚀 Запуск Arduino Monitoring System with AI...")
    print("🌐 Веб-интерфейс: http://localhost:8000")
    print("🤖 AI рекомендации доступны в чате")
    uvicorn.run(app, host="0.0.0.0", port=8000)