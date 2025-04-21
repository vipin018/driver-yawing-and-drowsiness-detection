#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Vipin's S24";            // Replace with your WiFi SSID
const char* password = "12345678";    // Replace with your WiFi password

const char* serverURL = "http://192.168.236.158:5000/get_buzzer_status"; // Flask endpoint

const int buzzerPin = 13;

void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    
    int httpResponseCode = http.GET();
    if (httpResponseCode == 200) {
      String payload = http.getString();
      Serial.println("Status: " + payload);

      if (payload == "drowsy" || payload == "yawn" || payload == "both") {
        digitalWrite(buzzerPin, HIGH);  // Trigger buzzer
      } else {
        digitalWrite(buzzerPin, LOW);   // Turn off buzzer
      }
    } else {
      Serial.println("Error: " + String(httpResponseCode));
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected!");
  }

  delay(2000);  // Check every 2 seconds
}
