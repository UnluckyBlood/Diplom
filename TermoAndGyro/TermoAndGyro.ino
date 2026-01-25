#include "DHT.h"

#define DHT_PIN 2
#define MOTION_PIN 5
#define TEMP_READ_INTERVAL 1000  // таймер темпы

DHT dht(DHT_PIN, DHT11);

unsigned long lastHitTime = 0;
unsigned long timeBetweenHits = 0;
unsigned long lastTempTime = 0; 

void setup() {
  pinMode(MOTION_PIN, INPUT_PULLUP);
  dht.begin();
  Serial.begin(9600);
}

void loop() {
  //проверка на удары
  if (digitalRead(MOTION_PIN) == LOW) {
    unsigned long currentTime = millis();
    
    if (lastHitTime != 0) {
      timeBetweenHits = currentTime - lastHitTime;
      Serial.print("Время между ударами: ");
      Serial.print(timeBetweenHits);
      Serial.println(" мс");
    }
    
    lastHitTime = currentTime;
    
    // Анти дребезг
    delay(50);
    while(digitalRead(MOTION_PIN) == LOW) {
      delay(10);
    }
  }
  //Темпа
  if (millis() - lastTempTime >= TEMP_READ_INTERVAL) {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    
    if (!isnan(h) && !isnan(t)) {
      Serial.print("Влажность: ");
      Serial.print(h);
      Serial.print("%, Температура: ");
      Serial.print(t);
      Serial.println("°C");
    } else {
      Serial.println("Ошибка чтения DHT11!");
    }
    
    lastTempTime = millis();  // сброс таймера
  }
}