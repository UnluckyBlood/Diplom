from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import sqlite3
import uvicorn
import os
import csv
import hashlib
import secrets
from io import StringIO, BytesIO
from typing import List, Optional
import jwt
from jwt import PyJWTError
import requests
from contextlib import asynccontextmanager
# доп библиотеки для PDF могут не работать на всех системах, поэтому оборачиваем в try-except
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import inch
    PDF_EXPORT_SUPPORT = True
except ImportError:
    PDF_EXPORT_SUPPORT = False

# КОНСТАНТЫ
DB_NAME = 'sensor_data.db'
HOST = "localhost"
PORT = 8000

# JWT настройки желательно закинуть в .env файл и не хранить в коде, но для простоты примера так и чтобы не усложнять при  демке проекта
SECRET_KEY = "your-super-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Ollama настройки
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral:7b"

# Модели данных
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    email: str
    full_name: str

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

security = HTTPBearer()

# Функции для работы с Ollama
def check_ollama_available():
    """Проверка доступности Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"✅ Ollama доступен, модели: {[m.get('name') for m in models]}")
            return True
    except:
        print("⚠️ Ollama недоступен")
    return False

def get_ollama_response(prompt: str, context: str = "") -> str:
    """Получение ответа от локальной Ollama модели"""
    try:
        full_prompt = f"{context}\n\nПользователь: {prompt}\n\nАссистент:"

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('response', "Извините, не удалось получить ответ.")
        else:
            return f"Ошибка Ollama: {response.status_code}"

    except requests.exceptions.Timeout:
        return "⚠️ Таймаут ожидания ответа от Ollama. Попробуйте позже."
    except Exception as e:
        print(f"❌ Ошибка Ollama: {e}")
        return f"⚠️ Ошибка подключения к Ollama: {str(e)}"

OLLAMA_AVAILABLE = check_ollama_available()

# Функции для работы с паролями и JWT
def hash_password(password: str) -> str:
    """Хеширование пароля"""
    salt = secrets.token_hex(16)
    return f"{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"

def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    try:
        salt, hash_val = hashed.split(':')
        return hash_val == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка JWT токена"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен"
            )
        return username
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший токен"
        )

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

# Работа с базой данных
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица данных сенсоров
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

    # Таблица AI рекомендаций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_recommendations (
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
            user_id INTEGER,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            department TEXT,
            position TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Новая таблица для документов AI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создаем тестового пользователя (только если нет пользователей)
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        hashed_pw = hash_password("admin123")
        cursor.execute('''
            INSERT INTO users (username, password, email, full_name)
            VALUES (?, ?, ?, ?)
        ''', ("admin", hashed_pw, "admin@prommonitoring.ru", "Администратор"))

        # Получаем ID созданного пользователя
        user_id = cursor.lastrowid

        # Создаем профиль для админа
        cursor.execute('''
            INSERT INTO profiles (user_id, full_name, email, phone, department, position)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, "Администратор", "admin@prommonitoring.ru", "+7 (495) 123-45-67", "IT отдел", "Системный администратор"))

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

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# Lifespan для управления стартом и остановкой
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    print(f"🚀 Сервер запущен на http://localhost:{PORT}")
    print(f"⚡ WebSocket: ws://localhost:{PORT}/ws")
    print(f"🤖 Ollama: {'✅ Доступен' if OLLAMA_AVAILABLE else '❌ Недоступен'}")
    print(f"🔐 JWT аутентификация: ✅ Включена")
    print(f"📝 Тестовый пользователь: admin / admin123")
    if PDF_SUPPORT: print("📄 Поддержка PDF документов: ✅")
    else: print("📄 PDF документы: ❌ (установите PyPDF2)")
    if PDF_EXPORT_SUPPORT: print("📊 Экспорт в PDF: ✅")
    else: print("📊 Экспорт в PDF: ❌ (установите reportlab)")
    yield
    # Shutdown
    print("🛑 Сервер остановлен")

app = FastAPI(title="Пром Мониторинг", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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

# ============ АУТЕНТИФИКАЦИЯ ============

@app.post("/api/auth/register")
async def register(user: UserRegister):
    """Регистрация нового пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username = ?', (user.username,))
        if cursor.fetchone():
            conn.close()
            return {"status": "error", "message": "Пользователь уже существует"}

        hashed_pw = hash_password(user.password)
        cursor.execute('''
            INSERT INTO users (username, password, email, full_name)
            VALUES (?, ?, ?, ?)
        ''', (user.username, hashed_pw, user.email, user.full_name))

        user_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO profiles (user_id, full_name, email, phone, department, position)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user.full_name, user.email, "", "", ""))

        conn.commit()
        conn.close()

        token = create_access_token(data={"sub": user.username})

        return {
            "status": "success",
            "token": token,
            "user": {
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email
            }
        }

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/auth/login")
async def login(user: UserLogin):
    """Вход в систему"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password, email, full_name FROM users WHERE username = ?', (user.username,))
        db_user = cursor.fetchone()
        conn.close()

        if not db_user:
            return {"status": "error", "message": "Неверное имя пользователя или пароль"}

        if not verify_password(user.password, db_user["password"]):
            return {"status": "error", "message": "Неверное имя пользователя или пароль"}

        token = create_access_token(data={"sub": user.username})

        return {
            "status": "success",
            "token": token,
            "user": {
                "id": db_user["id"],
                "username": db_user["username"],
                "full_name": db_user["full_name"],
                "email": db_user["email"]
            }
        }

    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/auth/verify")
async def verify_token_endpoint(username: str = Depends(verify_token)):
    """Проверка валидности токена"""
    return {"status": "success", "username": username}

# ============ API ЭНДПОИНТЫ ============

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

# ---------- AI и рекомендации ----------
async def add_ai_recommendation(data: dict):
    """Добавление AI рекомендации в БД и broadcast (если не чат)"""
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

        # Отправляем broadcast только если это не сообщение чата (чтобы избежать дублирования)
        if data.get("type") != "chat":
            await manager.broadcast(json.dumps({
                "type": "ai_recommendation",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }))

    except Exception as e:
        print(f"❌ Ошибка добавления рекомендации: {e}")

@app.post("/api/ai/chat")
async def ai_chat(request: ChatRequest, username: str = Depends(verify_token)):
    """Обработка AI чата с использованием Ollama (с поиском по документам)"""
    try:
        user_message = request.message

        # Поиск релевантных документов (инструкций)
        doc_context = ""
        words = user_message.lower().split()
        if words:
            conn_doc = get_db_connection()
            cursor_doc = conn_doc.cursor()
            # Простой поиск по ключевым словам
            placeholders = ' OR '.join(['content LIKE ?' for _ in words])
            try:
                cursor_doc.execute(f'SELECT content FROM documents WHERE {placeholders} LIMIT 3',
                                   [f'%{word}%' for word in words])
                docs = cursor_doc.fetchall()
                if docs:
                    doc_context = "Релевантные инструкции:\n" + "\n".join([d["content"][:500] for d in docs])
            except:
                pass
            conn_doc.close()

        # Получаем текущие данные с датчиков
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT temperature, humidity, hit_count, hits_per_minute FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()

        context = ""
        if row:
            temperature = row["temperature"] or 0.0
            humidity = row["humidity"] or 0.0
            hits_per_minute = row["hits_per_minute"] or 0.0

            context = f"""Текущие показатели промышленного оборудования:
