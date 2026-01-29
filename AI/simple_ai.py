import numpy as np
from datetime import datetime, timedelta
from typing import Dict
import warnings
warnings.filterwarnings('ignore')

class ImprovedAIModel:
    """AI модель с одним сообщением в минуту"""
    
    def __init__(self):
        self.hit_timestamps = []
        self.last_total_hits = 0
        self.last_reset_time = datetime.now()
        self.last_ai_message = "🤖 AI система инициализирована"
        self.last_ai_time = datetime.now()
        self.message_cooldown = 60  # Сообщение раз в 60 секунд
        print("🤖 AI модель инициализирована (одно сообщение в минуту)")
    
    def _calculate_hits_per_minute(self, new_total_hits: int) -> float:
        """Правильный подсчет ударов в минуту"""
        current_time = datetime.now()
        
        if (current_time - self.last_reset_time).seconds > 300:
            self.hit_timestamps = []
            self.last_total_hits = new_total_hits
            self.last_reset_time = current_time
            return 0
        
        if new_total_hits < self.last_total_hits:
            self.hit_timestamps = []
            self.last_total_hits = new_total_hits
            return 0
        
        if new_total_hits > self.last_total_hits:
            hits_delta = new_total_hits - self.last_total_hits
            for _ in range(hits_delta):
                self.hit_timestamps.append(current_time)
            self.last_total_hits = new_total_hits
        
        one_minute_ago = current_time - timedelta(seconds=60)
        self.hit_timestamps = [ts for ts in self.hit_timestamps if ts > one_minute_ago]
        
        return float(len(self.hit_timestamps))
    
    def _generate_ai_message(self, temp: float, hum: float, hits_per_min: float) -> str:
        """Генерирует ОДНО интеллектуальное сообщение"""
        
        current_time = datetime.now()
        
        # Проверяем кулдаун (1 сообщение в минуту)
        if (current_time - self.last_ai_time).seconds < self.message_cooldown:
            return self.last_ai_message  # Возвращаем старое сообщение
        
        # ===== КРИТИЧЕСКИЕ СОСТОЯНИЯ =====
        if temp > 38:
            msg = f"🔴 КРИТИЧЕСКИЙ ПЕРЕГРЕВ {temp:.1f}°C! Немедленно: 1) Остановите оборудование 2) Проверьте вентиляторы 3) Очистите радиаторы"
        
        elif hum > 90:
            msg = f"🔴 КРИТИЧЕСКАЯ ВЛАЖНОСТЬ {hum:.1f}%! Немедленно: 1) Включите осушитель 2) Проверьте герметичность 3) Уберите влагу"
        
        elif hits_per_min > 40:
            msg = f"🔴 ОПАСНЫЕ ВИБРАЦИИ {hits_per_min:.1f} уд/мин! Немедленно: 1) Проверьте крепления 2) Выполните балансировку 3) Установите демпферы"
        
        # ===== ВЫСОКИЙ РИСК =====
        elif temp > 32:
            msg = f"🟠 ВЫСОКАЯ ТЕМПЕРАТУРА {temp:.1f}°C. Проверьте: 1) Вентиляцию помещения 2) Систему охлаждения 3) Радиаторы"
        
        elif hum > 75:
            msg = f"🟠 ВЫСОКАЯ ВЛАЖНОСТЬ {hum:.1f}%. Проверьте: 1) Осушитель воздуха 2) Отсутствие протечек 3) Герметичность корпуса"
        
        elif hits_per_min > 25:
            msg = f"🟠 ПОВЫШЕННЫЕ ВИБРАЦИИ {hits_per_min:.1f} уд/мин. Проверьте: 1) Крепежные винты 2) Амортизационные прокладки 3) Ровность установки"
        
        # ===== ВНИМАНИЕ =====
        elif temp > 28:
            msg = f"🟡 ТЕМПЕРАТУРА ПОВЫШЕНА {temp:.1f}°C. Рекомендации: 1) Мониторьте нагрев 2) Улучшите вентиляцию 3) Очистите от пыли"
        
        elif hum > 65:
            msg = f"🟡 ВЛАЖНОСТЬ ПОВЫШЕНА {hum:.1f}%. Рекомендации: 1) Контролируйте уровень 2) Улучшите вентиляцию 3) Проверьте осушитель"
        
        elif hits_per_min > 15:
            msg = f"🟡 ВИБРАЦИИ {hits_per_min:.1f} уд/мин. Рекомендации: 1) Проверяйте крепления 2) Установите датчики 3) Мониторьте тенденцию"
        
        # ===== ИДЕАЛЬНЫЕ УСЛОВИЯ =====
        elif 18 <= temp <= 28 and 30 <= hum <= 60 and hits_per_min <= 5:
            msg = f"✅ ИДЕАЛЬНЫЕ УСЛОВИЯ: {temp:.1f}°C, {hum:.1f}%, {hits_per_min:.1f} уд/мин. Оборудование работает оптимально"
        
        # ===== ВСЁ ХОРОШО =====
        else:
            msg = f"✅ ВСЁ ХОРОШО: {temp:.1f}°C, {hum:.1f}%, {hits_per_min:.1f} уд/мин. Продолжайте работу в обычном режиме"
        
        # Сохраняем сообщение и время
        self.last_ai_message = msg
        self.last_ai_time = current_time
        
        return msg
    
    def analyze(self, temperature: float, humidity: float, total_hits: int) -> Dict:
        """Анализ данных - возвращает ОДНО сообщение в минуту"""
        try:
            hits_per_minute = self._calculate_hits_per_minute(total_hits)
            
            # Генерируем ОДНО сообщение (с учетом кулдауна)
            ai_message = self._generate_ai_message(temperature, humidity, hits_per_minute)
            
            # Определяем приоритет для статистики
            if temperature > 38 or humidity > 90 or hits_per_minute > 40:
                priority = 'critical'
                risk_score = 0.9
            elif temperature > 32 or humidity > 75 or hits_per_minute > 25:
                priority = 'warning'
                risk_score = 0.6
            elif temperature > 28 or humidity > 65 or hits_per_minute > 15:
                priority = 'caution'
                risk_score = 0.3
            else:
                priority = 'normal'
                risk_score = 0.1
            
            return {
                'ai_message': ai_message,
                'priority_level': priority,
                'risk_score': risk_score,
                'hits_per_minute': hits_per_minute,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits_total': total_hits,
                    'hits_per_minute': hits_per_minute
                }
            }
            
        except Exception as e:
            print(f"❌ Ошибка AI анализа: {e}")
            return {
                'ai_message': "🤖 AI анализ временно недоступен",
                'priority_level': 'normal',
                'risk_score': 0.1,
                'hits_per_minute': 0,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits_total': total_hits,
                    'error': str(e)
                }
            }

