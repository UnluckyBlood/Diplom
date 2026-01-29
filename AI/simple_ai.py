import json
from datetime import datetime

class SimpleRuleBasedAI:
    def __init__(self):
        self.rules = self.load_rules()
    
    def load_rules(self):
        """Загрузка правил для принятия решений"""
        return {
            'temperature': {
                'normal': (18, 25),
                'warning': (25, 30),
                'danger': (30, 50)
            },
            'humidity': {
                'normal': (30, 70),
                'warning': (70, 80),
                'danger': (80, 100)
            },
            'hits': {
                'normal': (0, 5),
                'warning': (5, 15),
                'danger': (15, 100)
            }
        }
    
    def evaluate_parameter(self, value, ranges):
        """Оценка одного параметра"""
        for level, (min_val, max_val) in ranges.items():
            if min_val <= value < max_val:
                return level
        return 'unknown'
    
    def calculate_confidence(self, levels):
        """Расчет уверенности на основе уровней"""
        level_weights = {
            'normal': 0.1,
            'warning': 0.3,
            'danger': 0.9
        }
        
        total_weight = sum(level_weights.get(level, 0) for level in levels)
        confidence = min(0.99, total_weight / len(levels))
        
        # Увеличиваем уверенность если все параметры в одном состоянии
        if all(level == levels[0] for level in levels):
            confidence = min(0.99, confidence + 0.2)
        
        return confidence
    
    def get_recommendation(self, temperature, humidity, hits):
        """Получение рекомендации на основе данных"""
        try:
            # Оценка каждого параметра
            temp_level = self.evaluate_parameter(temperature, self.rules['temperature'])
            hum_level = self.evaluate_parameter(humidity, self.rules['humidity'])
            hits_level = self.evaluate_parameter(hits, self.rules['hits'])
            
            levels = [temp_level, hum_level, hits_level]
            
            # Определение общего уровня опасности
            if 'danger' in levels:
                overall_level = 'danger'
            elif 'warning' in levels:
                overall_level = 'warning'
            else:
                overall_level = 'normal'
            
            # Расчет уверенности
            confidence = self.calculate_confidence(levels)
            
            # Генерация рекомендаций
            recommendations = []
            
            if overall_level == 'normal':
                recommendations.append("✅ Все параметры в пределах нормы")
                recommendations.append("📊 Система работает стабильно")
                
            elif overall_level == 'warning':
                recommendations.append("⚠️ Внимание! Некоторые параметры близки к критическим")
                
                if temp_level == 'warning':
                    recommendations.append(f"🌡️ Температура повышена: {temperature:.1f}°C")
                if hum_level == 'warning':
                    recommendations.append(f"💧 Влажность высокая: {humidity:.1f}%")
                if hits_level == 'warning':
                    recommendations.append(f"🔨 Обнаружены вибрации: {hits} ударов")
                    
                recommendations.append("Рекомендуется провести проверку оборудования")
                
            elif overall_level == 'danger':
                recommendations.append("🚨 КРИТИЧЕСКОЕ СОСТОЯНИЕ!")
                
                if temp_level == 'danger':
                    recommendations.append(f"🔥 ОПАСНО: Температура критически высокая! {temperature:.1f}°C")
                if hum_level == 'danger':
                    recommendations.append(f"💦 ОПАСНО: Влажность критически высокая! {humidity:.1f}%")
                if hits_level == 'danger':
                    recommendations.append(f"⚡ ОПАСНО: Сильные вибрации! {hits} ударов")
                    
                recommendations.append("НЕМЕДЛЕННО проверьте оборудование!")
                confidence = max(confidence, 0.95)
            
            # Дополнительные рекомендации
            if temperature < 18:
                recommendations.append("❄️ Низкая температура может влиять на работу оборудования")
            
            if humidity < 30:
                recommendations.append("🏜️ Низкая влажность - риск статического электричества")
            
            if hits > 0:
                recommendations.append(f"📈 Зафиксировано ударов/вибраций: {hits}")
            
            # Карта уровней для числового представления
            level_map = {'normal': 0, 'warning': 1, 'danger': 2}
            
            return {
                'recommendations': recommendations,
                'confidence': float(confidence),
                'prediction_class': level_map[overall_level],
                'timestamp': datetime.now().isoformat(),
                'levels': {
                    'temperature': temp_level,
                    'humidity': hum_level,
                    'hits': hits_level
                },
                'values': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits': hits
                }
            }
            
        except Exception as e:
            print(f"Ошибка AI: {e}")
            return {
                'recommendations': ["ИИ временно недоступен"],
                'confidence': 0.0,
                'error': str(e),
                'prediction_class': -1
            }

# Глобальный экземпляр
ai_instance = SimpleRuleBasedAI()

def get_recommendation(temperature, humidity, hits):
    return ai_instance.get_recommendation(temperature, humidity, hits)

if __name__ == "__main__":
    # Тестирование
    print("Тестирование AI системы:")
    
    test_cases = [
        (22.5, 55, 2),    # Норма
        (27.0, 75, 8),    # Предупреждение
        (32.0, 85, 18)    # Опасность
    ]
    
    for temp, hum, hits in test_cases:
        result = get_recommendation(temp, hum, hits)
        print(f"\nТемпература: {temp}°C, Влажность: {hum}%, Удары: {hits}")
        print(f"Класс: {result['prediction_class']}, Уверенность: {result['confidence']:.2%}")
        for rec in result['recommendations'][:2]:
            print(f"  • {rec}")
