import serial
import time
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from collections import deque
import sys
import os
import numpy as np

# Конфигурация
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:8000/api/data"
AI_CHAT_URL = "http://127.0.0.1:8000/api/ai/add_recommendation"

class ArduinoDataProcessor:
    def __init__(self):
        self.serial_conn = None
        self.db_conn = sqlite3.connect('sensor_data.db', check_same_thread=False)
        self.init_db()
        self.hit_timestamps = deque(maxlen=300)
        self.last_hit_count = 0
        self.last_ai_message_time = datetime.now() - timedelta(minutes=5)  # 5 минут назад
        self.ai_message_cooldown = 60  # 60 секунд между сообщениями
        self.setup_serial()
        
    def init_db(self):
        cursor = self.db_conn.cursor()
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
        self.db_conn.commit()
        print("✅ База данных инициализирована")
    
    def setup_serial(self):
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                print(f"🔌 Подключение к {SERIAL_PORT} (попытка {attempt + 1}/{max_attempts})...")
                self.serial_conn = serial.Serial(
                    port=SERIAL_PORT,
                    baudrate=BAUD_RATE,
                    timeout=2
                )
                time.sleep(2)
                self.serial_conn.flushInput()
                print(f"✅ Успешно подключено к Arduino")
                return
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(3)
                else:
                    print("❌ Не удалось подключиться")
                    self.serial_conn = None
    
    def calculate_hits_per_minute(self) -> float:
        """Расчет ударов в минуту"""
        current_time = datetime.now()
        one_minute_ago = current_time - timedelta(seconds=60)
        
        while self.hit_timestamps and self.hit_timestamps[0] < one_minute_ago:
            self.hit_timestamps.popleft()
        
        return float(len(self.hit_timestamps))
    
    def parse_serial_data(self, line):
        """Парсинг данных от Arduino"""
        try:
            line = line.strip()
            if not line:
                return None
            
            print(f"📥 Получено: {line}")
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'hit_detected': 0,
                'hit_count': 0
            }
            
            if line.startswith('HIT:'):
                parts = line.split(',')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        if key.strip() == 'HIT':
                            data['hit_interval'] = int(value.strip())
                            data['hit_detected'] = 1
                            self.hit_timestamps.append(datetime.now())
                        elif key.strip() == 'COUNT':
                            data['hit_count'] = int(value.strip())
                            self.last_hit_count = data['hit_count']
                
            elif line.startswith('TEMP:'):
                parts = line.split(',')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'TEMP':
                            data['temperature'] = float(value)
                        elif key == 'HUM':
                            data['humidity'] = float(value)
                        elif key == 'HIT_COUNT':
                            data['hit_count'] = int(value)
                            self.last_hit_count = data['hit_count']
                
                if 'temperature' in data and 'humidity' in data:
                    hits_per_minute = self.calculate_hits_per_minute()
                    data['hits_per_minute'] = hits_per_minute
                    print(f"🌡️ {data['temperature']:.1f}°C | 💧 {data['humidity']:.1f}% | ⚡ {hits_per_minute:.1f} уд/мин")
            
            elif 'ERROR' in line:
                print(f"⚠️ Ошибка: {line}")
                return None
            elif 'System started' in line:
                print("🔄 Arduino перезапущен")
                self.hit_timestamps.clear()
                self.last_hit_count = 0
                return None
            
            return data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return None
    
    def get_ai_analysis(self, temp, hum, hits):
        """Получение анализа от AI"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'AI'))
            from simple_ai import get_recommendation
            
            result = get_recommendation(temp, hum, hits)
            return result
            
        except Exception as e:
            print(f"⚠️ Ошибка AI: {e}")
            hits_per_minute = self.calculate_hits_per_minute()
            return {
                'ai_message': "🤖 AI недоступен. Продолжайте мониторинг",
                'priority_level': 'normal',
                'hits_per_minute': hits_per_minute
            }
    
    def should_send_ai_message(self):
        """Проверяем, можно ли отправлять новое AI сообщение"""
        current_time = datetime.now()
        time_diff = (current_time - self.last_ai_message_time).seconds
        return time_diff >= self.ai_message_cooldown
    
    def process_data(self):
        """Основной цикл обработки"""
        print("=" * 60)
        print("🚀 ARDUINO DATA PROCESSOR v5.0")
        print("🤖 AI сообщения: ОДНО в минуту")
        print("=" * 60)
        
        last_temp_time = datetime.now()
        temp_buffer = []
        
        try:
            while True:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    try:
                        line_bytes = self.serial_conn.readline()
                        line = line_bytes.decode('utf-8', errors='ignore')
                        
                        if line:
                            data = self.parse_serial_data(line)
                            if data and 'temperature' in data:
                                # Сохраняем температуру для усреднения
                                temp_buffer.append({
                                    'temp': data['temperature'],
                                    'hum': data['humidity'],
                                    'time': datetime.now()
                                })
                                
                                # Храним только последние 30 секунд
                                thirty_seconds_ago = datetime.now() - timedelta(seconds=30)
                                temp_buffer = [d for d in temp_buffer if d['time'] > thirty_seconds_ago]
                                
                                # Отправляем данные на сервер
                                self.send_to_server(data)
                                
                                # Проверяем AI анализ (раз в минуту)
                                if self.should_send_ai_message():
                                    if len(temp_buffer) >= 3:  # Есть достаточно данных
                                        # Усредняем температуру и влажность
                                        avg_temp = np.mean([d['temp'] for d in temp_buffer])
                                        avg_hum = np.mean([d['hum'] for d in temp_buffer])
                                        
                                        # Получаем AI анализ
                                        ai_result = self.get_ai_analysis(
                                            avg_temp, 
                                            avg_hum, 
                                            self.last_hit_count
                                        )
                                        
                                        # Добавляем hits_per_minute если его нет
                                        if 'hits_per_minute' not in ai_result:
                                            ai_result['hits_per_minute'] = self.calculate_hits_per_minute()
                                        
                                        # Отправляем в чат
                                        self.send_ai_to_chat(ai_result)
                                        
                                        # Обновляем время последнего сообщения
                                        self.last_ai_message_time = datetime.now()
                                        
                                        print(f"⏰ Следующее AI сообщение через 60 секунд")
                    
                    except Exception as e:
                        print(f"❌ Ошибка обработки: {e}")
                
                # Проверяем состояние каждую секунду
                current_time = datetime.now()
                if (current_time - last_temp_time).seconds >= 10:
                    # Показываем текущее состояние
                    hits_per_minute = self.calculate_hits_per_minute()
                    print(f"🔄 Статус: {hits_per_minute:.1f} уд/мин | Сообщений до: {60 - (current_time - self.last_ai_message_time).seconds}с")
                    last_temp_time = current_time
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Завершение работы...")
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def send_to_server(self, data):
        """Отправка данных на сервер"""
        try:
            # Добавляем hits_per_minute
            if 'temperature' in data:
                data['hits_per_minute'] = self.calculate_hits_per_minute()
            
            response = requests.post(API_URL, json={
                'type': 'realtime',
                'data': data
            }, timeout=5)
            
            if response.status_code != 200:
                print(f"⚠️ Сервер вернул {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
    
    def send_ai_to_chat(self, ai_result):
        """Отправка AI сообщения в чат"""
        try:
            chat_message = {
                "timestamp": datetime.now().isoformat(),
                "message": ai_result.get('ai_message', "🤖 Нет рекомендаций"),
                "type": "info",
                "confidence": 0.9,
                "parameters": {
                    "hits_per_minute": ai_result.get('hits_per_minute', 0),
                    "priority_level": ai_result.get('priority_level', 'normal'),
                    "risk_score": ai_result.get('risk_score', 0.0)
                }
            }
            
            # Определяем тип сообщения
            priority = ai_result.get('priority_level', 'normal')
            if priority == 'critical':
                chat_message['type'] = 'danger'
            elif priority == 'warning':
                chat_message['type'] = 'warning'
            elif priority == 'normal':
                chat_message['type'] = 'success'
            
            response = requests.post(AI_CHAT_URL, json=chat_message, timeout=5)
            if response.status_code == 200:
                msg = ai_result.get('ai_message', '')
                print(f"✅ AI: {msg[:80]}...")
            else:
                print(f"⚠️ Не удалось отправить в чат")
                
        except Exception as e:
            print(f"❌ Ошибка отправки в чат: {e}")
    
    def cleanup(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("🔌 Порт закрыт")
        self.db_conn.close()
        print("✅ Ресурсы очищены")

def main():
    processor = ArduinoDataProcessor()
    try:
        processor.process_data()
    except KeyboardInterrupt:
        print("\n✅ Программа завершена")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        processor.cleanup()

if __name__ == "__main__":
    main()