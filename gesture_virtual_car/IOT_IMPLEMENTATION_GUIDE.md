# Implementation Guide: ML-Based Computer Vision IoT Car

This document provides a comprehensive, step-by-step implementation plan for building and deploying the **ML-Based Computer Vision IoT Car**. It translates the architectural vision and technical details from the `Project Plan ML-Based Computer Vision IoT Car.pdf` into actionable hardware, software, machine learning, and IoT integration steps.

---

## 1. Executive Summary & Architecture Overview

The system pairs **Edge AI Computer Vision** on a host PC/laptop with an **IoT Edge Robotic Car**. Instead of physical joysticks or wearable sensors, a user controls the vehicle via real-time hand gestures captured by a webcam.

```
       +-------------------------------------------------------+
       |               Vision Controller (Host PC)            |
       |  +----------------+   +---------------+   +--------+  |
       |  | Webcam Capture |-->| MediaPipe ML  |-->| Python |  |
       |  |  (OpenCV)      |   | Landmark AI   |   | IoT    |  |
       |  +----------------+   +---------------+   | Engine |  |
       +-------------------------------------------+---+----+--+
                                                       |
                                    Wi-Fi UDP/TCP or USB Serial (JSON)
                                                       |
       +-----------------------------------------------+-------+
       |               IoT Receiver (Physical Car)             |
       |  +-----------------+  GPIO PWM   +-----------------+  |
       |  | ESP32 Micro-    |------------>| L298N Motor     |  |
       |  | controller      |             | Driver Module   |  |
       |  +-----------------+             +--------+--------+  |
       |                                           | Power     |
       |                                  +--------v--------+  |
       |                                  | 4x DC Gear Motors| |
       |                                  +-----------------+  |
       +-------------------------------------------------------+
```

### Core Subsystems:
1. **Vision Controller (Laptop/PC)**: Captures webcam video feed, extracts hand landmark coordinates using MediaPipe, classifies gestures using a trained Machine Learning model, and calculates differential drive motor telemetry.
2. **IoT Communication Link**: Transmits control packets (`JSON` payload) over Wi-Fi (UDP/TCP/MQTT) or USB Serial to the ESP32.
3. **IoT Receiver (Robotic Car)**: ESP32 receives command packets, parses motor PWM signals, drives the L298N H-Bridge driver, and executes safety watchdog monitoring.

---

## 2. Requirements & Bill of Materials (BOM)

### 2.1 Hardware Components
| Subsystem | Component | Quantity | Notes / Specifications |
| :--- | :--- | :---: | :--- |
| **Controller** | Laptop/PC with Webcam | 1 | Runs Python 3.x, OpenCV, MediaPipe, ML model |
| **Microcontroller** | ESP32 Development Board | 1 | NodeMCU ESP32-WROOM-32 (Wi-Fi & Bluetooth enabled) |
| **Motor Driver** | L298N Dual H-Bridge Driver | 1 | Controls motor direction & PWM speed (5V-35V) |
| **Motors** | DC Gear Motors | 4 | Yellow TT Motors (3V-6V), pre-wired |
| **Wheels** | Robot Wheels | 4 | Compatible with TT motor D-shafts |
| **Chassis** | 4WD Acrylic Robot Chassis | 1 | Double-deck chassis with standoff mounts |
| **Power Supply** | 18650 Li-ion Batteries | 2 | 3.7V each (~7.4V total) with dual slot battery holder |
| **Interconnects** | Jumper Wires | 1 Set | Female-to-Female & Male-to-Female jumper wires |

### 2.2 Software & AI Stack
* **Python Environment**: Python 3.8+, OpenCV (`opencv-python`), MediaPipe (`mediapipe`), NumPy, Scikit-Learn / TensorFlow, PySerial (`pyserial`).
* **Microcontroller IDE**: Arduino IDE or VS Code with PlatformIO (ESP32 Board Package installed).
* **Codebase Components**:
  * [data_collection.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/data_collection.py): Dataset acquisition script.
  * [preprocessing.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/preprocessing.py): Feature extraction and normalization.
  * [train_model.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/train_model.py): Model training pipeline.
  * [gesture_predictor.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/gesture_predictor.py): Real-time inference engine.
  * [iot_controller.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/iot_controller.py): Serial/Network telemetry bridge.
  * [iot_esp32_car_firmware.ino](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/iot_firmware/iot_esp32_car_firmware.ino): ESP32 embedded firmware.

---

## 3. Hardware Assembly & Circuit Wiring

### 3.1 Mechanical Assembly Steps
1. **Mount Motors**: Secure the 4 DC gear motors to the acrylic chassis base using the provided steel brackets, nuts, and bolts.
2. **Attach Wheels**: Press-fit the 4 rubber wheels onto the extended TT motor shafts.
3. **Mount Electronics**: Secure the L298N driver, ESP32 board, and 18650 battery holder to the top chassis deck using standoffs or double-sided adhesive tape.

