const int sensorPin = 5;
unsigned long lastHitTime = 0;
unsigned long timeBetweenHits = 0;

void setup() {
  pinMode(sensorPin, INPUT_PULLUP);
  Serial.begin(9600);
  Serial.println("Ожидание первого удара...");
}

void loop() {
  if (digitalRead(sensorPin) == LOW) {
    unsigned long currentTime = millis();
    
    // Если это не самый первый удар (lastHitTime не равен 0)
    if (lastHitTime != 0) {
      timeBetweenHits = currentTime - lastHitTime;
      Serial.print("Время между ударами: ");
      Serial.print(timeBetweenHits);
      Serial.println(" мс");
    }
    
    lastHitTime = currentTime;
    
    // Защита от дребезга контактов
    delay(100);
    // Ждем, пока контакт разомкнется
    while(digitalRead(sensorPin) == LOW) {
      delay(10);
    }
  }
}