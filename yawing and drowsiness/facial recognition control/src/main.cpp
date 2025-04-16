#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Airtel_Buddys";  // Replace with your WiFi SSID
const char* password = "buddys@123";  // Replace with your WiFi Password
const char* serverUrl = "http://192.168.1.49:5000/get_buzzer_status";  // Flask server URL

#define BUZZER_PIN 14  // Buzzer connected to pin 19

void setup() {
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        
        int httpResponseCode = http.GET();  // Request buzzer status

        if (httpResponseCode > 0) {
            String response = http.getString();
            Serial.println("Server Response: " + response);
            
            if (response == "1") {  // Check if face detected (buzzer should be triggered)
                Serial.println("Activating Buzzer...");
                digitalWrite(BUZZER_PIN, HIGH);  // Buzzer ON
                delay(2000);  // Keep buzzer ON for 2 seconds
                digitalWrite(BUZZER_PIN, LOW);   // Buzzer OFF
            } else {
                Serial.println("No face detected, buzzer not activated.");
            }
        } else {
            Serial.println("Failed to connect to server");
        }

        http.end();
    } else {
        Serial.println("WiFi Disconnected! Reconnecting...");
        WiFi.begin(ssid, password);
    }

    delay(500);  
}
