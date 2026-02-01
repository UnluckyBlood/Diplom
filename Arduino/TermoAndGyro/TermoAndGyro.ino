#include "DHT.h"

// КОНСТАНТЫ ПИНОВ
#define DHT_PIN 2
#define MOTION_PIN 5

// КОНСТАНТЫ ВРЕМЕНИ
#define TEMP_READ_INTERVAL_MS 2000  // Чтение температуры каждые 2 секунды
#define HIT_RESET_INTERVAL_MS 600000 // Сброс счетчика каждые 10 минут
#define DEBOUNCE_DELAY_MS 50
#define HOLD_DELAY_MS 10
#define MAIN_LOOP_DELAY_MS 10

DHT dht(DHT_PIN, DHT11);

// ПЕРЕМЕННЫЕ ДЛЯ УДАРОВ
unsigned long lastHitTime = 0;
unsigned long timeBetweenHits = 0;
unsigned long lastTempTime = 0;
int hitCount = 0;

// ПЕРЕМЕННЫЕ ДЛЯ ТЕМПЕРАТУРЫ
float lastTemperature = 0;
float lastHumidity = 0;

void setup() {
  pinMode(MOTION_PIN, INPUT_PULLUP);
  dht.begin();
  Serial.begin(9600);
  Serial.println("System started");
}

void loop() {
  // ОБРАБОТКА УДАРОВ/ВИБРАЦИИ
  if (digitalRead(MOTION_PIN) == LOW) {
    unsigned long currentTime = millis();
    
    if (lastHitTime != 0) {
      timeBetweenHits = currentTime - lastHitTime;
      hitCount++;
      
      // Отправляем данные об ударе
      Serial.print("HIT:");
      Serial.print(timeBetweenHits);
      Serial.print(",COUNT:");
      Serial.print(hitCount);
      Serial.println();
    }
    
    lastHitTime = currentTime;
    
    // Антидребезг
    delay(DEBOUNCE_DELAY_MS);
    while(digitalRead(MOTION_PIN) == LOW) {
      delay(HOLD_DELAY_MS);
    }
  }
  
  // ЧТЕНИЕ ТЕМПЕРАТУРЫ И ВЛАЖНОСТИ
  if (millis() - lastTempTime >= TEMP_READ_INTERVAL_MS) {
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    
    if (!isnan(humidity) && !isnan(temperature)) {
      lastTemperature = temperature;
      lastHumidity = humidity;
      
      // Отправляем данные в формате для Python
      Serial.print("TEMP:");
      Serial.print(temperature, 1);
      Serial.print(",HUM:");
      Serial.print(humidity, 1);
      Serial.print(",HIT_COUNT:");
      Serial.print(hitCount);
      Serial.println();
    } else {
      Serial.println("ERROR:DHT11 read failed");
    }
    
    lastTempTime = millis();
    
    // СБРОС СЧЕТЧИКА УДАРОВ
    if (millis() > HIT_RESET_INTERVAL_MS) {
      hitCount = 0;
    }
  }
  
  delay(MAIN_LOOP_DELAY_MS);
}