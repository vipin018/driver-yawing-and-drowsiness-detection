#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

void updateLCD();

// WiFi credentials
const char* ssid = "Gautam";
const char* password = "crawizzz";

// Define relay and ACS712 pin
const int relayPin = 18;       // First relay
const int relayPin2 = 5;       // Second relay
const int acsPin = 34;         // Pin connected to ACS712 analog output

// Define IR sensor pin
const int irSensorRight = 14;  // Right IR sensor

// Create a web server object
WebServer server(80);

// Constants for ACS712
const float sensitivity = 0.1; // 100mV/A for ACS712 20A version
const float vRef = 3.3;        // ESP32 ADC reference voltage
const int adcResolution = 4096; // 12-bit ADC resolution
const float zeroCurrentOffset = vRef / 2; // Midpoint for ACS712

// Power and energy tracking
float accumulatedEnergy = 0.0; // Energy in watt-minutes
unsigned long previousMillis = 0;
const unsigned long interval = 30000; // 30 seconds in milliseconds

// LCD Setup (I2C Address: 0x27, 16 columns, 2 rows)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// HTML content for the webpage
const char* webpage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>Relay Control, Power Monitoring & Object Detection</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; }
        button { padding: 15px 30px; margin: 10px; font-size: 20px; background-color : #a4764c; border-radius:2vh }
    </style>
</head>
<body>
    <h1>Relay Control, Power Monitoring & Object Detection</h1>
    <div>
        <h2>Relay 1</h2>
        <button onclick="sendRequest('relay1', 'ON')">Turn ON</button>
        <button onclick="sendRequest('relay1', 'OFF')">Turn OFF</button>
    </div>
    <div>
        <h2>Relay 2</h2>
        <button onclick="sendRequest('relay2', 'ON')">Turn ON</button>
        <button onclick="sendRequest('relay2', 'OFF')">Turn OFF</button>
    </div>
    <p id="power">Loading power data...</p>
    <p id="object">Object detection status...</p>

    <script>
        const sendRequest = (relay, action) =>
            fetch(/relay?relay=${relay}&state=${action})
                .then(res => res.text())
                .then(alert)
                .catch(console.error);

        const updatePower = () => {
            fetch('/power')
                .then(res => res.text())
                .then(data => document.getElementById('power').innerHTML = data)
                .catch(console.error);
        };

        const updateObject = () => {
            fetch('/object')
                .then(res => res.text())
                .then(data => document.getElementById('object').innerHTML = data)
                .catch(console.error);
        };

        setInterval(updatePower, 1000); // Refresh power data every second
        setInterval(updateObject, 1000); // Refresh object detection data every second
    </script>
</body>
</html>
)rawliteral";

// Function to handle the root URL
void handleRoot() {
    server.send(200, "text/html", webpage);
}

// Function to control the relays
void handleRelay() {
    String relay = server.arg("relay");
    String state = server.arg("state");

    if (relay == "relay1") {
        if (state == "ON") {
            digitalWrite(relayPin, LOW);  // Activate relay 1 (active LOW)
            Serial.println("Relay 1 turned ON via webpage");
        } else if (state == "OFF") {
            digitalWrite(relayPin, HIGH); // Deactivate relay 1
            Serial.println("Relay 1 turned OFF via webpage");
        } else {
            server.send(400, "text/plain", "Invalid request for relay 1");
        }
    } else if (relay == "relay2") {
        if (state == "ON") {
            digitalWrite(relayPin2, LOW);  // Activate relay 2 (active LOW)
            Serial.println("Relay 2 turned ON via webpage");
        } else if (state == "OFF") {
            digitalWrite(relayPin2, HIGH); // Deactivate relay 2
            Serial.println("Relay 2 turned OFF via webpage");
        } else {
            server.send(400, "text/plain", "Invalid request for relay 2");
        }
    } else {
        server.send(400, "text/plain", "Invalid relay");
    }
    updateLCD();
}

// Function to calculate power and energy consumption
void handlePower() {
    int adcValue = analogRead(acsPin); // Read raw ADC value
    float voltage = adcValue * (vRef / adcResolution); // Convert to voltage
    float current = (voltage - zeroCurrentOffset) / sensitivity; // Calculate current
    current = abs(current); // Get absolute value of current
    float power = current * 230.0; // Power in watts (P = IV, assuming 230V AC)

    // Accumulate energy consumption over time
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval) {
        accumulatedEnergy += (power * 0.5); // Convert 30-second power (W) to watt-minutes
        previousMillis = currentMillis;
    }

    String response = "Power: " + String(power, 2) + " W<br>Energy: " + String(accumulatedEnergy, 2) + " Wh";
    server.send(200, "text/html", response);
    Serial.print("Power: ");
    Serial.print(power);
    Serial.print(" W, Energy: ");
    Serial.print(accumulatedEnergy);
    Serial.println(" Wh");

    updateLCD();
}

// Function to handle object detection
void handleObjectDetection() {
    String status = digitalRead(irSensorRight) == LOW ? "BITCHES IN THE HOUSE LESSGO!!!" : "NO BITCHES HERE!!!";
    server.send(200, "text/html", status);
    Serial.print("Object Detection Status: ");
    Serial.println(status);
}

// Function to update LCD display
void updateLCD() {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("R1: ");
    lcd.print(digitalRead(relayPin) == LOW ? "ON " : "OFF");
    lcd.print(" R2: ");
    lcd.print(digitalRead(relayPin2) == LOW ? "ON" : "OFF");
    lcd.setCursor(0, 1);
    lcd.print("Power: ");
    lcd.print(accumulatedEnergy, 1);
    lcd.print(" Wh");
}

void setup() {
    // Initialize serial communication
    Serial.begin(115200);
    Serial.println("Initializing ESP32...");

    // Set up relay pins
    pinMode(relayPin, OUTPUT);
    digitalWrite(relayPin, HIGH); // Start with relay 1 OFF
    pinMode(relayPin2, OUTPUT);
    digitalWrite(relayPin2, HIGH); // Start with relay 2 OFF

    // Set up IR sensor pin
    pinMode(irSensorRight, INPUT);

    // Initialize I2C LCD
    Wire.begin(22, 23); // SDA: GPIO 22, SCL: GPIO 23
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("Initializing...");

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi!");

    // Print assigned IP address
    Serial.print("Web server accessible at: http://");
    Serial.println(WiFi.localIP());

    // Set up web server routes
    server.on("/", handleRoot);
    server.on("/relay", handleRelay);
    server.on("/power", handlePower);
    server.on("/object", handleObjectDetection);

    // Start the web server
    server.begin();
    Serial.println("Web server started");

    // Update LCD after initialization
    updateLCD();
}

void loop() {
    // Handle incoming client requests
    server.handleClient();
}