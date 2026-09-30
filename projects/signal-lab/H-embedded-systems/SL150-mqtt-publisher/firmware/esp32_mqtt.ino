// Wokwi ESP32 + PubSubClient: publishes a reading every 2 s to a public test broker (runs in the browser simulator)
#include <WiFi.h>
#include <PubSubClient.h>
WiFiClient net; PubSubClient mqtt(net);
void setup() { Serial.begin(115200); WiFi.begin("Wokwi-GUEST", "", 6); while (WiFi.status() != WL_CONNECTED) delay(100);
  mqtt.setServer("test.mosquitto.org", 1883); }
void loop() { if (!mqtt.connected()) mqtt.connect("eelab-wokwi-demo"); mqtt.loop();
  static uint32_t t = 0; if (millis() - t > 2000) { t = millis(); char b[16]; dtostrf(20 + random(100) / 100.0, 0, 2, b); mqtt.publish("eelab/demo/temp", b); } }