- Температура: {temperature:.1f}°C
- Влажность: {humidity:.1f}%
- Вибрации: {hits_per_minute:.1f} уд/мин

Нормы:
- Температура: 20-75°C
- Влажность: 20-80%
- Вибрации: 0-30 уд/мин

Ты - AI ассистент для промышленного мониторинга. Отвечай кратко, профессионально и давай практические рекомендации."""

        # Добавляем контекст из документов
        if doc_context:
            context += "\n\n" + doc_context

        if OLLAMA_AVAILABLE:
            ai_response = get_ollama_response(user_message, context)
        else:
            ai_response = f"""🤖 **Ассистент по промышленному мониторингу**

⚠️ *Ollama не доступен. Убедитесь, что он запущен:*
- Установите Ollama: https://ollama.ai
- Запустите: `ollama serve`
- Установите модель: `ollama pull {OLLAMA_MODEL}`

**Ваш вопрос:** {user_message}

**Последние данные:**
{context if context else "Нет данных с датчиков"}"""

        await add_ai_recommendation({
            "timestamp": datetime.now().isoformat(),
            "message": f"💬 {username}: {user_message}\n🤖 AI: {ai_response}",
            "type": "chat",
            "parameters": json.dumps({"user_message": user_message, "response": ai_response, "username": username})
        })

        return {"status": "success", "response": ai_response}

    except Exception as e:
        print(f"❌ Ошибка AI чата: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/add_recommendation")
async def add_recommendation(request: AIRecommendationRequest):
    """Добавление AI рекомендации (для внешних вызовов)"""
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
async def get_ai_recommendations(limit: int = Query(10, ge=1, le=100), username: str = Depends(verify_token)):
    """Получение списка AI рекомендаций (GET)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, message, type, parameters
            FROM ai_recommendations
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        recommendations = []
        for row in rows:
            recommendations.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "message": row["message"],
                "type": row["type"],
                "parameters": json.loads(row["parameters"]) if row["parameters"] else {}
            })

        return {"status": "success", "recommendations": recommendations}
    except Exception as e:
        print(f"❌ Ошибка получения рекомендаций: {e}")
        return {"status": "error", "message": str(e), "recommendations": []}

