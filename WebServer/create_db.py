# create_new_db.py - Создание новой базы данных с правильной структурой
import sqlite3
import os
import hashlib
import secrets

DB_NAME = 'sensor_data.db'

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    salt = secrets.token_hex(16)
    return f"{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"

def create_new_database():
    """Создание новой базы данных с правильной структурой"""
    
    # Удаляем старую базу если существует
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"✅ Удалена старая база данных: {DB_NAME}")
        except:
            print(f"⚠️ Не удалось удалить {DB_NAME}, попробуем перезаписать")
    
    # Создаем новое соединение
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("📝 Создаем таблицы...")
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Таблица users создана")
    
    # Таблица данных сенсоров
    cursor.execute('''
        CREATE TABLE sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            hit_count INTEGER DEFAULT 0,
            hits_per_minute REAL DEFAULT 0
        )
    ''')
    print("  ✅ Таблица sensor_data создана")
    
    # Таблица AI рекомендаций
    cursor.execute('''
        CREATE TABLE ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            type TEXT,
            parameters TEXT
        )
    ''')
    print("  ✅ Таблица ai_recommendations создана")
    
    # Таблица настроек
    cursor.execute('''
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter TEXT UNIQUE,
            value TEXT
        )
    ''')
    print("  ✅ Таблица settings создана")
    
    # Таблица профилей
    cursor.execute('''
        CREATE TABLE profiles (
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
    print("  ✅ Таблица profiles создана")
    
    # Создаем тестового пользователя
    print("📝 Создаем тестового пользователя...")
    hashed_pw = hash_password("admin123")
    cursor.execute('''
        INSERT INTO users (username, password, email, full_name)
        VALUES (?, ?, ?, ?)
    ''', ("admin", hashed_pw, "admin@prommonitoring.ru", "Администратор"))
    
    user_id = cursor.lastrowid
    print(f"  ✅ Пользователь admin создан с ID: {user_id}")
    
    # Создаем профиль для админа
    cursor.execute('''
        INSERT INTO profiles (user_id, full_name, email, phone, department, position)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, "Администратор", "admin@prommonitoring.ru", "+7 (495) 123-45-67", "IT отдел", "Системный администратор"))
    print("  ✅ Профиль администратора создан")
    
    # Начальные настройки
    print("📝 Добавляем настройки по умолчанию...")
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
        cursor.execute('INSERT INTO settings (parameter, value) VALUES (?, ?)', (param, value))
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ БАЗА ДАННЫХ УСПЕШНО СОЗДАНА!")
    print("="*50)
    print(f"📁 Файл базы данных: {os.path.abspath(DB_NAME)}")
    print("🔐 Тестовый пользователь: admin")
    print("🔑 Пароль: admin123")
    print("="*50)

if __name__ == "__main__":
    create_new_database()