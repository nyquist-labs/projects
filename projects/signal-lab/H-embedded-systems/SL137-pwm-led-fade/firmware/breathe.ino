// Wokwi: Arduino Uno, LED on pin 9 (hardware PWM) — breathing with gamma correction
const uint8_t LED = 9;
uint8_t gamma8[256];
void setup() { for (int i = 0; i < 256; i++) gamma8[i] = round(pow(i / 255.0, 2.2) * 255.0); pinMode(LED, OUTPUT); }
void loop() {
  for (int i = 0; i < 256; i++) { analogWrite(LED, gamma8[i]); delay(4); }
  for (int i = 255; i >= 0; i--) { analogWrite(LED, gamma8[i]); delay(4); }
}
