import json
from datetime import datetime
import numpy as np
from typing import List, Dict, Optional
import os
import warnings
warnings.filterwarnings('ignore')

class IndustrialEquipmentAI:
    """AI для промышленного оборудования с конкретными рекомендациями"""
    
    def __init__(self, spec_path: Optional[str] = None):
        self.device_specs = self._load_device_specs(spec_path)
        self.equipment_database = self._load_equipment_database()
        self.history = []
        self.failure_cases = []
        print("🤖 AI для промышленного оборудования инициализирован")
    
    def _load_device_specs(self, spec_path: Optional[str]) -> Dict:
        """Загрузка спецификации устройства"""
        default_specs = {
            'device_type': 'Industrial_Vibration_Monitor',
            'equipment_model': 'VibroSense-5000',
            'installation_date': '2024-01-01',
            'max_temperature': 35.0,
            'optimal_temperature': (20, 25),
            'max_humidity': 85.0,
            'optimal_humidity': (40, 60),
            'vibration_threshold': 12,
            'power_rating': '24V DC, 2A',
            'operating_hours': 1500
        }
        
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, 'r', encoding='utf-8') as f:
                    custom_specs = json.load(f)
                    merged = {**default_specs, **custom_specs}
                    print(f"✅ Загружена спецификация: {merged.get('equipment_model', 'unknown')}")
                    return merged
            except Exception as e:
                print(f"⚠️ Ошибка загрузки спецификации: {e}")
        
        return default_specs
    
    def _load_equipment_database(self) -> Dict:
        """База данных компонентов оборудования и возможных поломок"""
        return {
            'cooling_system': {
                'components': [
                    {
                        'name': 'Вентилятор охлаждения',
                        'check_points': [
                            'Проверить вращение лопастей',
                            'Измерить скорость вращения (должна быть 2500-3000 RPM)',
                            'Проверить подшипники на шум',
                            'Очистить от пыли и загрязнений'
                        ],
                        'failure_modes': [
                            'Заклинивание подшипника → перегрев процессора',
                            'Обрыв обмотки двигателя → остановка вентилятора',
                            'Накопление пыли → снижение эффективности на 40%'
                        ],
                        'symptoms': ['высокая температура', 'шум вентилятора'],
                        'repair_time': '1-2 часа',
                        'spare_part': 'Вентилятор 80x80mm, 12V'
                    },
                    {
                        'name': 'Радиатор',
                        'check_points': [
                            'Проверить тепловой контакт с процессором',
                            'Очистить рёбра радиатора от пыли',
                            'Проверить состояние термопасты',
                            'Измерить температуру поверхности'
                        ],
                        'failure_modes': [
                            'Отслоение термопасты → тепловое сопротивление +30%',
                            'Загрязнение рёбер → снижение теплоотдачи на 50%',
                            'Деформация основания → неравномерный нагрев'
                        ],
                        'symptoms': ['локальный перегрев', 'нестабильная температура'],
                        'repair_time': '30 минут',
                        'spare_part': 'Термопаста MX-4, радиатор медный'
                    }
                ],
                'system_effects': 'Перегрев может привести к отказу процессора, сбоям памяти, сокращению срока службы на 60%'
            },
            
            'power_supply': {
                'components': [
                    {
                        'name': 'Блок питания 24V',
                        'check_points': [
                            'Измерить выходное напряжение (должно быть 24V ±5%)',
                            'Проверить пульсации напряжения (<100mV)',
                            'Измерить температуру корпуса (<60°C)',
                            'Проверить электролитические конденсаторы на вздутие'
                        ],
                        'failure_modes': [
                            'Вздутие конденсаторов → увеличение пульсаций',
                            'Перегрев стабилизатора → нестабильное напряжение',
                            'Пробой диодов → короткое замыкание'
                        ],
                        'symptoms': ['нестабильная работа', 'шум в аудиовыходе'],
                        'repair_time': '2-3 часа',
                        'spare_part': 'Конденсатор 1000μF 35V, стабилизатор LM317'
                    },
                    {
                        'name': 'Кабели питания',
                        'check_points': [
                            'Проверить целостность изоляции',
                            'Проверить контакты на окисление',
                            'Измерить сопротивление контактов (<0.1Ω)',
                            'Проверить нагрев в точках соединения'
                        ],
                        'failure_modes': [
                            'Окисление контактов → увеличение сопротивления',
                            'Нарушение изоляции → короткое замыкание',
                            'Перелом жил → прерывистый контакт'
                        ],
                        'symptoms': ['падение напряжения', 'искрение'],
                        'repair_time': '1 час',
                        'spare_part': 'Кабель AWG18, клеммы WAGO'
                    }
                ],
                'system_effects': 'Нестабильное питание вызывает сбои АЦП, ошибки измерений, перезагрузки системы'
            },
            
            'vibration_sensors': {
                'components': [
                    {
                        'name': 'Акселерометр ADXL345',
                        'check_points': [
                            'Проверить калибровку нулевого смещения',
                            'Проверить чувствительность (256 LSB/g)',
                            'Проверить соединение по I2C',
                            'Измерить собственный шум датчика'
                        ],
                        'failure_modes': [
                            'Дрейф нуля → постоянное смещение сигнала',
                            'Потеря чувствительности → недооценка вибраций',
                            'Обрыв контактов → полный отказ датчика'
                        ],
                        'symptoms': ['постоянное смещение', 'заниженные показания'],
                        'repair_time': '1 час',
                        'spare_part': 'Датчик ADXL345, разъем 4-pin'
                    },
                    {
                        'name': 'Крепление датчика',
                        'check_points': [
                            'Проверить затяжку крепежных винтов',
                            'Проверить целостность изоляционной прокладки',
                            'Проверить ориентацию датчика',
                            'Проверить на наличие коррозии'
                        ],
                        'failure_modes': [
                            'Ослабление крепления → занижение амплитуды вибраций',
                            'Коррозия контактов → увеличение сопротивления',
                            'Деформация прокладки → изменение частотной характеристики'
                        ],
                        'symptoms': ['необычные резонансы', 'дребезг сигнала'],
                        'repair_time': '30 минут',
                        'spare_part': 'Винты M3, изоляционная прокладка'
                    }
                ],
                'system_effects': 'Некорректные показания вибраций могут пропустить критическое состояние оборудования'
            },
            
            'environmental_sensors': {
                'components': [
                    {
                        'name': 'Датчик температуры DHT22',
                        'check_points': [
                            'Проверить калибровку (погрешность ±0.5°C)',
                            'Очистить от пыли защитный колпачок',
                            'Проверить вентиляцию вокруг датчика',
                            'Сравнить с эталонным термометром'
                        ],
                        'failure_modes': [
                            'Загрязнение сенсора → задержка отклика',
                            'Конденсация влаги → коррозия контактов',
                            'Старение сенсора → увеличение погрешности'
                        ],
                        'symptoms': ['медленный отклик', 'систематическая ошибка'],
                        'repair_time': '30 минут',
                        'spare_part': 'Датчик DHT22, защитный корпус'
                    },
                    {
                        'name': 'Датчик влажности',
                        'check_points': [
                            'Проверить калибровку при 50% RH',
                            'Очистить сенсорную поверхность',
                            'Проверить защиту от прямого попадания влаги',
                            'Проверить время отклика (<5 сек)'
                        ],
                        'failure_modes': [
                            'Загрязнение полимерного сенсора → нелинейная характеристика',
                            'Проникновение влаги → короткое замыкание',
                            'Старение материала → дрейф показаний'
                        ],
                        'symptoms': ['нелинейность показаний', 'долгий отклик'],
                        'repair_time': '30 минут',
                        'spare_part': 'Датчик влажности HIH-4000'
                    }
                ],
                'system_effects': 'Неточные температурные данные приводят к неправильной оценке состояния оборудования'
            },
            
            'electronics': {
                'components': [
                    {
                        'name': 'Микроконтроллер Arduino',
                        'check_points': [
                            'Проверить тактовую частоту (16MHz)',
                            'Измерить напряжение питания (5V ±5%)',
                            'Проверить температуру кристалла (<85°C)',
                            'Проверить стабильность опорного напряжения'
                        ],
                        'failure_modes': [
                            'Перегрев кристалла → сбои в вычислениях',
                            'Нестабильное питание → ошибки АЦП',
                            'Пробой портов ввода-вывода → потеря каналов'
                        ],
                        'symptoms': ['случайные сбросы', 'ошибки вычислений'],
                        'repair_time': '1-2 часа',
                        'spare_part': 'Arduino Nano, кварц 16MHz'
                    },
                    {
                        'name': 'Плата коммутации',
                        'check_points': [
                            'Проверить пайку на предмет трещин',
                            'Проверить дорожки на окисление',
                            'Проверить разъемы на люфт',
                            'Проверить изоляцию между слоями'
                        ],
                        'failure_modes': [
                            'Трещины пайки → прерывистый контакт',
                            'Окисление дорожек → увеличение сопротивления',
                            'Деформация платы → обрыв контактов'
                        ],
                        'symptoms': ['прерывистая работа', 'плавающие неисправности'],
                        'repair_time': '2-3 часа',
                        'spare_part': 'PCB плата, разъемы'
                    }
                ],
                'system_effects': 'Сбои электроники приводят к полной остановке системы мониторинга'
            }
        }
    
    def analyze_high_temperature(self, temp: float, trend: str) -> List[str]:
        """Анализ при высокой температуре"""
        recommendations = []
        
        if temp > 35:
            recommendations.append("🔥 КРИТИЧЕСКАЯ ТЕМПЕРАТУРА! НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:")
            recommendations.append("1. ОСТАНОВИТЕ оборудование если возможно")
            recommendations.append("2. Включите дополнительное охлаждение")
            recommendations.append("3. Проверьте следующие компоненты В ПЕРВУЮ ОЧЕРЕДЬ:")
        elif temp > 30:
            recommendations.append("🌡️  ВЫСОКАЯ ТЕМПЕРАТУРА - ТРЕБУЕТСЯ ПРОВЕРКА:")
        else:
            return []
        
        # Конкретные проверки для системы охлаждения
        cooling = self.equipment_database['cooling_system']
        recommendations.append("")
        recommendations.append("❄️ СИСТЕМА ОХЛАЖДЕНИЯ:")
        
        for component in cooling['components']:
            recommendations.append(f"  📍 {component['name']}:")
            for check in component['check_points'][:2]:  # Первые 2 самые важные
                recommendations.append(f"    • {check}")
        
        recommendations.append("")
        recommendations.append("⚠️ ВОЗМОЖНЫЕ ПОЛОМКИ ПРИ ПЕРЕГРЕВЕ:")
        for component in cooling['components']:
            for failure in component['failure_modes'][:1]:  # Самая критичная
                recommendations.append(f"  • {component['name']}: {failure}")
        
        recommendations.append("")
        recommendations.append("🔧 ЗАПЧАСТИ ДЛЯ РЕМОНТА:")
        for component in cooling['components']:
            recommendations.append(f"  • {component['name']}: {component['spare_part']}")
        
        recommendations.append("")
        recommendations.append(f"⏱️  ВРЕМЯ РЕМОНТА: {cooling['components'][0]['repair_time']}")
        recommendations.append(f"📋 СИСТЕМНЫЕ ЭФФЕКТЫ: {cooling['system_effects']}")
        
        return recommendations
    
    def analyze_high_vibration(self, vib: int, threshold: int) -> List[str]:
        """Анализ при высоких вибрациях"""
        recommendations = []
        
        if vib > threshold * 2:
            recommendations.append("⚡ ОПАСНЫЕ ВИБРАЦИИ! НЕМЕДЛЕННЫЙ ОСМОТР:")
            recommendations.append("1. ПРОВЕРЬТЕ балансировку вращающихся частей")
            recommendations.append("2. ЗАТЯНИТЕ все крепежные элементы")
            recommendations.append("3. ВЫЯСНИТЕ источник вибраций:")
        elif vib > threshold:
            recommendations.append("⚡ ПОВЫШЕННЫЕ ВИБРАЦИИ - ТРЕБУЕТСЯ ДИАГНОСТИКА:")
        else:
            return []
        
        # Конкретные проверки для датчиков вибрации
        sensors = self.equipment_database['vibration_sensors']
        recommendations.append("")
        recommendations.append("📡 ДАТЧИКИ ВИБРАЦИИ:")
        
        for component in sensors['components']:
            recommendations.append(f"  📍 {component['name']}:")
            for check in component['check_points'][:2]:
                recommendations.append(f"    • {check}")
        
        recommendations.append("")
        recommendations.append("⚠️ ВОЗМОЖНЫЕ ПРИЧИНЫ ВИБРАЦИЙ:")
        recommendations.append("  • Разбалансировка ротора электродвигателя")
        recommendations.append("  • Износ подшипников качения")
        recommendations.append("  • Ослабление крепления оборудования")
        recommendations.append("  • Резонанс конструкции")
        
        recommendations.append("")
        recommendations.append("🔧 ЗАПЧАСТИ ДЛЯ КРЕПЛЕНИЯ:")
        recommendations.append("  • Винты M3 с контргайками")
        recommendations.append("  • Демпфирующие прокладки")
        recommendations.append("  • Амортизаторы вибраций")
        
        return recommendations
    
    def analyze_high_humidity(self, hum: float) -> List[str]:
        """Анализ при высокой влажности"""
        recommendations = []
        
        if hum > 85:
            recommendations.append("💦 КРИТИЧЕСКАЯ ВЛАЖНОСТЬ! РИСК КОРОЗИИ:")
            recommendations.append("1. ВКЛЮЧИТЕ осушитель воздуха")
            recommendations.append("2. ПРОВЕРЬТЕ герметичность корпуса")
            recommendations.append("3. ОСМОТРИТЕ электронные компоненты:")
        elif hum > 75:
            recommendations.append("💦 ПОВЫШЕННАЯ ВЛАЖНОСТЬ - ПРОВЕРКА ГЕРМЕТИЧНОСТИ:")
        else:
            return []
        
        # Конкретные проверки для защиты от влаги
        env_sensors = self.equipment_database['environmental_sensors']
        recommendations.append("")
        recommendations.append("🛡️  ЗАЩИТА ОТ ВЛАГИ:")
        
        for component in env_sensors['components']:
            recommendations.append(f"  📍 {component['name']}:")
            recommendations.append(f"    • {component['check_points'][2]}")  # Защита от влаги
        
        recommendations.append("")
        recommendations.append("⚠️ РИСКИ ПРИ ВЫСОКОЙ ВЛАЖНОСТИ:")
        recommendations.append("  • Коррозия контактов и дорожек платы")
        recommendations.append("  • Короткое замыкание между компонентами")
        recommendations.append("  • Образование конденсата на сенсорах")
        recommendations.append("  • Ускоренное старение изоляции")
        
        recommendations.append("")
        recommendations.append("🔧 МЕРЫ ЗАЩИТЫ:")
        recommendations.append("  • Нанесение конформного покрытия на платы")
        recommendations.append("  • Установка силикагелевых осушителей")
        recommendations.append("  • Герметизация разъемов")
        
        return recommendations
    
    def calculate_trend(self, values: List[float]) -> str:
        """Расчет тренда"""
        if len(values) < 3:
            return "недостаточно данных"
        
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.1:
            return "рост"
        elif slope < -0.1:
            return "спад"
        else:
            return "стабильно"
    
    def predict_failure_risk(self, temp: float, hum: float, vib: int) -> float:
        """Прогноз риска отказа"""
        risk_score = 0.0
        
        # Температурный риск
        if temp > 35:
            temp_risk = 0.8 + min(0.2, (temp - 35) / 10)
        elif temp > 30:
            temp_risk = 0.5 + (temp - 30) / 10
        elif temp > 25:
            temp_risk = 0.2 + (temp - 25) / 10
        else:
            temp_risk = 0.0
        
        # Риск влажности
        if hum > 85:
            hum_risk = 0.7 + min(0.3, (hum - 85) / 15)
        elif hum > 75:
            hum_risk = 0.4 + (hum - 75) / 20
        elif hum > 65:
            hum_risk = 0.2 + (hum - 65) / 20
        else:
            hum_risk = 0.0
        
        # Риск вибраций
        threshold = self.device_specs.get('vibration_threshold', 12)
        if vib > threshold * 2:
            vib_risk = 0.8 + min(0.2, (vib - threshold * 2) / 20)
        elif vib > threshold:
            vib_risk = 0.5 + (vib - threshold) / threshold
        else:
            vib_risk = 0.0
        
        # Взвешенная сумма
        risk_score = (temp_risk * 0.4) + (hum_risk * 0.3) + (vib_risk * 0.3)
        
        return min(1.0, risk_score)
    
    def get_recommendation(self, temperature: float, humidity: float, hits: int) -> Dict:
        """Получение детальных рекомендаций по оборудованию"""
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
                self.history = self.history[-50:]
            
            # Анализ трендов
            trend_analysis = {}
            if len(self.history) > 5:
                recent_temps = [h['temperature'] for h in self.history[-5:]]
                recent_hums = [h['humidity'] for h in self.history[-5:]]
                
                trend_analysis = {
                    'temperature_trend': self.calculate_trend(recent_temps),
                    'humidity_trend': self.calculate_trend(recent_hums),
                    'avg_temperature_5min': np.mean(recent_temps) if recent_temps else 0,
                    'avg_humidity_5min': np.mean(recent_hums) if recent_hums else 0
                }
            
            # Расчет риска
            failure_risk = self.predict_failure_risk(temperature, humidity, hits)
            
            # Анализ по условиям
            all_recommendations = []
            
            # Основное состояние
            if failure_risk > 0.7:
                all_recommendations.append("🔴 КРИТИЧЕСКИЙ УРОВЕНЬ ОПАСНОСТИ!")
                all_recommendations.append("НЕМЕДЛЕННОЕ ВМЕШАТЕЛЬСТВО ТРЕБУЕТСЯ")
                severity = "critical"
            elif failure_risk > 0.5:
                all_recommendations.append("🟠 ВЫСОКИЙ УРОВЕНЬ ОПАСНОСТИ")
                all_recommendations.append("СРОЧНАЯ ПРОВЕРКА ОБОРУДОВАНИЯ")
                severity = "high"
            elif failure_risk > 0.3:
                all_recommendations.append("🟡 СРЕДНИЙ УРОВЕНЬ ОПАСНОСТИ")
                all_recommendations.append("РЕКОМЕНДУЕТСЯ ПРОФИЛАКТИКА")
                severity = "medium"
            else:
                all_recommendations.append("🟢 НОРМАЛЬНЫЙ УРОВЕНЬ")
                all_recommendations.append("СИСТЕМА РАБОТАЕТ ШТАТНО")
                severity = "low"
            
            all_recommendations.append("")
            all_recommendations.append("📊 ТЕКУЩИЕ ПОКАЗАНИЯ:")
            all_recommendations.append(f"  • Температура: {temperature:.1f}°C")
            all_recommendations.append(f"  • Влажность: {humidity:.1f}%")
            all_recommendations.append(f"  • Вибрации: {hits} ударов")
            all_recommendations.append(f"  • Риск отказа: {failure_risk:.1%}")
            
            # Конкретные рекомендации в зависимости от условий
            if temperature > 30 or failure_risk > 0.5:
                temp_recs = self.analyze_high_temperature(temperature, 
                                                         trend_analysis.get('temperature_trend', 'стабильно'))
                all_recommendations.extend(temp_recs)
            
            if hits > self.device_specs.get('vibration_threshold', 12):
                vib_recs = self.analyze_high_vibration(hits, 
                                                      self.device_specs.get('vibration_threshold', 12))
                all_recommendations.extend(vib_recs)
            
            if humidity > 75:
                hum_recs = self.analyze_high_humidity(humidity)
                all_recommendations.extend(hum_recs)
            
            # Если нет конкретных проблем, но есть риск
            if len(all_recommendations) <= 8 and failure_risk > 0.3:
                all_recommendations.append("")
                all_recommendations.append("🔍 ОБЩИЕ РЕКОМЕНДАЦИИ ПО ТЕХОБСЛУЖИВАНИЮ:")
                all_recommendations.append("1. Проведите визуальный осмотр оборудования")
                all_recommendations.append("2. Проверьте журналы ошибок системы")
                all_recommendations.append("3. Выполните тестовые измерения")
                all_recommendations.append("4. Обновите журнал технического обслуживания")
            
            # Маппинг уровня на числовой класс
            level_map = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            
            return {
                'recommendations': all_recommendations,
                'confidence': max(0.6, 1.0 - failure_risk),
                'prediction_class': level_map[severity],
                'failure_risk': failure_risk,
                'severity_level': severity,
                'trend_analysis': trend_analysis,
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'hits': hits,
                    'equipment_model': self.device_specs.get('equipment_model', 'unknown'),
                    'operating_hours': self.device_specs.get('operating_hours', 0)
                }
            }
            
        except Exception as e:
            print(f"❌ Ошибка AI анализа: {e}")
            return {
                'recommendations': [f"ИИ временно недоступен: {str(e)[:50]}"],
                'confidence': 0.0,
                'prediction_class': -1,
                'failure_risk': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Глобальный экземпляр
spec_path = os.path.join(os.path.dirname(__file__), 'device_specs.json')
ai_instance = IndustrialEquipmentAI(spec_path=spec_path)

def get_recommendation(temperature: float, humidity: float, hits: int) -> Dict:
    """Публичная функция для получения рекомендаций"""
    return ai_instance.get_recommendation(temperature, humidity, hits)

if __name__ == "__main__":
    # Тестирование
    print("🤖 ТЕСТИРОВАНИЕ AI ДЛЯ ПРОМЫШЛЕННОГО ОБОРУДОВАНИЯ")
    print("=" * 70)
    
    test_cases = [
        (22.5, 55, 0),      # Нормальные условия
        (28.5, 72, 8),      # Средний риск
        (32.0, 82, 15),     # Высокий риск (температура)
        (25.0, 65, 25),     # Высокий риск (вибрации)
        (38.0, 88, 30)      # Критический риск
    ]
    
    for temp, hum, hits in test_cases:
        result = get_recommendation(temp, hum, hits)
        print(f"\n{'='*70}")
        print(f"🌡️  {temp}°C | 💧 {hum}% | ⚡ {hits} ударов")
        print(f"{'='*70}")
        print(f"Уровень опасности: {result['severity_level'].upper()}")
        print(f"Риск отказа: {result['failure_risk']:.1%}")
        print("\nРЕКОМЕНДАЦИИ:")
        for rec in result['recommendations']:
            print(f"  {rec}")