# webserver.py - ПОЛНЫЙ ИСПРАВЛЕННЫЙ КОД
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import json
import sqlite3
import uvicorn
import os
import csv
import sys
from io import StringIO
from typing import List, Optional

# КОНСТАНТЫ
DB_NAME = 'sensor_data.db'
HOST = "0.0.0.0"
PORT = 8000

# Модели
class ChatRequest(BaseModel):
    message: str

class SettingsRequest(BaseModel):
    temperature: dict
    pressure: dict
    vibration: dict

class ProfileRequest(BaseModel):
    fullName: str
    email: str
    phone: str
    department: str
    position: str

class AIRecommendationRequest(BaseModel):
    message: str
    type: str = "info"
    parameters: dict = {}

app = FastAPI(title="Пром Мониторинг")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# AI модуль
try:
    current_dir = os.path.dirname(__file__)
    base_dir = os.path.dirname(current_dir)
    ai_path = os.path.join(base_dir, 'AI')
    
    sys.path.insert(0, ai_path)
    
    from simple_ai import get_recommendation
    AI_AVAILABLE = True
    print(f"✅ AI модуль загружен из: {ai_path}")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI модуль недоступен: {e}")
    print("ℹ️  Проверьте наличие файла simple_ai.py в папке ../AI")

# WebSocket менеджер
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
    conn = sqlite3.connect(DB_NAME)
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
            hits_per_minute REAL DEFAULT 0
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
    
    # Проверяем, есть ли колонка parameters, если нет - добавляем
    cursor.execute("PRAGMA table_info(ai_recommendations)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'parameters' not in columns:
        print("⚠️ Добавляем колонку 'parameters' в таблицу ai_recommendations...")
        cursor.execute('ALTER TABLE ai_recommendations ADD COLUMN parameters TEXT DEFAULT "{}"')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter TEXT UNIQUE,
            value TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            department TEXT,
            position TEXT
        )
    ''')
    
    # Начальные настройки
    default_settings = [
        ('temperature_min', '20'),
        ('temperature_max', '75'),
        ('temperature_critical', '80'),
        ('pressure_min', '5'),
        ('pressure_max', '10'),
        ('pressure_critical', '12'),
        ('vibration_min', '0'),
        ('vibration_max', '6'),
        ('vibration_critical', '8')
    ]
    
    for param, value in default_settings:
        cursor.execute('INSERT OR IGNORE INTO settings (parameter, value) VALUES (?, ?)', (param, value))
    
    cursor.execute('''
        INSERT OR IGNORE INTO profiles (full_name, email, phone, department, position) 
        VALUES (?, ?, ?, ?, ?)
    ''', ('Иван Петров', 'ivan.petrov@company.ru', '+7 (495) 123-45-67', 'Производственный отдел', 'Инженер по оборудованию'))
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

@app.on_event("startup")
async def startup_event():
    init_database()
    print(f"🚀 Сервер запущен на http://localhost:{PORT}")
    print(f"⚡ WebSocket: ws://localhost:{PORT}/ws")
    print(f"🤖 AI: {'✅ Доступен' if AI_AVAILABLE else '❌ Недоступен'}")

# Статические файлы
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "static")
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_dashboard():
    """Главная страница"""
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        print(f"❌ Ошибка загрузки dashboard.html: {e}")
        return HTMLResponse("<h1>Пром Мониторинг</h1><p>Ошибка загрузки интерфейса</p>")

# API эндпоинты
@app.post("/api/data")
async def receive_data(data: dict):
    """Прием данных от Arduino"""
    try:
        sensor_data = data.get('data', {})
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_data (timestamp, temperature, humidity, hit_count, hits_per_minute)
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
        
        await manager.broadcast(json.dumps({
            'type': 'realtime',
            'data': sensor_data,
            'timestamp': datetime.now().isoformat()
        }))
        
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Ошибка приема данных: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    """Обработка AI чата"""
    try:
        user_message = request.message
        
        # Получаем последние данные сенсоров
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT temperature, humidity, hit_count, hits_per_minute FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            temperature = row["temperature"] or 0.0
            humidity = row["humidity"] or 0.0
            hit_count = row["hit_count"] or 0
            hits_per_minute = row["hits_per_minute"] or 0.0
            
            # Используем AI для анализа
            if AI_AVAILABLE:
                ai_result = get_recommendation(temperature, humidity, hit_count)
                response_message = ai_result.get('ai_message', '🤖 Нет рекомендаций')
            else:
                # Запасные ответы
                responses = [
                    f"📊 Текущие показатели: температура {temperature:.1f}°C, влажность {humidity:.1f}%, вибрации {hits_per_minute:.1f} уд/мин",
                    "✅ Система работает нормально. Все параметры в пределах нормы.",
                    "🔍 Рекомендую продолжить мониторинг оборудования.",
                    "📈 Нет критических отклонений в работе системы.",
                    f"🌡️ Температура в норме: {temperature:.1f}°C",
                    f"💧 Влажность оптимальна: {humidity:.1f}%",
                    "⚙️ Проверьте состояние оборудования согласно графику ТО.",
                    "📋 Все системы функционируют в штатном режиме."
                ]
                import random
                response_message = random.choice(responses)
        else:
            response_message = "📡 Данные датчиков отсутствуют. Проверьте подключение Arduino."
        
        # Сохраняем в базу как рекомендацию
        await add_ai_recommendation({
            "timestamp": datetime.now().isoformat(),
            "message": f"💬 Пользователь: {user_message}\n🤖 AI: {response_message}",
            "type": "chat",
            "parameters": json.dumps({"user_message": user_message, "response": response_message})
        })
        
        return {"status": "success", "response": response_message}
        
    except Exception as e:
        print(f"❌ Ошибка AI чата: {e}")
        return {"status": "error", "message": str(e)}

async def add_ai_recommendation(data):
    """Добавление AI рекомендации"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO ai_recommendations (timestamp, message, type, parameters) VALUES (?, ?, ?, ?)',
                      (data.get("timestamp", datetime.now().isoformat()),
                       data.get("message", ""),
                       data.get("type", "info"),
                       data.get("parameters", "{}")))
        
        conn.commit()
        conn.close()
        
        # Рассылаем через WebSocket
        await manager.broadcast(json.dumps({
            "type": "ai_recommendation",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
        
    except Exception as e:
        print(f"❌ Ошибка добавления рекомендации: {e}")

@app.post("/api/ai/add_recommendation")
async def add_recommendation(request: AIRecommendationRequest):
    """Добавление AI рекомендации (для main.py)"""
    try:
        await add_ai_recommendation({
            "timestamp": datetime.now().isoformat(),
            "message": request.message,
            "type": request.type,
            "parameters": json.dumps(request.parameters)
        })
        return {"status": "success", "message": "Recommendation added"}
    except Exception as e:
        print(f"❌ Ошибка добавления рекомендации: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/ai/recommendations")
async def get_ai_recommendations(limit: int = Query(10, ge=1, le=100)):
    """Получение последних AI рекомендаций"""
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
        print(f"❌ Ошибка получения AI рекомендаций: {e}")
        return []

@app.get("/api/current")
async def get_current_data():
    """Текущие данные"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "timestamp": row["timestamp"],
            "temperature": row["temperature"] or 0.0,
            "humidity": row["humidity"] or 0.0,
            "hit_count": row["hit_count"] or 0,
            "hits_per_minute": row["hits_per_minute"] or 0.0
        }
    return {"message": "Нет данных"}

@app.get("/api/history")
async def get_history(hours: int = Query(1, ge=1, le=24)):
    """История данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, temperature, humidity, hit_count, hits_per_minute
            FROM sensor_data 
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp ASC
            LIMIT 500
        ''', (f'-{hours} hours',))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"] or 0.0,
                "humidity": row["humidity"] or 0.0,
                "hit_count": row["hit_count"] or 0,
                "hits_per_minute": row["hits_per_minute"] or 0.0
            })
        
        return history
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        return []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Отправляем приветственное сообщение
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "✅ Подключено к серверу мониторинга",
            "timestamp": datetime.now().isoformat()
        }))
        
        while True:
            # Ждем сообщения (хотя мы их не обрабатываем, но нужно для поддержания соединения)
            await websocket.receive_text()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("🔌 WebSocket отключен")
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
        manager.disconnect(websocket)

