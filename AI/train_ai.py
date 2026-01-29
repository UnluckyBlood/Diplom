import numpy as np
import pandas as pd
import joblib
import pickle
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime
import os
from pathlib import Path

class SimpleAI:
    def __init__(self, model_path: str = "ai_model.pkl"):
        self.model = None
        self.model_path = model_path
        self.load_or_train_model()
    
    def load_or_train_model(self):
        """Загрузка или обучение модели"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                print("ИИ модель загружена")
                return
            except Exception as e:
                print(f"Ошибка загрузки модели: {e}, создаем новую...")
        
        # Создаем простую модель на синтетических данных
        self.train_simple_model()
    
    def train_simple_model(self):
        """Обучение простой модели на синтетических данных"""
        # Создаем синтетические данные
        np.random.seed(42)
        n_samples = 1000
        
        # Температура: 15-35°C
        temperature = np.random.uniform(15, 35, n_samples)
        
        # Влажность: 20-90%
        humidity = np.random.uniform(20, 90, n_samples)
        
        # Количество ударов: 0-20
        hits = np.random.randint(0, 21, n_samples)
        
        # Создаем целевые переменные (рекомендации)
        # 0: всё нормально, 1: предупреждение, 2: опасность
        labels = []
        
        for i in range(n_samples):
            t = temperature[i]
            h = humidity[i]
            hit = hits[i]
            
            if t > 30 or h > 80 or hit > 15:
                labels.append(2)  # Опасность
            elif t > 25 or h > 70 or hit > 5:
                labels.append(1)  # Предупреждение
            else:
                labels.append(0)  # Норма
            
        # Подготовка данных
        X = np.column_stack([temperature, humidity, hits])
        y = np.array(labels)
        
        # Обучение модели
        self.model = RandomForestClassifier(
            n_estimators=50, 
            random_state=42,
            max_depth=10
        )
        self.model.fit(X, y)
        
        # Сохранение модели
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        print("ИИ модель обучена и сохранена")
    
    def get_recommendation(self, temperature: float, humidity: float, hits: int):
        """Получение рекомендации на основе данных"""
        try:
            # Подготовка входных данных
            X = np.array([[temperature, humidity, hits]])
            
            # Предсказание
            prediction = self.model.predict(X)[0]
            
            # Получаем вероятности
            probabilities = self.model.predict_proba(X)[0]
            confidence = float(np.max(probabilities))
            
            # Генерация рекомендаций
            recommendations = []
            
            if prediction == 0:  # Норма
                recommendations.append("✅ Все параметры в пределах нормы")
                recommendations.append("📊 Система работает стабильно")
                
            elif prediction == 1:  # Предупреждение
                recommendations.append("⚠️ Внимание! Некоторые параметры близки к критическим")
                
                if temperature > 25:
                    recommendations.append("🌡️ Температура повышена")
                if humidity > 70:
                    recommendations.append("💧 Влажность высокая")
                if hits > 5:
                    recommendations.append("🔨 Обнаружены вибрации")
                    
                recommendations.append("Рекомендуется провести проверку оборудования")
                
            elif prediction == 2:  # Опасность
                recommendations.append("🚨 КРИТИЧЕСКОЕ СОСТОЯНИЕ!")
                
                if temperature > 30:
                    recommendations.append("🔥 ОПАСНО: Температура критически высокая!")
                if humidity > 80:
                    recommendations.append("💦 ОПАСНО: Влажность критически высокая!")
                if hits > 15:
                    recommendations.append("⚡ ОПАСНО: Сильные вибрации!")
                    
                recommendations.append("НЕМЕДЛЕННО проверьте оборудование!")
                confidence = max(confidence, 0.95)  # Минимальная уверенность для опасности
            
            # Дополнительные рекомендации на основе конкретных значений
            if temperature < 18:
                recommendations.append("❄️ Низкая температура может влиять на работу оборудования")
            
            if humidity < 30:
                recommendations.append("🏜️ Низкая влажность - риск статического электричества")
            
            if hits > 0:
                recommendations.append(f"📈 Зафиксировано ударов/вибраций: {hits}")
            
            return {
                'recommendations': recommendations,
                'confidence': confidence,
                'prediction_class': int(prediction),
                'timestamp': datetime.now().isoformat(),
                'probabilities': probabilities.tolist()
            }
            
        except Exception as e:
            print(f"Ошибка ИИ: {e}")
            return {
                'recommendations': ["ИИ временно недоступен"],
                'confidence': 0.0,
                'error': str(e),
                'prediction_class': -1
            }

# Глобальный экземпляр ИИ
ai_instance = SimpleAI()

def get_recommendation(temperature: float, humidity: float, hits: int):
    """Функция для импорта из других модулей"""
    return ai_instance.get_recommendation(temperature, humidity, hits)

def retrain_model(new_data=None):
    """Переобучение модели с новыми данными"""
    print("Переобучение модели...")
    ai_instance.train_simple_model()
    return True

if __name__ == "__main__":
    # Тестирование модели
    print("Тестирование ИИ модели:")
    
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