# main.py - ПОЛНЫЙ ИСПРАВЛЕННЫЙ КОД
import serial
import time
import json
import requests
import sys
import os
from datetime import datetime, timedelta
from collections import deque

# КОНСТАНТЫ КОНФИГУРАЦИИ
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:8000/api/data"
AI_CHAT_URL = "http://127.0.0.1:8000/api/ai/add_recommendation"

# КОНСТАНТЫ ДЛЯ ОБРАБОТКИ
MAX_SERIAL_ATTEMPTS = 5
SERIAL_RETRY_DELAY = 3  # секунды
INITIAL_CONNECTION_DELAY = 2  # секунды

# ВРЕМЕННЫЕ КОНСТАНТЫ
TEMPERATURE_AVERAGE_WINDOW = 30  # секунд для усреднения температуры
STATUS_UPDATE_INTERVAL = 10  # секунд между статусными сообщениями
MAIN_LOOP_DELAY = 0.1  # секунд
AI_MESSAGE_INTERVAL = 30  # секунд между AI сообщениями

# РАЗМЕРЫ БУФЕРОВ
HIT_TIMESTAMP_BUFFER_SIZE = 300

class ArduinoDataProcessor:
    def __init__(self):
        self.serial_conn = None
        self.hit_timestamps = deque(maxlen=HIT_TIMESTAMP_BUFFER_SIZE)
        self.last_hit_count = 0
        self.last_temp = None
        self.last_hum = None
        
        # Инициализация AI модуля
        self.ai_available = False
        self.get_recommendation = None
        self.init_ai_module()
        
        self.setup_serial()
    
    def init_ai_module(self):
        """Инициализация AI модуля"""
        try:
            # main.py находится в DataProcessor, поднимаемся на уровень выше, затем в AI
            current_dir = os.path.dirname(__file__)
            base_dir = os.path.dirname(current_dir)
            ai_path = os.path.join(base_dir, 'AI')
            
            sys.path.insert(0, ai_path)
            
            from simple_ai import get_recommendation
            self.get_recommendation = get_recommendation
            self.ai_available = True
            print(f"✅ AI модуль загружен из: {ai_path}")
        except ImportError as e:
            self.ai_available = False
            print(f"⚠️ AI модуль недоступен: {e}")
            print("ℹ️  AI сообщения будут генерироваться локально")
    
    def setup_serial(self):
        """Настройка последовательного порта"""
        for attempt in range(MAX_SERIAL_ATTEMPTS):
            try:
                print(f"🔌 Подключение к {SERIAL_PORT} (попытка {attempt + 1}/{MAX_SERIAL_ATTEMPTS})...")
                self.serial_conn = serial.Serial(
                    port=SERIAL_PORT,
                    baudrate=BAUD_RATE,
                    timeout=SERIAL_RETRY_DELAY
                )
                time.sleep(INITIAL_CONNECTION_DELAY)
                self.serial_conn.flushInput()
                print(f"✅ Успешно подключено к Arduino")
                return
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                if attempt < MAX_SERIAL_ATTEMPTS - 1:
                    time.sleep(SERIAL_RETRY_DELAY)
                else:
                    print("❌ Не удалось подключиться к Arduino")
                    self.serial_conn = None
    
    def calculate_hits_per_minute(self) -> float:
        """Расчет ударов в минуту"""
        current_time = datetime.now()
        one_minute_ago = current_time - timedelta(seconds=60)
        
        # Удаляем старые записи
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
                print(f"⚠️ Ошибка Arduino: {line}")
                return None
            elif 'System started' in line:
                print("🔄 Arduino перезапущен, сбрасываем счетчики")
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
            if self.ai_available and self.get_recommendation:
                result = self.get_recommendation(temp, hum, hits)
                return result
            else:
                # Генерируем локальный анализ если AI недоступен
                hits_per_minute = self.calculate_hits_per_minute()
                
                # Простая логика анализа
                if temp > 35:
                    message = f"⚠️ Внимание! Высокая температура: {temp:.1f}°C"
                    priority = 'warning'
                elif temp < 15:
                    message = f"⚠️ Низкая температура: {temp:.1f}°C"
                    priority = 'warning'
                elif hum > 80:
                    message = f"⚠️ Высокая влажность: {hum:.1f}%"
                    priority = 'warning'
                elif hum < 20:
                    message = f"⚠️ Низкая влажность: {hum:.1f}%"
                    priority = 'warning'
                elif hits_per_minute > 30:
                    message = f"⚠️ Повышенные вибрации: {hits_per_minute:.1f} уд/мин"
                    priority = 'warning'
                else:
                    message = f"✅ Система работает нормально. Темп: {temp:.1f}°C, Вл: {hum:.1f}%"
                    priority = 'normal'
                
                return {
                    'ai_message': message,
                    'priority_level': priority,
                    'hits_per_minute': hits_per_minute
                }
                
        except Exception as e:
            print(f"⚠️ Ошибка AI анализа: {e}")
            hits_per_minute = self.calculate_hits_per_minute()
            return {
                'ai_message': "🤖 Ошибка анализа данных",
                'priority_level': 'normal',
                'hits_per_minute': hits_per_minute
            }
    
    def should_send_ai_message(self, temp, hum):
        """Проверяем, изменились ли данные"""
        if self.last_temp is None or self.last_hum is None:
            return True
        
        # Отправляем если температура изменилась более чем на 0.5°C
        # или влажность изменилась более чем на 2%
        temp_changed = abs(temp - self.last_temp) > 0.5
        hum_changed = abs(hum - self.last_hum) > 2
        
        return temp_changed or hum_changed
    
    def process_data(self):
        """Основной цикл обработки"""
        print("=" * 60)
        print("🚀 ARDUINO DATA PROCESSOR v5.0")
        print(f"🤖 AI: {'✅ Включен' if self.ai_available else '⚠️ Локальный режим'}")
        print("=" * 60)
        
        last_status_time = datetime.now()
        last_ai_message_time = datetime.now()
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
                                # Сохраняем данные для усреднения
                                temp_buffer.append({
                                    'temp': data['temperature'],
                                    'hum': data['humidity'],
                                    'time': datetime.now()
                                })
                                
                                # Храним только последние N секунд
                                time_window = datetime.now() - timedelta(seconds=TEMPERATURE_AVERAGE_WINDOW)
                                temp_buffer = [d for d in temp_buffer if d['time'] > time_window]
                                
                                # Отправляем данные на сервер
                                self.send_to_server(data)
                                
                                # Проверяем AI сообщения
                                if len(temp_buffer) > 0:
                                    # Берем последнее значение для быстрой реакции
                                    last_data = temp_buffer[-1]
                                    temp = last_data['temp']
                                    hum = last_data['hum']
                                    
                                    # Проверяем, изменились ли данные
                                    current_time = datetime.now()
                                    if self.should_send_ai_message(temp, hum) or \
                                       (current_time - last_ai_message_time).seconds >= AI_MESSAGE_INTERVAL:
                                        
                                        # Получаем AI анализ
                                        ai_result = self.get_ai_analysis(
                                            temp, 
                                            hum, 
                                            self.last_hit_count
                                        )
                                        
                                        # Добавляем hits_per_minute если его нет
                                        if 'hits_per_minute' not in ai_result:
                                            ai_result['hits_per_minute'] = self.calculate_hits_per_minute()
                                        
                                        # Отправляем в чат
                                        self.send_ai_to_chat(ai_result)
                                        
                                        # Обновляем время последнего AI сообщения
                                        last_ai_message_time = current_time
                                        
                                        # Обновляем последние значения
                                        self.last_temp = temp
                                        self.last_hum = hum
                    
                    except Exception as e:
                        print(f"❌ Ошибка обработки данных: {e}")
                
                # Показываем статус каждые N секунд
                current_time = datetime.now()
                if (current_time - last_status_time).seconds >= STATUS_UPDATE_INTERVAL:
                    hits_per_minute = self.calculate_hits_per_minute()
                    print(f"🔄 Статус: {hits_per_minute:.1f} уд/мин | Темп: {self.last_temp or 0:.1f}°C | Вл: {self.last_hum or 0:.1f}%")
                    last_status_time = current_time
                
                time.sleep(MAIN_LOOP_DELAY)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Завершение работы по команде пользователя...")
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
                print(f"⚠️ Сервер вернул код {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка отправки на сервер: {e}")
    
    def send_ai_to_chat(self, ai_result):
        """Отправка AI сообщения в чат"""
        try:
            priority = ai_result.get('priority_level', 'normal')
            
            chat_message = {
                "message": ai_result.get('ai_message', "🤖 Нет рекомендаций"),
                "type": "info",
                "parameters": {
                    "hits_per_minute": ai_result.get('hits_per_minute', 0),
                    "priority_level": priority
                }
            }
            
            # Определяем тип сообщения по приоритету
            type_mapping = {
                'critical': 'danger',
                'warning': 'warning',
                'caution': 'warning',
                'normal': 'success'
            }
            chat_message['type'] = type_mapping.get(priority, 'info')
            
            response = requests.post(AI_CHAT_URL, json=chat_message, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    msg = ai_result.get('ai_message', '')
                    short_msg = msg[:80] + "..." if len(msg) > 80 else msg
                    print(f"🤖 AI: {short_msg}")
                else:
                    print(f"⚠️ Ошибка от сервера: {data.get('message', 'Unknown error')}")
            else:
                print(f"⚠️ Не удалось отправить AI сообщение в чат (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Ошибка отправки AI в чат: {e}")
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("🔌 Последовательный порт закрыт")
        print("✅ Ресурсы очищены")

def main():
    """Основная функция"""
    processor = ArduinoDataProcessor()
    try:
        processor.process_data()
    except KeyboardInterrupt:
        print("\n✅ Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        processor.cleanup()

if __name__ == "__main__":
    main()