# ---------- Основные данные ----------
@app.get("/api/current")
async def get_current_data(username: str = Depends(verify_token)):
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
async def get_history(hours: int = Query(1, ge=1, le=24), username: str = Depends(verify_token)):
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
    """WebSocket для реального времени"""
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
        print("🔌 WebSocket отключен")
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
        manager.disconnect(websocket)

# ---------- Настройки и профиль ----------
@app.post("/api/save_settings")
async def save_settings(request: SettingsRequest, username: str = Depends(verify_token)):
    """Сохранение настроек"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_min', request.temperature.get('min', '20')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_max', request.temperature.get('max', '75')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('temperature_critical', request.temperature.get('critical', '80')))

        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_min', request.pressure.get('min', '5')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_max', request.pressure.get('max', '10')))
        cursor.execute('INSERT OR REPLACE INTO settings (parameter, value) VALUES (?, ?)', 
                      ('pressure_critical', request.pressure.get('critical', '12')))

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
async def get_settings(username: str = Depends(verify_token)):
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
async def save_profile(request: ProfileRequest, username: str = Depends(verify_token)):
    """Сохранение профиля"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user:
            cursor.execute('''
                UPDATE profiles SET 
                full_name=?, email=?, phone=?, department=?, position=?
                WHERE user_id=?
            ''', (request.fullName, request.email, request.phone, request.department, request.position, user["id"]))

            cursor.execute('UPDATE users SET full_name=? WHERE id=?', (request.fullName, user["id"]))

            conn.commit()

        conn.close()
        return {"status": "success", "message": "Профиль успешно сохранен"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/get_profile")
async def get_profile(username: str = Depends(verify_token)):
    """Получение профиля"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.full_name, p.email, p.phone, p.department, p.position
            FROM profiles p
            JOIN users u ON p.user_id = u.id
            WHERE u.username = ?
        ''', (username,))
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

# ---------- Загрузка CSV файлов ----------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), username: str = Depends(verify_token)):
    """Загрузка CSV файла"""
    try:
        contents = await file.read()
        csv_text = contents.decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)

        conn = get_db_connection()
        cursor = conn.cursor()
        imported_count = 0

        for row in rows[1:]:
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

# ---------- Документы AI (загрузка инструкций) ----------
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), username: str = Depends(verify_token)):
    """Загрузка документа (TXT или PDF) в базу знаний AI"""
    content = ""
    filename = file.filename
    if filename.endswith('.txt'):
        content = (await file.read()).decode('utf-8')
    elif filename.endswith('.pdf'):
        if not PDF_SUPPORT:
            raise HTTPException(status_code=400, detail="PDF не поддерживается. Установите PyPDF2.")
        pdf_bytes = await file.read()
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                content += page_text + "\n"
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются только TXT и PDF файлы")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO documents (filename, content) VALUES (?, ?)', (filename, content))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Документ '{filename}' загружен"}

@app.get("/api/documents")
async def list_documents(username: str = Depends(verify_token)):
    """Список загруженных документов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filename, created_at FROM documents ORDER BY created_at DESC')
    docs = [{"id": row["id"], "filename": row["filename"], "created_at": row["created_at"]} for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "documents": docs}

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int, username: str = Depends(verify_token)):
    """Удаление документа"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Документ удалён"}

# ---------- Экспорт данных (CSV, JSON, PDF) ----------
@app.get("/api/export/data")
async def export_data(format: str = Query("csv"),
                      start_date: Optional[str] = Query(None),
                      end_date: Optional[str] = Query(None),
                      username: str = Depends(verify_token)):
    """Экспорт данных в CSV или JSON"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute('SELECT * FROM sensor_data WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp ASC',
                    (start_date, end_date))
    else:
        cursor.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "temperature", "humidity", "hits_per_minute", "hit_count"])
        for row in rows:
            writer.writerow([row["timestamp"], row["temperature"], row["humidity"],
                             row["hits_per_minute"], row["hit_count"]])
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=data.csv"})
    elif format == "json":
        data = [{"timestamp": row["timestamp"], "temperature": row["temperature"],
                 "humidity": row["humidity"], "hits_per_minute": row["hits_per_minute"],
                 "hit_count": row["hit_count"]} for row in rows]
        return JSONResponse(content=data)
    elif format == "excel":
        return {"status": "error", "message": "Excel экспорт не реализован. Установите openpyxl."}
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат")

