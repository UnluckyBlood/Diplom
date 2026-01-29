#include "DHT.h"

#define DHT_PIN 2
#define MOTION_PIN 5
#define TEMP_READ_INTERVAL 2000  // Чтение температуры каждые 2 сек

DHT dht(DHT_PIN, DHT11);

unsigned long lastHitTime = 0;
unsigned long timeBetweenHits = 0;
unsigned long lastTempTime = 0;
int hitCount = 0;
float lastTemperature = 0;
float lastHumidity = 0;

void setup() {
  pinMode(MOTION_PIN, INPUT_PULLUP);
  dht.begin();
  Serial.begin(9600);
  Serial.println("System started");
}

void loop() {
  // Проверка на удары/вибрацию
  if (digitalRead(MOTION_PIN) == LOW) {
    unsigned long currentTime = millis();
    
    if (lastHitTime != 0) {
      timeBetweenHits = currentTime - lastHitTime;
      hitCount++;
      
      // Отправляем данные об ударе в правильном формате
      Serial.print("HIT:");
      Serial.print(timeBetweenHits);
      Serial.print(",COUNT:");
      Serial.print(hitCount);
      Serial.println();
    }
    
    lastHitTime = currentTime;
    
    // Антидребезг
    delay(50);
    while(digitalRead(MOTION_PIN) == LOW) {
      delay(10);
    }
  }
  
  // Чтение температуры и влажности
  if (millis() - lastTempTime >= TEMP_READ_INTERVAL) {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    
    if (!isnan(h) && !isnan(t)) {
      lastTemperature = t;
      lastHumidity = h;
      
      // Отправляем данные в формате для Python
      Serial.print("TEMP:");
      Serial.print(t, 1);
      Serial.print(",HUM:");
      Serial.print(h, 1);
      Serial.print(",HIT_COUNT:");
      Serial.print(hitCount);
      Serial.println();
    } else {
      Serial.println("ERROR:DHT11 read failed");
    }
    
    lastTempTime = millis();
    
    // Сброс счетчика ударов каждые 10 минут
    if (millis() > 600000) { // 10 минут
      hitCount = 0;
    }
  }
  
  delay(10); // Небольшая пауза для стабильности
}