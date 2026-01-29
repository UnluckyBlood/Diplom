import json
from datetime import datetime
import numpy as np
from typing import List, Dict, Tuple

class AdvancedRuleBasedAI:
    def __init__(self):
        self.rules = self.load_rules()
        self.device_specs = self.load_device_specs()
        self.history = []
        
    def load_rules(self):
        """Загрузка правил для принятия решений"""
        return {
            'temperature': {
                'optimal': (20, 24),
                'normal': (18, 26),
                'warning': (26, 30),
                'danger': (30, 100)
            },
            'humidity': {
                'optimal': (40, 60),
                'normal': (30, 70),
                'warning': (70, 85),
                'danger': (85, 100)
            },
            'hits': {
                'optimal': (0, 1),
                'normal': (1, 5),
                'warning': (5, 15),
                'danger': (15, 1000)
            }
        }
    
    def load_device_specs(self):
        """Загрузка спецификации устройства"""
        # Здесь можно загрузить спецификации из файла
        return {
            'max_temperature': 35,      # Максимальная рабочая температура
            'min_temperature': 10,      # Минимальная рабочая температура
            'max_humidity': 80,         # Максимальная влажность
            'vibration_threshold': 10,  # Порог вибраций
            'device_type': 'industrial_sensor',  # Тип устройства
            'maintenance_interval': 30  # Дней между обслуживанием
        }
    
    def evaluate_trend(self, values: List[float]) -> str:
        """Оценка тренда данных"""
        if len(values) < 3:
            return "insufficient_data"
        
        # Простой расчет тренда
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        slope = coeffs[0]
        
        if slope > 0.1:
            return "rising"
        elif slope < -0.1:
            return "falling"
        else:
            return "stable"
    
    def analyze_correlation(self, temp: float, hum: float, hits: int) -> Dict:
        """Анализ корреляции параметров"""
        analysis = {
            'temperature_humidity': 'normal',
            'temperature_vibration': 'normal',
            'combined_risk': 'low'
        }
        
        # Корреляция температура-влажность
        if temp > 25 and hum > 70:
            analysis['temperature_humidity'] = 'high_risk'
            analysis['combined_risk'] = 'high'
        elif temp > 28 or hum > 75:
            analysis['temperature_humidity'] = 'medium_risk'
            analysis['combined_risk'] = 'medium'
        
        # Корреляция температура-вибрации
        if temp > 27 and hits > 5:
            analysis['temperature_vibration'] = 'high_risk'
            analysis['combined_risk'] = 'high'
        
        return analysis
    
    def generate_device_specific_recommendations(self, temp: float, hum: float, hits: int) -> List[str]:
        """Генерация рекомендаций на основе спецификации устройства"""
        recommendations = []
        
        # Проверка против спецификации устройства
        if temp > self.device_specs['max_temperature']:
            recommendations.append(f"🚨 ПРЕВЫШЕНИЕ МАКС. ТЕМПЕРАТУРЫ! {temp:.1f}°C > {self.device_specs['max_temperature']}°C")
            recommendations.append("НЕМЕДЛЕННО снизить нагрузку или охладить устройство")
        
        if hum > self.device_specs['max_humidity']:
            recommendations.append(f"💦 ПРЕВЫШЕНИЕ МАКС. ВЛАЖНОСТИ! {hum:.1f}% > {self.device_specs['max_humidity']}%")
            recommendations.append("Рекомендуется включить осушение воздуха")
        
        if hits > self.device_specs['vibration_threshold']:
            recommendations.append(f"⚡ ВИБРАЦИИ ВЫШЕ ПОРОГА! {hits} > {self.device_specs['vibration_threshold']}")
            recommendations.append("Проверьте крепление и балансировку устройства")
        
        # Оптимизационные рекомендации
        if self.device_specs['device_type'] == 'industrial_sensor':
            if 20 <= temp <= 24 and 40 <= hum <= 60:
                recommendations.append("✅ Оптимальные условия для промышленного датчика")
            elif temp < 20:
                recommendations.append("❄️ Температура ниже оптимальной для точных измерений")
        
        return recommendations
    
    def predict_failure_risk(self, temp: float, hum: float, hits: int) -> float:
        """Прогноз риска отказа оборудования"""
        risk_score = 0.0
        
        # Веса параметров
        weights = {
            'temperature': 0.4,
            'humidity': 0.3,
            'vibration': 0.3
        }
        
        # Расчет риска по температуре
        temp_risk = max(0, (temp - 25) / 10)  # 0-1, где 25°C = 0, 35°C = 1
        risk_score += temp_risk * weights['temperature']
        
        # Расчет риска по влажности
        hum_risk = max(0, (hum - 65) / 20)    # 0-1, где 65% = 0, 85% = 1
        risk_score += hum_risk * weights['humidity']
        
        # Расчет риска по вибрациям
        vib_risk = min(1, hits / 20)          # 0-1, где 20 ударов = 1
        risk_score += vib_risk * weights['vibration']
        
        # Корректировка на основе истории
        if len(self.history) > 10:
            recent_temps = [h['temperature'] for h in self.history[-5:]]
            trend = self.evaluate_trend(recent_temps)
            if trend == 'rising':
                risk_score *= 1.2
        
        return min(1.0, risk_score)
    
    def get_recommendation(self, temperature: float, humidity: float, hits: int) -> Dict:
        """Получение комплексной рекомендации"""
        try:
            # Сохраняем в историю
            self.history.append({
                'timestamp': datetime.now(),
                'temperature': temperature,
                'humidity': humidity,
                'hits': hits
            })
            
            # Ограничиваем историю
            if len(self.history) > 100:
                self.history = self.history[-100:]
            
            # Анализ параметров
            correlation = self.analyze_correlation(temperature, humidity, hits)
            device_recs = self.generate_device_specific_recommendations(temperature, humidity, hits)
            failure_risk = self.predict_failure_risk(temperature, humidity, hits)
            
            # Определение уровня опасности
            if failure_risk > 0.7 or any('🚨' in rec for rec in device_recs):
                overall_level = 'danger'
                confidence = max(0.8, failure_risk)
            elif failure_risk > 0.4 or len(device_recs) > 2:
                overall_level = 'warning'
                confidence = failure_risk
            else:
                overall_level = 'normal'
                confidence = 1.0 - failure_risk
            
            # Формирование полного списка рекомендаций
            all_recommendations = []
            
            # Общие рекомендации
            if overall_level == 'normal':
                all_recommendations.append("✅ Система работает в штатном режиме")
                all_recommendations.append(f"📊 Условия: {temperature:.1f}°C, {humidity:.1f}%")
            
            elif overall_level == 'warning':
                all_recommendations.append("⚠️ Требуется внимание к параметрам системы")
                if correlation['combined_risk'] in ['medium', 'high']:
                    all_recommendations.append("🔗 Обнаружена корреляция рисков")
            
            elif overall_level == 'danger':
                all_recommendations.append("🚨 КРИТИЧЕСКОЕ СОСТОЯНИЕ!")
                all_recommendations.append(f"📈 Риск отказа: {failure_risk:.0%}")
            
            # Добавляем специфические рекомендации
            all_recommendations.extend(device_recs)
            
            # Рекомендации по обслуживанию
            if hits > 0:
                all_recommendations.append(f"🔧 Зафиксировано вибраций: {hits}")
                if hits > 10:
                    all_recommendations.append("Рекомендуется проверить крепление устройства")
            
            # Прогноз
            if failure_risk > 0.5:
                all_recommendations.append(f"📉 Прогнозируемый риск отказа: {failure_risk:.0%}")
                if temperature > 28:
                    all_recommendations.append("Снизьте температуру для уменьшения риска")
            
            # Маппинг уровня на числовой класс
            level_map = {'normal': 0, 'warning': 1, 'danger': 2}
            
            return {
                'recommendations': all_recommendations,
                'confidence': float(confidence),
                'prediction_class': level_map[overall_level],
                'failure_risk': float(failure_risk),
                'correlation_analysis': correlation,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits': hits
                }
            }
            
        except Exception as e:
            print(f"❌ Ошибка AI: {e}")
            return {
                'recommendations': ["ИИ временно недоступен", f"Ошибка: {str(e)[:50]}"],
                'confidence': 0.0,
                'prediction_class': -1,
                'failure_risk': 0.0,
                'error': str(e)
            }

# Глобальный экземпляр
ai_instance = AdvancedRuleBasedAI()

def get_recommendation(temperature: float, humidity: float, hits: int) -> Dict:
    """Публичная функция для получения рекомендаций"""
    return ai_instance.get_recommendation(temperature, humidity, hits)

if __name__ == "__main__":
    # Тестирование
    print("🤖 ТЕСТИРОВАНИЕ AI СИСТЕМЫ")
    print("=" * 50)
    
    test_cases = [
        (22.5, 55, 0),    # Оптимальные условия
        (27.5, 72, 8),    # Предупреждение
        (32.0, 82, 20)    # Опасность
    ]
    
    for temp, hum, hits in test_cases:
        result = get_recommendation(temp, hum, hits)
        print(f"\nТемпература: {temp}°C, Влажность: {hum}%, Удары: {hits}")
        print(f"Уровень: {result['prediction_class']}, Уверенность: {result['confidence']:.1%}")
        print(f"Риск отказа: {result['failure_risk']:.1%}")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
        print("-" * 50)