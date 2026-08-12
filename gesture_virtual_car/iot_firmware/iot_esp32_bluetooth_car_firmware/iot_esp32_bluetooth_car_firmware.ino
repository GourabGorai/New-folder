/*
 * ESP32 / Arduino Bluetooth-Controlled Physical IoT Car Firmware
 * 
 * Hardware Requirements:
 * - ESP32 Development Board (NodeMCU ESP32-WROOM-32 or similar)
 * - L298N or TB6612FNG Dual H-Bridge Motor Driver
 * - 2WD or 4WD Robot Chassis with DC Motors
 * 
 * Bluetooth Features:
 * 1. Bluetooth Serial (Classic BT Name: "ESP32_Car_BT")
 * 2. Parses real-time JSON packets from Python Gesture Controller:
 *    {"cmd":"DRIVE", "pwml": 180, "pwmr": 210, "steer": 12.5, "speed": 15.2, "state": "CONTROL"}
 * 3. Supports single-character Bluetooth RC Car Smartphone App commands:
 *    - 'F' / 'f' -> Drive Forward
 *    - 'B' / 'b' -> Drive Reverse
 *    - 'L' / 'l' -> Turn Left
 *    - 'R' / 'r' -> Turn Right
 *    - 'S' / 's' -> Stop Motors
 * 4. USB Hardware Serial Port (115200 Baud fallback)
 * 5. Automatic Fail-Safe Safety Watchdog (Stops motors if signal is lost for >500ms)
 */

#include <Arduino.h>
#include <BluetoothSerial.h>

// Motor Driver Pin Definitions (L298N / TB6612FNG)
#define ENA_PIN 13  // Left Motor Speed PWM (ESP32 GPIO 13)
#define IN1_PIN 12  // Left Motor Direction 1
#define IN2_PIN 14  // Left Motor Direction 2

#define ENB_PIN 25  // Right Motor Speed PWM (ESP32 GPIO 25)
#define IN3_PIN 26  // Right Motor Direction 1
#define IN4_PIN 27  // Right Motor Direction 2

#define WATCHDOG_TIMEOUT_MS 500
unsigned long last_packet_time = 0;

// Bluetooth Instance
BluetoothSerial SerialBT;

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

void parseCommand(String cmdStr) {
  cmdStr.trim();
  if (cmdStr.length() == 0) return;

  // 1. JSON Telemetry Packet (from Python Gesture Controller)
  int idx_l = cmdStr.indexOf("\"pwml\":");
  int idx_r = cmdStr.indexOf("\"pwmr\":");

  if (idx_l != -1 && idx_r != -1) {
    int pwml = cmdStr.substring(idx_l + 7, cmdStr.indexOf(",", idx_l)).toInt();
    int pwmr = cmdStr.substring(idx_r + 7, cmdStr.indexOf(",", idx_r)).toInt();

    if (cmdStr.indexOf("STOP") != -1) {
      stopCar();
    } else {
      setMotorLeft(pwml);
      setMotorRight(pwmr);
    }
    last_packet_time = millis();
    return;
  }

  // 2. Single-character Bluetooth RC App Commands ('F', 'B', 'L', 'R', 'S')
  char c = toupper(cmdStr.charAt(0));
  int default_speed = 200;

  if (c == 'F') {
    setMotorLeft(default_speed);
    setMotorRight(default_speed);
    last_packet_time = millis();
  } else if (c == 'B') {
    setMotorLeft(-default_speed);
    setMotorRight(-default_speed);
    last_packet_time = millis();
  } else if (c == 'L') {
    setMotorLeft(-default_speed / 2);
    setMotorRight(default_speed);
    last_packet_time = millis();
  } else if (c == 'R') {
    setMotorLeft(default_speed);
    setMotorRight(-default_speed / 2);
    last_packet_time = millis();
  } else if (c == 'S') {
    stopCar();
    last_packet_time = millis();
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

  // Initialize Bluetooth Serial
  SerialBT.begin("ESP32_Car_BT");

  Serial.println("\n========================================================");
  Serial.println(" ESP32 BLUETOOTH IOT CAR FIRMWARE READY");
  Serial.println("========================================================");
  Serial.println(" [Bluetooth] Device Name: ESP32_Car_BT");
  Serial.println(" [Commands] Accepts Python JSON & Standard RC App ('F','B','L','R','S')");
  Serial.println("========================================================\n");
}

void loop() {
  // 1. Read Bluetooth Serial Stream
  if (SerialBT.available() > 0) {
    String line = SerialBT.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      parseCommand(line);
    }
  }

  // 2. Read USB Serial Stream (Wired Fallback / Debug)
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      parseCommand(line);
    }
  }

  // 3. Safety Watchdog: Stop motors if command stream stops for > 500ms
  if (millis() - last_packet_time > WATCHDOG_TIMEOUT_MS) {
    stopCar();
  }
}