---

### 3.2 Electrical Wiring Diagram & Pin Mapping

#### Electrical Block Diagram
```
+------------------------------------+
| 7.4V Battery Pack (2x 18650 Cells) |
+------------------+-----------------+
  | (+) Red wire     | (-) Black wire
  v                  v
+--------------------+---------------------------------------+
| L298N Motor Driver Module                                  |
| [12V]             [GND]                     [5V]           |
|   |                 | (Common GND)            |            |
|   |                 +---------------+         |            |
|   |                 v               |         |            |
|   |          +--------------+       |         |            |
|   |          | ESP32 Board  |       |         |            |
|   +----------| VIN   GND    |<------+---------+            |
|              +-------+------+ (Powers ESP32 logic)        |
|                      | GPIO Pins                           |
|                      +=========> [ENA, IN1..IN4, ENB]      |
|                                    (Logic / PWM Control)   |
| [OUT1 & OUT2]                            [OUT3 & OUT4]     |
+------|-----|-----------------------------------|-----|-----+
       |     |                                   |     |
       v     v                                   v     v
 +---------------+                         +---------------+
 |  Left Motors  |                         | Right Motors  |
 |  (Parallel)   |                         |  (Parallel)   |
 +---------------+                         +---------------+
```

#### Detailed Pin Mapping Table
| Source Component & Pin | Target Component & Pin | Description / Purpose |
| :--- | :--- | :--- |
| **Battery Holder (+ Red)** | **L298N 12V Screw Terminal** | Motor Power Supply (+7.4V DC) |
| **Battery Holder (- Black)**| **L298N GND Screw Terminal** | System Power Ground |
| **L298N 5V Screw Terminal** | **ESP32 VIN Pin (or 5V)** | Powering ESP32 (requires 5V jumper ON) |
| **L298N GND Terminal** | **ESP32 GND Pin** | **CRITICAL: Shared Common Ground** |
| **ESP32 GPIO 14** | **L298N ENA** | Left Motors Speed PWM Control |
| **ESP32 GPIO 27** | **L298N IN1** | Left Motors Direction Signal 1 |
| **ESP32 GPIO 26** | **L298N IN2** | Left Motors Direction Signal 2 |
| **ESP32 GPIO 25** | **L298N IN3** | Right Motors Direction Signal 1 |
| **ESP32 GPIO 33** | **L298N IN4** | Right Motors Direction Signal 2 |
| **ESP32 GPIO 32** | **L298N ENB** | Right Motors Speed PWM Control |
| **L298N OUT1 & OUT2** | **Left Motors (Front + Rear)** | Parallel connection for Left wheels |
| **L298N OUT3 & OUT4** | **Right Motors (Front + Rear)**| Parallel connection for Right wheels |

> [!IMPORTANT]
> **Common Ground Requirement**: You MUST connect the GND screw terminal of the L298N driver directly to a GND pin on the ESP32. Without a shared ground reference, logic signals will fluctuate, causing erratic motor behavior or communication failure.

---

## 4. Gesture Mapping & Machine Learning Pipeline

### 4.1 Gesture Classification Matrix
| Hand Gesture | ML Output Class | Vehicle Command | Differential PWM Output |
| :--- | :---: | :---: | :--- |
| **Open Palm facing camera** | `FORWARD` | Drive Forward | `PWML > 0`, `PWMR > 0` |
| **Closed Fist** | `STOP` | Stop Motors | `PWML = 0`, `PWMR = 0` |
| **Thumb pointing Left** | `LEFT` | Turn Left | `PWMR > PWML` |
| **Thumb pointing Right** | `RIGHT` | Turn Right | `PWML > PWMR` |
| **Peace Sign (Two Fingers)** | `BACKWARD` | Reverse Drive | `PWML < 0`, `PWMR < 0` |

---

### 4.2 Machine Learning Workflow

1. **Landmark Extraction**: Rather than passing raw high-resolution webcam frames into heavy Convolutional Neural Networks (CNNs), the vision pipeline utilizes **MediaPipe Hand Landmarker** to extract 21 3D hand joint coordinates \((x, y, z)\).
2. **Coordinate Normalization**:
   - Translate landmarks relative to the wrist point (Landmark 0).
   - Scale landmarks by hand bounding box size to achieve scale and distance invariance.
3. **Model Selection**: Train a lightweight Multi-Layer Perceptron (MLP) or Random Forest Classifier on normalized 63-dimensional feature vectors \((21 \times 3)\).
4. **Real-time Inference**: Achieve >60 FPS inference speed on modern laptops with negligible CPU utilization.

---