@app.get("/api/export/pdf")
async def export_pdf(start_date: Optional[str] = Query(None),
                     end_date: Optional[str] = Query(None),
                     username: str = Depends(verify_token)):
    """Экспорт данных в PDF отчёт"""
    if not PDF_EXPORT_SUPPORT:
        raise HTTPException(status_code=501, detail="PDF экспорт недоступен. Установите reportlab.")

    conn = get_db_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute('SELECT * FROM sensor_data WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp ASC',
                    (start_date, end_date))
    else:
        cursor.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']

    elements.append(Paragraph("Отчёт системы Пром Мониторинг", title_style))
    elements.append(Spacer(1, 12))

    if rows:
        temps = [r["temperature"] for r in rows if r["temperature"] is not None]
        hums = [r["humidity"] for r in rows if r["humidity"] is not None]
        vibs = [r["hits_per_minute"] for r in rows if r["hits_per_minute"] is not None]
        summary_data = [
            ["Показатель", "Минимум", "Максимум", "Среднее"],
            ["Температура (°C)", f"{min(temps):.1f}" if temps else "—",
             f"{max(temps):.1f}" if temps else "—", f"{sum(temps)/len(temps):.1f}" if temps else "—"],
            ["Влажность (%)", f"{min(hums):.1f}" if hums else "—",
             f"{max(hums):.1f}" if hums else "—", f"{sum(hums)/len(hums):.1f}" if hums else "—"],
            ["Вибрации (уд/мин)", f"{min(vibs):.1f}" if vibs else "—",
             f"{max(vibs):.1f}" if vibs else "—", f"{sum(vibs)/len(vibs):.1f}" if vibs else "—"],
        ]
        t = Table(summary_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ]))
        elements.append(Paragraph("Сводка", heading_style))
        elements.append(t)
        elements.append(Spacer(1, 12))

        data = [["Время", "Температура", "Влажность", "Вибрации", "Удары"]]
        for r in rows:
            data.append([
                r["timestamp"],
                f"{r['temperature']:.1f}" if r["temperature"] is not None else "",
                f"{r['humidity']:.1f}" if r["humidity"] is not None else "",
                f"{r['hits_per_minute']:.1f}" if r["hits_per_minute"] is not None else "",
                str(r["hit_count"]) if r["hit_count"] is not None else ""
            ])
        t2 = Table(data)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(Paragraph("Данные", heading_style))
        elements.append(t2)
    else:
        elements.append(Paragraph("Нет данных за выбранный период.", normal_style))

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=report.pdf"})

# ---------- Статус ----------
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
        "ollama_available": OLLAMA_AVAILABLE,
        "data_records": data_count,
        "ai_recommendations": ai_count,
        "version": "6.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)