# Глобальный экземпляр
ai_model = ImprovedAIModel()

def get_recommendation(temperature: float, humidity: float, hits: int) -> Dict:
    """Публичная функция - возвращает ОДНО сообщение"""
    return ai_model.analyze(temperature, humidity, hits)

if __name__ == "__main__":
    print("🧪 Тестирование AI (одно сообщение в минуту)")
    print("=" * 60)
    
    # Тест: должно выдать 5 сообщений с интервалом
    test_data = [
        (24.7, 32.2, 8),
        (39.0, 50.0, 5),    # Должно сработать критическое
        (33.0, 70.0, 10),   # Должно сработать предупреждение
        (25.0, 80.0, 30),   # Должно сработать предупреждение
        (22.0, 50.0, 2)     # Должно сказать "всё хорошо"
    ]
    
    for i, (temp, hum, hits) in enumerate(test_data, 1):
        print(f"\n📊 Тест {i}: {temp}°C, {hum}%, {hits} ударов")
        result = get_recommendation(temp, hum, hits)
        print(f"🤖 Сообщение: {result['ai_message']}")
        print(f"📈 Уровень: {result['priority_level']}")
        print(f"⚠️  Риск: {result['risk_score']*100:.0f}%")
        if i < len(test_data):
            print("⏳ Имитация ожидания 30 секунд...")