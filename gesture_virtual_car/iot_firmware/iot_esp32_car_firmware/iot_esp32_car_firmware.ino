/*
 * ESP32 / Arduino Wireless (Wi-Fi Only) & Gesture-Controlled Physical IoT Car Firmware
 * 
 * Hardware Requirements:
 * - ESP32 Development Board (NodeMCU ESP32-WROOM-32 or similar)
 * - L298N or TB6612FNG Dual H-Bridge Motor Driver
 * - 2WD or 4WD Robot Chassis with DC Motors
 * 
 * Wireless Features (Wi-Fi Only):
 * 1. Wi-Fi Access Point (AP Mode: SSID "ESP32_Car_WiFi", Pass "12345678", IP 192.168.4.1)
 * 2. Real-time Wi-Fi UDP Packet Receiver (Port 8888) for Python Gesture Controller
 * 3. Embedded Web Server Remote Control (Port 80) for Smartphone / Laptop Web Browsers
 * 4. USB Hardware Serial Port (115200 Baud fallback)
 * 5. Automatic Fail-Safe Safety Watchdog (Stops motors if signal is lost for >500ms)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebServer.h>

// Motor Driver Pin Definitions (L298N / TB6612FNG)
#define ENA_PIN 13  // Left Motor Speed PWM (ESP32 GPIO 13)
#define IN1_PIN 12  // Left Motor Direction 1
#define IN2_PIN 14  // Left Motor Direction 2

#define ENB_PIN 25  // Right Motor Speed PWM (ESP32 GPIO 25)
#define IN3_PIN 26  // Right Motor Direction 1
#define IN4_PIN 27  // Right Motor Direction 2

#define WATCHDOG_TIMEOUT_MS 500
unsigned long last_packet_time = 0;

// Wi-Fi Configuration
const char* AP_SSID = "ESP32_Car_WiFi";
const char* AP_PASS = "12345678";
const int UDP_PORT = 8888;

// Network & Control Instances
WiFiUDP udpServer;
WebServer webServer(80);

char packetBuffer[255];

void setMotorLeft(int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, pwm);
  } else if (pwm < 0) {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, HIGH);
    analogWrite(ENA_PIN, -pwm);
  } else {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, 0);
  }
}

void setMotorRight(int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(IN3_PIN, HIGH);
    digitalWrite(IN4_PIN, LOW);
    analogWrite(ENB_PIN, pwm);
  } else if (pwm < 0) {
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, HIGH);
    analogWrite(ENB_PIN, -pwm);
  } else {
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, LOW);
    analogWrite(ENB_PIN, 0);
  }
}

void stopCar() {
  setMotorLeft(0);
  setMotorRight(0);
}

void parseCommand(String jsonStr) {
  // Simple fast parser for {"pwml":180,"pwmr":210,"state":"CONTROL"}
  int pwml = 0;
  int pwmr = 0;

  int idx_l = jsonStr.indexOf("\"pwml\":");
  int idx_r = jsonStr.indexOf("\"pwmr\":");

  if (idx_l != -1 && idx_r != -1) {
    pwml = jsonStr.substring(idx_l + 7, jsonStr.indexOf(",", idx_l)).toInt();
    pwmr = jsonStr.substring(idx_r + 7, jsonStr.indexOf(",", idx_r)).toInt();

    if (jsonStr.indexOf("STOP") != -1) {
      stopCar();
    } else {
      setMotorLeft(pwml);
      setMotorRight(pwmr);
    }
    last_packet_time = millis();
  }
}

// Embedded HTML/JS Web Remote Dashboard
const char HTML_INDEX[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>ESP32 Wireless IoT Car Control (Wi-Fi)</title>
  <style>
    body { font-family: Arial, sans-serif; text-align: center; background: #12161e; color: #fff; margin: 0; padding: 20px; }
    h1 { color: #00ffc8; font-size: 24px; margin-bottom: 5px; }
    p { color: #888; font-size: 14px; }
    .card { background: #1a202c; border-radius: 12px; padding: 20px; max-width: 400px; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .btn-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 20px 0; }
    .btn { background: #2d3748; color: #00e5ff; border: 2px solid #00e5ff; padding: 18px; font-size: 18px; font-weight: bold; border-radius: 10px; cursor: pointer; user-select: none; transition: 0.1s; }
    .btn:active { background: #00e5ff; color: #12161e; transform: scale(0.95); }
    .btn-stop { background: #e53e3e; color: #fff; border-color: #ff5252; grid-column: span 3; }
    .btn-stop:active { background: #c53030; }
    .slider-container { margin: 20px 0; }
    input[type=range] { width: 100%; accent-color: #00ffc8; }
    .status { font-weight: bold; color: #00ffc8; font-size: 16px; margin-top: 15px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>🚗 ESP32 Wi-Fi Car</h1>
    <p>Wi-Fi Web Remote Control Interface</p>
    
    <div class="slider-container">
      <label>Max Speed PWM: <span id="speedVal">200</span></label><br><br>
      <input type="range" id="speed" min="50" max="255" value="200" oninput="document.getElementById('speedVal').innerText=this.value">
    </div>

    <div class="btn-grid">
      <div></div>
      <button class="btn" onclick="sendCmd('FORWARD')">▲<br>FWD</button>
      <div></div>
      <button class="btn" onclick="sendCmd('LEFT')">◄<br>LEFT</button>
      <button class="btn" onclick="sendCmd('REVERSE')">▼<br>REV</button>
      <button class="btn" onclick="sendCmd('RIGHT')">►<br>RIGHT</button>
      <button class="btn btn-stop" onclick="sendCmd('STOP')">⏹ STOP</button>
    </div>

    <div class="status" id="status">Status: Connected via Wi-Fi</div>
  </div>

  <script>
    function sendCmd(action) {
      const spd = document.getElementById('speed').value;
      fetch(`/cmd?dir=${action}&speed=${spd}`)
        .then(r => r.text())
        .then(txt => { document.getElementById('status').innerText = 'State: ' + action; })
        .catch(err => { document.getElementById('status').innerText = 'Error'; });
    }
  </script>
</body>
</html>
)rawliteral";

void handleWebRoot() {
  webServer.send(200, "text/html", HTML_INDEX);
}

void handleWebCmd() {
  if (webServer.hasArg("dir")) {
    String dir = webServer.arg("dir");
    int spd = webServer.hasArg("speed") ? webServer.arg("speed").toInt() : 200;

    if (dir == "FORWARD") {
      setMotorLeft(spd);
      setMotorRight(spd);
    } else if (dir == "REVERSE") {
      setMotorLeft(-spd);
      setMotorRight(-spd);
    } else if (dir == "LEFT") {
      setMotorLeft(-spd / 2);
      setMotorRight(spd);
    } else if (dir == "RIGHT") {
      setMotorLeft(spd);
      setMotorRight(-spd / 2);
    } else {
      stopCar();
    }
    last_packet_time = millis();
    webServer.send(200, "text/plain", "OK");
  } else {
    webServer.send(400, "text/plain", "Missing dir argument");
  }
}

void setup() {
  Serial.begin(115200);
  
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  stopCar();

  // 1. Initialize Wi-Fi Access Point (AP Mode)
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  IPAddress apIP = WiFi.softAPIP();

  Serial.println("\n========================================================");
  Serial.println(" ESP32 WI-FI IOT CAR FIRMWARE READY (WI-FI ONLY)");
  Serial.println("========================================================");
  Serial.print(" [Wi-Fi AP] SSID: "); Serial.println(AP_SSID);
  Serial.print(" [Wi-Fi AP] Pass: "); Serial.println(AP_PASS);
  Serial.print(" [Wi-Fi AP] IP Address: "); Serial.println(apIP);

  // 2. Start UDP Server for fast low-latency telemetry from Python
  udpServer.begin(UDP_PORT);
  Serial.print(" [UDP Server] Listening on Port: "); Serial.println(UDP_PORT);

  // 3. Start Web Server for Smartphone / Web Remote Control
  webServer.on("/", handleWebRoot);
  webServer.on("/cmd", handleWebCmd);
  webServer.begin();
  Serial.println(" [Web Server] Remote Control hosted at http://192.168.4.1");
  Serial.println("========================================================\n");
}

void loop() {
  // 1. Check Wi-Fi UDP Packets (Python Wireless Controller)
  int packetSize = udpServer.parsePacket();
  if (packetSize > 0) {
    int len = udpServer.read(packetBuffer, 254);
    if (len > 0) {
      packetBuffer[len] = 0;
      parseCommand(String(packetBuffer));
    }
  }

  // 2. Check HTTP Web Server Requests (Browser Touch Controller)
  webServer.handleClient();

  // 3. Check USB Serial Commands (Wired Fallback / Debug)
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      parseCommand(line);
    }
  }

  // 4. Safety Watchdog: Stop motors if command stream stops for > 500ms
  if (millis() - last_packet_time > WATCHDOG_TIMEOUT_MS) {
    stopCar();
  }
}


