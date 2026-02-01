import numpy as np
from datetime import datetime, timedelta
from typing import Dict
import warnings
warnings.filterwarnings('ignore')

# КОНСТАНТЫ ДЛЯ ТЕМПЕРАТУРЫ
TEMP_CRITICAL_HIGH = 38.0      # Критический перегрев
TEMP_WARNING_HIGH = 32.0       # Высокая температура
TEMP_CAUTION_HIGH = 28.0       # Повышенная температура

# КОНСТАНТЫ ДЛЯ ВЛАЖНОСТИ
HUMIDITY_CRITICAL_HIGH = 90.0  # Критическая влажность
HUMIDITY_WARNING_HIGH = 75.0   # Высокая влажность
HUMIDITY_CAUTION_HIGH = 65.0   # Повышенная влажность

# КОНСТАНТЫ ДЛЯ ВИБРАЦИЙ
VIBRATION_CRITICAL_HIGH = 40.0 # Критические вибрации
VIBRATION_WARNING_HIGH = 25.0  # Высокие вибрации
VIBRATION_CAUTION_HIGH = 15.0  # Повышенные вибрации

class SimpleAIModel:
    """Простая AI модель с мгновенной реакцией"""
    
    def __init__(self):
        self.hit_timestamps = []
        self.last_total_hits = 0
        self.last_status = "unknown"
        
        print("🤖 Простая AI модель инициализирована (мгновенная реакция)")
    
    def _calculate_hits_per_minute(self, new_total_hits: int) -> float:
        """Подсчет ударов в минуту"""
        current_time = datetime.now()
        
        # Если счетчик сброшен
        if new_total_hits < self.last_total_hits:
            self.hit_timestamps = [current_time] * new_total_hits
            self.last_total_hits = new_total_hits
            return float(new_total_hits)
        
        # Добавляем новые удары
        if new_total_hits > self.last_total_hits:
            hits_delta = new_total_hits - self.last_total_hits
            for _ in range(hits_delta):
                self.hit_timestamps.append(current_time)
            self.last_total_hits = new_total_hits
        
        # Оставляем только удары за последнюю минуту
        one_minute_ago = current_time - timedelta(seconds=60)
        self.hit_timestamps = [ts for ts in self.hit_timestamps if ts > one_minute_ago]
        
        return float(len(self.hit_timestamps))
    
    def analyze(self, temperature: float, humidity: float, total_hits: int) -> Dict:
        """Анализ данных - мгновенная реакция"""
        try:
            hits_per_minute = self._calculate_hits_per_minute(total_hits)
            
            # Определяем статус
            status = "normal"
            priority = "normal"
            risk_score = 0.1
            
            # КРИТИЧЕСКИЙ статус
            if (temperature > TEMP_CRITICAL_HIGH or 
                humidity > HUMIDITY_CRITICAL_HIGH or 
                hits_per_minute > VIBRATION_CRITICAL_HIGH):
                
                status = "critical"
                priority = "critical"
                risk_score = 0.9
                
                if temperature > TEMP_CRITICAL_HIGH:
                    message = f"🚨 КРИТИЧЕСКИЙ ПЕРЕГРЕВ {temperature:.1f}°C! Немедленно остановите оборудование!"
                elif humidity > HUMIDITY_CRITICAL_HIGH:
                    message = f"🚨 КРИТИЧЕСКАЯ ВЛАЖНОСТЬ {humidity:.1f}%! Риск образования конденсата!"
                else:
                    message = f"🚨 ОПАСНЫЕ ВИБРАЦИИ {hits_per_minute:.1f} уд/мин! Немедленно остановите оборудование!"
            
            # ВЫСОКИЙ РИСК
            elif (temperature > TEMP_WARNING_HIGH or 
                  humidity > HUMIDITY_WARNING_HIGH or 
                  hits_per_minute > VIBRATION_WARNING_HIGH):
                
                status = "warning"
                priority = "warning"
                risk_score = 0.6
                
                if temperature > TEMP_WARNING_HIGH:
                    message = f"⚠️ ВЫСОКАЯ ТЕМПЕРАТУРА {temperature:.1f}°C. Проверьте систему охлаждения."
                elif humidity > HUMIDITY_WARNING_HIGH:
                    message = f"⚠️ ВЫСОКАЯ ВЛАЖНОСТЬ {humidity:.1f}%. Включите осушитель."
                else:
                    message = f"⚠️ ПОВЫШЕННЫЕ ВИБРАЦИИ {hits_per_minute:.1f} уд/мин. Проверьте крепления."
            
            # ВНИМАНИЕ
            elif (temperature > TEMP_CAUTION_HIGH or 
                  humidity > HUMIDITY_CAUTION_HIGH or 
                  hits_per_minute > VIBRATION_CAUTION_HIGH):
                
                status = "caution"
                priority = "caution"
                risk_score = 0.3
                
                if temperature > TEMP_CAUTION_HIGH:
                    message = f"📈 Температура повышена {temperature:.1f}°C. Мониторьте нагрев."
                elif humidity > HUMIDITY_CAUTION_HIGH:
                    message = f"📈 Влажность повышена {humidity:.1f}%. Увеличьте вентиляцию."
                else:
                    message = f"📈 Вибрации {hits_per_minute:.1f} уд/мин. Проверяйте состояние."
            
            # НОРМАЛЬНЫЙ статус
            else:
                status = "normal"
                priority = "normal"
                risk_score = 0.1
                
                # Разные сообщения для нормального статуса
                if self.last_status != "normal":
                    message = f"✅ Показатели нормализовались: {temperature:.1f}°C, {humidity:.1f}%"
                else:
                    message = f"✅ Нормальные показатели: {temperature:.1f}°C, {humidity:.1f}%, {hits_per_minute:.1f} уд/мин"
            
            self.last_status = status
            
            return {
                'ai_message': message,
                'priority_level': priority,
                'risk_score': risk_score,
                'hits_per_minute': hits_per_minute,
                'status_changed': True,  # Всегда True для мгновенной реакции
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits_total': total_hits,
                    'hits_per_minute': hits_per_minute,
                    'status': status
                }
            }
            
        except Exception as e:
            print(f"❌ Ошибка AI анализа: {e}")
            return {
                'ai_message': "🤖 AI анализ выполнен",
                'priority_level': "normal",
                'risk_score': 0.1,
                'hits_per_minute': 0.0,
                'status_changed': True,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits_total': total_hits,
                    'error': str(e)
                }
            }

# Глобальный экземпляр
ai_model = SimpleAIModel()

def get_recommendation(temperature: float, humidity: float, hits: int) -> Dict:
    """Публичная функция - мгновенная реакция"""
    return ai_model.analyze(temperature, humidity, hits)

if __name__ == "__main__":
    print("🧪 Тестирование AI (мгновенная реакция)")
    
    # Тест: различные сценарии
    test_data = [
        (24.7, 32.2, 8),    # Норма
        (33.0, 70.0, 10),   # Предупреждение
        (39.5, 50.0, 8),    # Критическая температура
        (25.0, 80.0, 30),   # Высокая влажность
    ]
    
    for i, (temp, hum, hits) in enumerate(test_data, 1):
        print(f"\n📊 Тест {i}: {temp}°C, {hum}%, {hits} ударов")
        result = get_recommendation(temp, hum, hits)
        print(f"🤖 Сообщение: {result['ai_message']}")
        print(f"⚠️  Приоритет: {result['priority_level']}")