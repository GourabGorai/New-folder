/*
 * ESP32 / Arduino Gesture-Controlled Physical IoT Car Firmware
 * 
 * Hardware Requirements:
 * - ESP32 or Arduino UNO/Nano Development Board
 * - L298N or TB6612FNG Dual H-Bridge Motor Driver
 * - 2WD or 4WD Robot Chassis with DC Motors
 * 
 * Features:
 * - Receives real-time JSON packets from Python Gesture Controller:
 *   {"cmd":"DRIVE", "pwml": 180, "pwmr": 210, "steer": 12.5, "speed": 15.2, "state": "CONTROL"}
 * - Differential Drive PWML / PWMR motor speed regulation (0-255)
 * - Automatic Fail-Safe Safety Watchdog (Stops car if signal is lost for >500ms)
 */

#include <Arduino.h>

// Motor Driver Pin Definitions (L298N / TB6612FNG)
#define ENA_PIN 13  // Left Motor Speed PWM (ESP32 GPIO 13)
#define IN1_PIN 12  // Left Motor Direction 1
#define IN2_PIN 14  // Left Motor Direction 2

#define ENB_PIN 25  // Right Motor Speed PWM (ESP32 GPIO 25)
#define IN3_PIN 26  // Right Motor Direction 1
#define IN4_PIN 27  // Right Motor Direction 2

#define WATCHDOG_TIMEOUT_MS 500
unsigned long last_packet_time = 0;

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

void setup() {
  Serial.begin(115200);
  
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  stopCar();
  Serial.println("ESP32 IoT Gesture Controlled Car Ready!");
}

void loop() {
  // Read Serial JSON packets from Python Gesture Simulator
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      parseCommand(line);
    }
  }

  // Safety Watchdog: Stop motors if command stream stops for > 500ms
  if (millis() - last_packet_time > WATCHDOG_TIMEOUT_MS) {
    stopCar();
  }
}
