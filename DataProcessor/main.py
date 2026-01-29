import serial
import time
import json
import sqlite3
import asyncio
import aiohttp
from datetime import datetime, timedelta
from collections import deque
import sys
import os

# Добавляем путь к AI
sys.path.append(os.path.join(os.path.dirname(__file__), 'AI'))

# Конфигурация
SERIAL_PORT = 'COM3'  # Измените на ваш порт
BAUD_RATE = 9600
API_URL = "http://localhost:8000/api/data"
BUFFER_SIZE = 150

class ArduinoDataProcessor:
    def __init__(self):
        self.serial_conn = None
        self.db_conn = sqlite3.connect('sensor_data.db', check_same_thread=False)
        self.init_db()
        self.data_buffer = deque(maxlen=BUFFER_SIZE)
        self.hit_count_5min = 0
        self.setup_serial()
        
    def init_db(self):
        cursor = self.db_conn.cursor()
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
        self.db_conn.commit()
        print("База данных инициализирована")
    
    def setup_serial(self):
        try:
            self.serial_conn = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUD_RATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
            print(f"Успешно подключено к {SERIAL_PORT}")
            time.sleep(2)
        except Exception as e:
            print(f"Ошибка подключения к {SERIAL_PORT}: {e}")
    
    def parse_serial_data(self, line):
        """Парсинг данных от Arduino"""
        try:
            line = line.strip()
            print(f"Получено: {line}")
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'hit_detected': 0,
                'hit_interval': 0,
                'hit_count': 0
            }
            
            if line.startswith('HIT:'):
                parts = line.split(',')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        if key == 'HIT':
                            data['hit_interval'] = int(value)
                            data['hit_detected'] = 1
                            self.hit_count_5min += 1
                        elif key == 'COUNT':
                            data['hit_count'] = int(value)
                
                print(f"Удар обнаружен! Интервал: {data['hit_interval']}ms")
                return data
            
            elif line.startswith('TEMP:'):
                parts = line.split(',')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        if key == 'TEMP':
                            data['temperature'] = float(value)
                        elif key == 'HUM':
                            data['humidity'] = float(value)
                        elif key == 'HIT_COUNT':
                            data['hit_count'] = int(value)
                
                if 'temperature' in data and 'humidity' in data:
                    print(f"Температура: {data['temperature']}°C, Влажность: {data['humidity']}%")
                    return data
            
            elif 'ERROR' in line:
                print(f"Ошибка от Arduino: {line}")
                return None
                
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
        
        return None
    
    def save_to_db(self, data):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO sensor_data 
                (timestamp, temperature, humidity, hit_detected, hit_interval, hit_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('temperature'),
                data.get('humidity'),
                data.get('hit_detected', 0),
                data.get('hit_interval', 0),
                data.get('hit_count', 0)
            ))
            self.db_conn.commit()
            
            if 'temperature' in data:
                self.data_buffer.append(data)
                
        except Exception as e:
            print(f"Ошибка сохранения в БД: {e}")
    
    async def send_to_web_server(self, data: dict):
        """Отправка данных на веб-сервер"""
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(API_URL, json=data) as response:
                    if response.status == 200:
                        print("✓ Данные успешно отправлены на сервер")
                        return True
                    else:
                        print(f"✗ Сервер вернул статус {response.status}")
                        return False
        except asyncio.TimeoutError:
            print("✗ Таймаут при отправке на сервер")
            return False
        except Exception as e:
            print(f"✗ Ошибка отправки на сервер: {e}")
            return False
    
    def calculate_5min_average(self):
        """Расчет средних значений за 5 минут"""
        if len(self.data_buffer) < 5:
            return None
        
        temps = []
        hums = []
        
        for d in self.data_buffer:
            if 'temperature' in d:
                temps.append(d['temperature'])
            if 'humidity' in d:
                hums.append(d['humidity'])
        
        if not temps or not hums:
            return None
        
        # Простой расчет среднего
        avg_temp = sum(temps) / len(temps)
        avg_hum = sum(hums) / len(hums)
        
        avg_data = {
            'timestamp': datetime.now().isoformat(),
            'avg_temperature': avg_temp,
            'avg_humidity': avg_hum,
            'total_hits': self.hit_count_5min,
            'buffer_size': len(self.data_buffer)
        }
        
        return avg_data
    
    def get_ai_recommendation(self, avg_data):
        """Получение рекомендаций от ИИ"""
        try:
            from simple_ai import get_recommendation
            
            recommendation = get_recommendation(
                avg_data['avg_temperature'],
                avg_data['avg_humidity'],
                avg_data['total_hits']
            )
            
            return recommendation
            
        except ImportError as e:
            print(f"ИИ модуль не найден: {e}")
            return self.get_basic_recommendation(avg_data)
    
    def get_basic_recommendation(self, avg_data):
        """Базовая логика рекомендаций"""
        recommendations = []
        confidence = 0.7
        
        temp = avg_data['avg_temperature']
        hum = avg_data['avg_humidity']
        hits = avg_data['total_hits']
        
        if temp > 30:
            recommendations.append("⚠️ ВНИМАНИЕ: Высокая температура!")
            confidence = 0.9
        elif temp > 25:
            recommendations.append("🌡️ Температура выше нормы.")
        
        if hum > 70:
            recommendations.append("💧 Высокая влажность!")
        elif hum < 30:
            recommendations.append("🏜️ Низкая влажность.")
        
        if hits > 10:
            recommendations.append("🔨 Обнаружено много вибраций!")
            confidence = 0.85
        elif hits > 0:
            recommendations.append("⚡ Зафиксированы вибрации.")
        
        return {
            'recommendations': recommendations,
            'confidence': confidence,
            'prediction_class': -1
        }
    
    def save_5min_data(self, avg_data, ai_recommendation):
        """Сохранение 5-минутных данных"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO five_min_avg 
                (timestamp, avg_temperature, avg_humidity, total_hits, ai_recommendation)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                avg_data['timestamp'],
                avg_data['avg_temperature'],
                avg_data['avg_humidity'],
                avg_data['total_hits'],
                json.dumps(ai_recommendation)
            ))
            self.db_conn.commit()
            
            self.hit_count_5min = 0
            
            print(f"✓ 5-минутные данные сохранены в БД")
            
        except Exception as e:
            print(f"✗ Ошибка сохранения 5-минутных данных: {e}")
    
    async def process_data(self):
        """Основной цикл обработки данных"""
        last_5min_calc = datetime.now()
        
        print("=" * 50)
        print("🚀 Обработчик данных Arduino запущен")
        print("=" * 50)
        print("Ожидание данных от Arduino...")
        print("Для остановки нажмите Ctrl+C")
        print("=" * 50)
        
        while True:
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    try:
                        line_bytes = self.serial_conn.readline()
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        
                        if line:
                            data = self.parse_serial_data(line)
                            if data:
                                self.save_to_db(data)
                                success = await self.send_to_web_server({
                                    'type': 'realtime',
                                    'data': data
                                })
                                
                    except Exception as e:
                        print(f"✗ Ошибка чтения из порта: {e}")
                
                if (datetime.now() - last_5min_calc).seconds >= 300:
                    avg_data = self.calculate_5min_average()
                    if avg_data:
                        ai_recommendation = self.get_ai_recommendation(avg_data)
                        self.save_5min_data(avg_data, ai_recommendation)
                        
                        combined_data = {
                            'type': '5min_avg',
                            'timestamp': avg_data['timestamp'],
                            'avg_temperature': avg_data['avg_temperature'],
                            'avg_humidity': avg_data['avg_humidity'],
                            'total_hits': avg_data['total_hits'],
                            'ai_recommendations': ai_recommendation['recommendations'],
                            'ai_confidence': ai_recommendation['confidence']
                        }
                        
                        success = await self.send_to_web_server(combined_data)
                        if success:
                            print("✓ 5-минутные данные отправлены на сервер")
                        
                        print("\n" + "="*50)
                        print("📊 5-МИНУТНЫЙ ОТЧЕТ:")
                        print(f"🌡️  Средняя температура: {avg_data['avg_temperature']:.1f}°C")
                        print(f"💧  Средняя влажность: {avg_data['avg_humidity']:.1f}%")
                        print(f"⚡  Всего ударов: {avg_data['total_hits']}")
                        print("🤖  Рекомендации ИИ:")
                        for rec in ai_recommendation['recommendations'][:3]:
                            print(f"    • {rec}")
                        print("="*50 + "\n")
                    
                    last_5min_calc = datetime.now()
                
                await asyncio.sleep(0.01)
                
            except KeyboardInterrupt:
                print("\n🛑 Завершение работы...")
                break
            except Exception as e:
                print(f"✗ Ошибка в основном цикле: {e}")
                await asyncio.sleep(1)
    
    def cleanup(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.db_conn.close()
        print("✅ Ресурсы очищены")

async def main_async():
    processor = ArduinoDataProcessor()
    try:
        await processor.process_data()
    except KeyboardInterrupt:
        print("\n✅ Программа завершена пользователем")
    finally:
        processor.cleanup()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
