"""
Тестовый скрипт для проверки Arduino без реального подключения
"""
import random
import time
from datetime import datetime
import requests

def simulate_arduino_data():
    """Симуляция данных от Arduino"""
    base_temp = 22.0
    base_hum = 55.0
    hit_chance = 0.1  # 10% шанс удара
    
    while True:
        # Немного изменяем температуру и влажность
        temp = base_temp + random.uniform(-2, 2)
        hum = base_hum + random.uniform(-5, 5)
        
        # Определяем, был ли удар
        hit_detected = random.random() < hit_chance
        hit_interval = random.randint(100, 1000) if hit_detected else 0
        
        # Увеличиваем шанс удара если долго не было
        if hit_detected:
            hit_chance = 0.1
        else:
            hit_chance = min(0.5, hit_chance + 0.01)
        
        # Отправляем данные
        data = {
            'timestamp': datetime.now().isoformat(),
            'temperature': round(temp, 1),
            'humidity': round(hum, 1),
            'hit_detected': 1 if hit_detected else 0,
            'hit_interval': hit_interval,
            'hit_count': random.randint(0, 10)
        }
        
        try:
            response = requests.post(
                'http://localhost:8000/api/data',
                json={'type': 'realtime', 'data': data},
                timeout=2
            )
            print(f"📤 Отправлено: {data['temperature']}°C, {data['humidity']}%, Удар: {hit_detected}")
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
        
        time.sleep(2)  # Интервал как у реального Arduino

if __name__ == "__main__":
    print("🧪 Тестовый симулятор Arduino")
    print("📡 Отправка данных на http://localhost:8000")
    print("Для остановки нажмите Ctrl+C\n")
    
    try:
        simulate_arduino_data()
    except KeyboardInterrupt:
        print("\n✅ Симуляция завершена")