@app.post("/api/save_settings")
async def save_settings(request: SettingsRequest):
    """Сохранение настроек"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Сохраняем настройки температуры
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_min', request.temperature.get('min', '20')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_max', request.temperature.get('max', '75')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_critical', request.temperature.get('critical', '80')))
        
        # Сохраняем настройки давления
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_min', request.pressure.get('min', '5')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_max', request.pressure.get('max', '10')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_critical', request.pressure.get('critical', '12')))
        
        # Сохраняем настройки вибрации
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('vibration_min', request.vibration.get('min', '0')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('vibration_max', request.vibration.get('max', '6')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('vibration_critical', request.vibration.get('critical', '8')))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Настройки успешно сохранены"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/get_settings")
async def get_settings():
    """Получение настроек"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT parameter, value FROM settings')
        rows = cursor.fetchall()
        conn.close()
        
        settings = {}
        for row in rows:
            settings[row["parameter"]] = row["value"]
        
        return {"status": "success", "settings": settings}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/save_profile")
async def save_profile(request: ProfileRequest):
    """Сохранение профиля"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE profiles SET 
            full_name=?, email=?, phone=?, department=?, position=?
            WHERE id=1
        ''', (request.fullName, request.email, request.phone, request.department, request.position))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Профиль успешно сохранен"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/get_profile")
async def get_profile():
    """Получение профиля"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT full_name, email, phone, department, position FROM profiles WHERE id=1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "status": "success",
                "profile": {
                    "fullName": row["full_name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "department": row["department"],
                    "position": row["position"]
                }
            }
        else:
            return {"status": "error", "message": "Профиль не найден"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка CSV файла"""
    try:
        contents = await file.read()
        csv_text = contents.decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        imported_count = 0
        
        for row in rows[1:]:  # Пропускаем заголовок
            if len(row) >= 5:
                try:
                    cursor.execute('''
                        INSERT INTO sensor_data (timestamp, temperature, humidity, hits_per_minute, hit_count)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (row[0], float(row[1] or 0), float(row[2] or 0), float(row[3] or 0), int(row[4] or 0)))
                    imported_count += 1
                except:
                    continue
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Загружено {imported_count} строк"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/status")
async def get_status():
    """Статус системы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM sensor_data')
    data_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM ai_recommendations')
    ai_count = cursor.fetchone()[0]
    conn.close()
    
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "websocket_connections": len(manager.active_connections),
        "ai_available": AI_AVAILABLE,
        "data_records": data_count,
        "ai_recommendations": ai_count,
        "version": "5.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)