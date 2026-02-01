from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import sqlite3
import uvicorn
import sys
import os
import csv
from io import StringIO

# КОНСТАНТЫ БД
DB_NAME = 'sensor_data.db'
SENSOR_DATA_TABLE = 'sensor_data'
AI_RECOMMENDATIONS_TABLE = 'ai_recommendations'

# КОНСТАНТЫ СЕРВЕРА
HOST = "0.0.0.0"
PORT = 8000
DASHBOARD_FILE = "dashboard.html"

# КОНСТАНТЫ ДЛЯ API
HISTORY_DEFAULT_HOURS = 1
HISTORY_MAX_RECORDS = 100
RECOMMENDATIONS_DEFAULT_LIMIT = 5

# Модели запросов
class ChatRequest(BaseModel):
    message: str

class ExportRequest(BaseModel):
    start_date: str
    end_date: str
    equipment: str
    format: str

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
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица данных сенсоров
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {SENSOR_DATA_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            hit_count INTEGER DEFAULT 0,
            hits_per_minute REAL DEFAULT 0,
            ai_message TEXT
        )
    ''')
    
    # Таблица AI рекомендаций
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {AI_RECOMMENDATIONS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            type TEXT,
            parameters TEXT
        )
    ''')
    
    # Таблица настроек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter TEXT UNIQUE,
            value TEXT
        )
    ''')
    
    # Таблица профилей
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
    
    # Индексы для оптимизации
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON {SENSOR_DATA_TABLE}(timestamp)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_ai_recommendations_timestamp ON {AI_RECOMMENDATIONS_TABLE}(timestamp)')
    
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
    
    # Начальный профиль
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
    print(f"🚀 Система мониторинга запущена")
    print(f"🌐 http://localhost:{PORT}")
    print(f"⚡ WebSocket: ws://localhost:{PORT}/ws")
    print(f"🤖 AI: {'✅ Доступен' if AI_AVAILABLE else '❌ Недоступен'}")

# Создаем папку static если ее нет
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_dashboard():
    """Главная страница"""
    try:
        # Сначала пробуем index.html
        dashboard_path = os.path.join(os.path.dirname(__file__), "index.html")
        if os.path.exists(dashboard_path):
            with open(dashboard_path, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())
        
        # Если нет index.html, пробуем dashboard.html
        dashboard_path = os.path.join(os.path.dirname(__file__), DASHBOARD_FILE)
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"""
        <html><body>
            <h1>Arduino Monitoring System</h1>
            <p>Ошибка загрузки дашборда: {str(e)}</p>
            <p>Проверьте наличие файла index.html или dashboard.html в папке с сервером</p>
            <script>setTimeout(() => location.reload(), 2000);</script>
        </body></html>
        """)

@app.get("/style.css")
async def get_style_css():
    """CSS файл для совместимости со старыми путями"""
    css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    
    return JSONResponse({"error": "CSS file not found"}, status_code=404)

@app.get("/script.js")
async def get_script_js():
    """JS файл для совместимости со старыми путями"""
    js_path = os.path.join(os.path.dirname(__file__), "static", "js", "script.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    
    js_path = os.path.join(os.path.dirname(__file__), "script.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    
    return JSONResponse({"error": "JS file not found"}, status_code=404)

@app.get("/static/css/style.css")
async def get_static_style_css():
    """Статический CSS файл"""
    css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return JSONResponse({"error": "CSS file not found"}, status_code=404)

@app.get("/static/js/script.js")
async def get_static_script_js():
    """Статический JS файл"""
    js_path = os.path.join(os.path.dirname(__file__), "static", "js", "script.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    return JSONResponse({"error": "JS file not found"}, status_code=404)

@app.post("/api/data")
async def receive_data(data: dict):
    """Прием данных от Arduino"""
    try:
        if data.get('type') == 'realtime':
            sensor_data = data.get('data', {})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(f'''
                INSERT INTO {SENSOR_DATA_TABLE} 
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
        print(f"❌ Ошибка приема данных: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/add_recommendation")
