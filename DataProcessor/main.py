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
SERIAL_PORT = 'COM3'  # Измените на ваш порт
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:8000/api/data"
AI_CHAT_URL = "http://127.0.0.1:8000/api/ai/add_recommendation"
BUFFER_SIZE = 150

class ArduinoDataProcessor:
    def __init__(self):
        self.serial_conn = None
        self.db_conn = sqlite3.connect('sensor_data.db', check_same_thread=False)
        self.init_db()
        self.data_buffer = deque(maxlen=BUFFER_SIZE)
        self.hit_count_5min = 0
        self.last_ai_recommendation = None
        self.setup_serial()
        
    def init_db(self):
        cursor = self.db_conn.cursor()
        # Таблицы уже созданы веб-сервером
        self.db_conn.commit()
        print("✅ Подключение к БД установлено")
    
    def setup_serial(self):
        """Подключение к Arduino через UART"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                print(f"🔌 Попытка подключения к {SERIAL_PORT} (попытка {attempt + 1}/{max_attempts})...")
                self.serial_conn = serial.Serial(
                    port=SERIAL_PORT,
                    baudrate=BAUD_RATE,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=2
                )
                time.sleep(2)  # Даем время Arduino на инициализацию
                
                # Читаем начальные сообщения
                self.serial_conn.flushInput()
                time.sleep(1)
                
                print(f"✅ Успешно подключено к Arduino на {SERIAL_PORT}")
                return
                
            except Exception as e:
                print(f"❌ Ошибка подключения: {e}")
                if attempt < max_attempts - 1:
                    print(f"⏳ Повторная попытка через 3 секунды...")
                    time.sleep(3)
                else:
                    print("❌ Не удалось подключиться к Arduino")
                    print("Проверьте:")
                    print("1. Подключен ли Arduino к компьютеру")
                    print("2. Правильный ли порт COM3")
                    print("3. Загружен ли скетч на Arduino")
    
    def parse_serial_data(self, line):
        """Парсинг данных от Arduino"""
        try:
            line = line.strip()
            if not line:
                return None
            
            print(f"📥 Получено от Arduino: {line}")
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'hit_detected': 0,
                'hit_interval': 0,
                'hit_count': 0
            }
            
            # Парсинг в зависимости от формата
            if line.startswith('HIT:'):
                # Формат: HIT:123,COUNT:5
                parts = line.split(',')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'HIT':
                            data['hit_interval'] = int(value)
                            data['hit_detected'] = 1
                            self.hit_count_5min += 1
                            print(f"⚡ Удар! Интервал: {value}ms")
                        elif key == 'COUNT':
                            data['hit_count'] = int(value)
                
            elif line.startswith('TEMP:'):
                # Формат: TEMP:22.5,HUM:55.0,HIT_COUNT:3
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
                
                if 'temperature' in data and 'humidity' in data:
                    print(f"🌡️  Температура: {data['temperature']}°C | 💧 Влажность: {data['humidity']}%")
            
            elif 'ERROR' in line:
                print(f"⚠️  Ошибка Arduino: {line}")
                return None
            elif 'System started' in line:
                print("🔄 Arduino перезапущен")
                return None
            else:
                print(f"📝 Неизвестный формат: {line}")
                return None
            
            return data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга данных: {e}")
            return None
    
    def send_to_web_server(self, data):
        """Отправка данных на веб-сервер"""
        try:
            response = requests.post(API_URL, json=data, timeout=5)
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️  Сервер вернул статус {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка отправки на сервер: {e}")
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
        
        # Расчет среднего и стандартного отклонения
        avg_temp = np.mean(temps)
        avg_hum = np.mean(hums)
        std_temp = np.std(temps)
        std_hum = np.std(hums)
        
        avg_data = {
            'timestamp': datetime.now().isoformat(),
            'avg_temperature': float(avg_temp),
            'avg_humidity': float(avg_hum),
            'std_temperature': float(std_temp),
            'std_humidity': float(std_hum),
            'total_hits': self.hit_count_5min,
            'data_points': len(self.data_buffer)
        }
        
        return avg_data
    
    def get_ai_analysis(self, avg_data):
        """Получение анализа от AI модуля"""
        try:
            # Динамический импорт AI модуля
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'AI'))
            from simple_ai import get_recommendation
            
            result = get_recommendation(
                avg_data['avg_temperature'],
                avg_data['avg_humidity'],
                avg_data['total_hits']
            )
            
            return result
            
        except Exception as e:
            print(f"⚠️  Ошибка AI модуля: {e}")
            # Базовая логика
            recommendations = ["AI модуль временно недоступен"]
            if avg_data['avg_temperature'] > 30:
                recommendations.append("⚠️ Высокая температура!")
            
            return {
                'recommendations': recommendations,
                'confidence': 0.5,
                'prediction_class': -1
            }
    
    def send_ai_to_chat(self, avg_data, ai_result):
        """Отправка AI рекомендации в чат"""
        try:
            chat_message = {
                "timestamp": datetime.now().isoformat(),
                "message": " | ".join(ai_result['recommendations'][:2]),
                "type": "warning" if ai_result['prediction_class'] > 0 else "info",
                "parameters": {
                    "temperature": avg_data['avg_temperature'],
                    "humidity": avg_data['avg_humidity'],
                    "hits": avg_data['total_hits'],
                    "confidence": ai_result['confidence']
                }
            }
            
            response = requests.post(AI_CHAT_URL, json=chat_message, timeout=5)
            if response.status_code == 200:
                print("✅ AI рекомендация отправлена в чат")
                self.last_ai_recommendation = chat_message
            else:
                print(f"⚠️  Не удалось отправить AI рекомендацию")
                
        except Exception as e:
            print(f"❌ Ошибка отправки AI в чат: {e}")
    
    def process_data(self):
        """Основной цикл обработки данных"""
        last_ai_analysis = datetime.now()  # Для частого AI
        last_5min_calc = datetime.now()    # Для 5-минутных средних
        last_hourly_reset = datetime.now()
        
        print("=" * 60)
        print("🚀 ARDUINO DATA PROCESSOR v3.0")
        print("=" * 60)
        print(f"📡 Порт: {SERIAL_PORT}")
        print(f"📊 Буфер: {BUFFER_SIZE} записей")
        print(f"🤖 AI анализ каждую минуту")
        print("=" * 60)
        
        try:
            while True:
                # Чтение данных из порта
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    try:
                        line_bytes = self.serial_conn.readline()
                        line = line_bytes.decode('utf-8', errors='ignore')
                        
                        if line:
                            data = self.parse_serial_data(line)
                            if data:
                                # Сохраняем в буфер
                                if 'temperature' in data:
                                    self.data_buffer.append(data)
                                
                                # Отправляем на веб-сервер
                                success = self.send_to_web_server({
                                    'type': 'realtime',
                                    'data': data
                                })
                                
                                if not success:
                                    print("⚠️  Не удалось отправить данные на сервер")
                                    
                    except Exception as e:
                        print(f"❌ Ошибка чтения/отправки: {e}")
                
                current_time = datetime.now()
                
                # ✅ ЧАСТЫЙ AI АНАЛИЗ (каждую минуту)
                if (current_time - last_ai_analysis).seconds >= 60:
                    print("\n" + "=" * 40)
                    print("🤖 БЫСТРЫЙ AI АНАЛИЗ...")
                    print("=" * 40)
                    
                    if len(self.data_buffer) > 0:
                        # Берем последние данные
                        latest_data = self.data_buffer[-1] if self.data_buffer else None
                        if latest_data and 'temperature' in latest_data:
                            # Быстрый AI анализ
                            quick_result = self.get_ai_analysis({
                                'avg_temperature': latest_data.get('temperature', 0),
                                'avg_humidity': latest_data.get('humidity', 0),
                                'total_hits': latest_data.get('hit_count', 0)
                            })
                            
                            # Отправляем быструю рекомендацию
                            quick_message = {
                                "timestamp": datetime.now().isoformat(),
                                "message": f"🔄 Быстрая проверка: {latest_data.get('temperature', 0):.1f}°C, "
                                        f"{latest_data.get('humidity', 0):.1f}%, "
                                        f"{latest_data.get('hit_count', 0)} ударов | "
                                        f"{quick_result['recommendations'][0] if quick_result['recommendations'] else 'OK'}",
                                "type": "info",
                                "parameters": {
                                    "temperature": latest_data.get('temperature', 0),
                                    "humidity": latest_data.get('humidity', 0),
                                    "hits": latest_data.get('hit_count', 0),
                                    "quick_check": True
                                }
                            }
                            
                            try:
                                response = requests.post(AI_CHAT_URL, json=quick_message, timeout=3)
                                if response.status_code == 200:
                                    print(f"✅ Быстрый AI анализ отправлен")
                            except:
                                pass
                    
                    last_ai_analysis = current_time
                    print("=" * 40 + "\n")
                
                # 5-минутный анализ (расширенный)
                if (current_time - last_5min_calc).seconds >= 60:  # 1 минута
                    print("\n" + "=" * 60)
                    print("📊 ВЫПОЛНЕНИЕ 5-МИНУТНОГО АНАЛИЗА...")
                    print("=" * 60)
                    
                    avg_data = self.calculate_5min_average()
                    if avg_data:
                        print(f"📈 Средняя температура: {avg_data['avg_temperature']:.1f}°C")
                        print(f"📈 Средняя влажность: {avg_data['avg_humidity']:.1f}%")
                        print(f"⚡ Всего ударов: {avg_data['total_hits']}")
                        
                        # Получаем AI анализ
                        ai_result = self.get_ai_analysis(avg_data)
                        
                        # Сохраняем в БД
                        self.save_5min_data(avg_data, ai_result)
                        
                        # Отправляем на веб-сервер
                        combined_data = {
                            'type': '5min_avg',
                            'timestamp': avg_data['timestamp'],
                            'avg_temperature': avg_data['avg_temperature'],
                            'avg_humidity': avg_data['avg_humidity'],
                            'total_hits': avg_data['total_hits'],
                            'ai_recommendations': ai_result['recommendations'][:3],  # Только 3 главные
                            'ai_confidence': ai_result['confidence'],
                            'failure_risk': ai_result.get('failure_risk', 0),
                            'risk_level': ai_result.get('risk_analysis', {}).get('risk_level', 'unknown')
                        }
                        
                        self.send_to_web_server(combined_data)
                        
                        # Отправляем в AI чат
                        self.send_ai_to_chat(avg_data, ai_result)
                        
                        # Выводим рекомендации
                        print("🤖 AI РЕКОМЕНДАЦИИ:")
                        for i, rec in enumerate(ai_result['recommendations'][:3], 1):
                            print(f"  {i}. {rec}")
                        print(f"  Уверенность: {ai_result['confidence']:.1%}")
                        print(f"  Риск отказа: {ai_result.get('failure_risk', 0):.1%}")
                    
                    last_5min_calc = current_time
                    print("=" * 60 + "\n")
                
                # Сброс счетчика ударов каждый час
                if (current_time - last_hourly_reset).seconds >= 3600:
                    self.hit_count_5min = 0
                    last_hourly_reset = current_time
                    print("🔄 Сброс счетчика ударов (каждый час)")
                
                time.sleep(0.05)  # Уменьшили паузу для более быстрой реакции
                
        except KeyboardInterrupt:
            print("\n\n🛑 Завершение работы...")
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
    
    def save_5min_data(self, avg_data, ai_result):
        """Сохранение 5-минутных данных"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO five_min_avg 
                (timestamp, avg_temperature, avg_humidity, total_hits, ai_recommendation, ai_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                avg_data['timestamp'],
                avg_data['avg_temperature'],
                avg_data['avg_humidity'],
                avg_data['total_hits'],
                json.dumps(ai_result),
                ai_result['confidence']
            ))
            self.db_conn.commit()
            
            print("💾 5-минутные данные сохранены в БД")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения 5-минутных данных: {e}")
    
    def cleanup(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.db_conn.close()
        print("✅ Ресурсы очищены")

def main():
    processor = ArduinoDataProcessor()
    try:
        processor.process_data()
    except KeyboardInterrupt:
        print("\n✅ Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
    finally:
        processor.cleanup()

if __name__ == "__main__":
    main()