## 5. IoT Communication & Software Integration

### 5.1 Communication Protocol & Data Packet Design
The laptop controller serializes vehicle telemetry into lightweight JSON strings sent via USB Serial or Wi-Fi UDP socket packets to the ESP32:

```json
{
  "cmd": "DRIVE",
  "pwml": 180,
  "pwmr": 210,
  "steer": 12.5,
  "speed": 15.2,
  "state": "CONTROL",
  "ts": 84520
}
```

### 5.2 Differential Drive Control Logic
The `IoTController` translates continuous steering angles (\(-35^\circ\) to \(+35^\circ\)) and target vehicle speed into left (`PWML`) and right (`PWMR`) motor power values in the range `[-255, 255]`:

$$\text{throttle} = \frac{\text{speed}}{\text{max\_speed}}$$
$$\text{base\_pwm} = \text{throttle} \times 255$$
$$\text{steer\_diff} = \frac{\text{steering\_angle}}{35.0} \times 120$$
$$\text{PWM}_L = \text{clamp}(\text{base\_pwm} + \text{steer\_diff}, -255, 255)$$
$$\text{PWM}_R = \text{clamp}(\text{base\_pwm} - \text{steer\_diff}, -255, 255)$$

### 5.3 Embedded Safety Watchdog
The ESP32 firmware ([iot_esp32_car_firmware.ino](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/iot_firmware/iot_esp32_car_firmware.ino)) enforces a **500 ms Watchdog Timer**. If no valid control packet is received within 500 ms (due to Wi-Fi dropout, camera obstruction, or host software pause), the car automatically cuts power to all motors to prevent runaway collisions.

---

## 6. Four-Phase Implementation Timeline

### Phase 1: Data Collection & Hardware Assembly (Week 1)
- [x] Assemble 4WD robot chassis, DC gear motors, L298N driver, and ESP32 board.
- [x] Complete electrical wiring following the pin mapping table.
- [x] Run [data_collection.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/data_collection.py) to capture ~500 frame samples per gesture class across different lighting conditions and hands.

### Phase 2: ML Model Training and Validation (Week 2)
- [x] Extract hand landmarks using MediaPipe via [preprocessing.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/preprocessing.py).
- [x] Train classifier model using [train_model.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/train_model.py).
- [x] Validate model accuracy locally via webcam preview to ensure real-time latency under 30ms.

### Phase 3: IoT Communication Setup (Week 3)
- [x] Flash ESP32 firmware ([iot_esp32_car_firmware.ino](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/iot_firmware/iot_esp32_car_firmware.ino)) via Arduino IDE / PlatformIO.
- [x] Configure communication parameters in [iot_controller.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/iot_controller.py) (Baud rate `115200` for Serial or IP/Port for UDP Wi-Fi).
- [x] Verify serial packet transmission using serial monitor / mock loop.

### Phase 4: End-to-End Integration and Field Testing (Week 4)
- [x] Execute [main.py](file:///d:/BragBoard-main/New%20folder/gesture_virtual_car/main.py) with live webcam gesture control and physical car connected.
- [x] Measure overall end-to-end latency (Webcam Capture $\rightarrow$ ML Inference $\rightarrow$ Wi-Fi/Serial Tx $\rightarrow$ ESP32 Motor Response). Target: $<100\text{ ms}$.
- [x] Tune PWM speed curves and confidence thresholds to prevent accidental movement triggers.

---

## 7. Troubleshooting & Safety Checklist

> [!WARNING]
> * **Motor Rotation Mismatch**: If a wheel turns backward when given a `FORWARD` command, invert the motor leads connected to the L298N screw terminals or swap the corresponding GPIO direction pins (`IN1`/`IN2` or `IN3`/`IN4`) in `iot_esp32_car_firmware.ino`.
> * **ESP32 Brownout / Reset Loops**: If the ESP32 resets whenever motors turn on, the motor power draw is collapsing the logic supply. Ensure batteries are fully charged (min 7.4V) and that motor driver power (`12V` terminal) is fed directly from the battery pack, not through the ESP32.
> * **Unresponsive Control**: Verify that host PC and ESP32 share the same Wi-Fi subnet (if using wireless UDP) and that firewall rules allow outbound UDP/TCP socket traffic.

---

## 8. Conclusion & Future Extensions

By delegating computational AI workloads to the host PC and using an ESP32 as a high-speed IoT execution edge node, this project achieves responsive, contactless vehicle control. 

**Potential Upgrades**:
* **On-Board Edge AI**: Replace the host laptop by mounting a Raspberry Pi 4 or NVIDIA Jetson Nano directly on the chassis with a CSI camera for fully autonomous onboard processing.
* **Telemetry Video Stream**: Stream live camera feed from an ESP32-CAM back to the laptop dashboard.