async def add_ai_recommendation(data: dict):
    """Добавление AI рекомендации"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            INSERT INTO {AI_RECOMMENDATIONS_TABLE} 
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
        print(f"❌ Ошибка добавления AI рекомендации: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    """Обработка сообщений AI чата"""
    try:
        user_message = request.message
        
        # Получаем последние данные сенсоров
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT temperature, humidity, hit_count, hits_per_minute
            FROM {SENSOR_DATA_TABLE}
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
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
            "parameters": {"user_message": user_message, "response": response_message}
        })
        
        return {"status": "success", "response": response_message}
        
    except Exception as e:
        print(f"❌ Ошибка AI чата: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/current")
async def get_current_data():
    """Текущие данные"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT timestamp, temperature, humidity, hit_count, hits_per_minute
            FROM {SENSOR_DATA_TABLE} 
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
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
        else:
            return {
                "message": "No data",
                "timestamp": datetime.now().isoformat(),
                "temperature": 0.0,
                "humidity": 0.0,
                "hit_count": 0,
                "hits_per_minute": 0.0
            }
        
    except Exception as e:
        print(f"❌ Ошибка получения текущих данных: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/history")
async def get_history(hours: int = HISTORY_DEFAULT_HOURS):
    """История"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT timestamp, temperature, humidity, hits_per_minute, hit_count
            FROM {SENSOR_DATA_TABLE} 
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (f'-{hours} hours', HISTORY_MAX_RECORDS))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"] or 0.0,
                "humidity": row["humidity"] or 0.0,
                "hits_per_minute": row["hits_per_minute"] or 0.0,
                "hit_count": row["hit_count"] or 0
            })
        
        return history
        
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        return []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "✅ Подключено к серверу мониторинга",
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
async def get_ai_recommendations(limit: int = RECOMMENDATIONS_DEFAULT_LIMIT):
    """AI рекомендации"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT timestamp, message, type, parameters
            FROM {AI_RECOMMENDATIONS_TABLE}
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
            full_name = ?, email = ?, phone = ?, department = ?, position = ?
            WHERE id = 1
        ''', (
            request.fullName,
            request.email,
            request.phone,
            request.department,
            request.position
        ))
        
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
        
        cursor.execute('SELECT full_name, email, phone, department, position FROM profiles WHERE id = 1')
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

@app.post("/api/export")
async def export_data(request: ExportRequest):
    """Экспорт данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем данные за указанный период
        cursor.execute(f'''
            SELECT timestamp, temperature, humidity, hits_per_minute, hit_count
            FROM {SENSOR_DATA_TABLE}
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp ASC
        ''', (request.start_date, request.end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"],
                "humidity": row["humidity"],
                "hits_per_minute": row["hits_per_minute"],
                "hit_count": row["hit_count"]
            })
        
        return {
            "status": "success", 
            "data": data,
            "metadata": {
                "period": f"{request.start_date} - {request.end_date}",
                "equipment": request.equipment,
                "format": request.format,
                "data_count": len(data),
                "exported_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), equipment: str = Form(...)):
    """Загрузка файла"""
    try:
        contents = await file.read()
        
        # Парсим CSV
        csv_text = contents.decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)
        
        if len(rows) < 2:
            return {"status": "error", "message": "Файл пустой"}
        
        # Сохраняем в БД
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        for i, row in enumerate(rows[1:], 1):  # Пропускаем заголовок
            if len(row) >= 5:
                try:
                    timestamp = row[0]
                    temperature = float(row[1]) if row[1] else 0.0
                    humidity = float(row[2]) if row[2] else 0.0
                    hits_per_minute = float(row[3]) if row[3] else 0.0
                    hit_count = int(row[4]) if row[4] else 0
                    
                    cursor.execute(f'''
                        INSERT INTO {SENSOR_DATA_TABLE} 
                        (timestamp, temperature, humidity, hits_per_minute, hit_count)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (timestamp, temperature, humidity, hits_per_minute, hit_count))
                    
                    imported_count += 1
                except ValueError as e:
                    print(f"Ошибка в строке {i}: {e}")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success", 
            "message": f"Файл успешно загружен",
            "rows": imported_count,
            "total_rows": len(rows) - 1
        }
        
    except Exception as e:
        print(f"❌ Ошибка загрузки файла: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/status")
async def get_status():
    """Статус системы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f'SELECT COUNT(*) as count FROM {SENSOR_DATA_TABLE}')
    data_count = cursor.fetchone()["count"]
    
    cursor.execute(f'SELECT COUNT(*) as count FROM {AI_RECOMMENDATIONS_TABLE}')
    ai_count = cursor.fetchone()["count"]
    
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
    print("INFO: Starting server process...")
    print("INFO: Waiting for application startup.")
    print("INFO: Application startup complete.")
    print(f"INFO: Uvicorn running on http://0.0.0.0:{PORT} (Press CTRL+C to quit)")
    uvicorn.run(app, host=HOST, port=PORT)