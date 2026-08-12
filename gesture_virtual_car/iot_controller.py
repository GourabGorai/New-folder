import json
import time

class IoTController:
    """
    IoT Hardware Controller Interface.
    Translates vehicle steering angle and throttle into Differential Motor PWM signals (PWML, PWMR)
    and serial/network JSON command packets compatible with ESP32 / Arduino physical cars.
    """
    def __init__(self, serial_port=None, baud_rate=115200):
        self.serial_port_name = serial_port
        self.baud_rate = baud_rate
        self.is_connected = False
        self.serial_inst = None
        
        # Packet history buffer for on-screen HUD telemetry log
        self.recent_packets = []
        self.max_log_history = 5
        
        self.connect()

    def connect(self):
        """Attempts to open Serial connection if port is specified."""
        if self.serial_port_name:
            try:
                import serial
                self.serial_inst = serial.Serial(self.serial_port_name, self.baud_rate, timeout=0.1)
                self.is_connected = True
                print(f"[IoTController] Connected to physical IoT serial port {self.serial_port_name}")
            except Exception as e:
                print(f"[IoTController] Serial port {self.serial_port_name} unavailable: {e}. Running in MOCK Mode.")
                self.is_connected = False
        else:
            self.is_connected = False

    def calculate_motor_pwm(self, speed_kmh, steering_angle_deg, max_speed_kmh=25.0):
        """
        Converts vehicle forward/reverse speed and steering angle into
        2-Wheel / 4-Wheel Differential Motor PWM values: PWML and PWMR in range [-255, 255].
        
        - Positive PWM -> Forward rotation
        - Negative PWM -> Reverse rotation
        - PWML > PWMR -> Vehicle turns right
        - PWMR > PWML -> Vehicle turns left
        """
        # Normalize throttle ratio [-1.0, 1.0]
        throttle = speed_kmh / max_speed_kmh
        base_pwm = throttle * 255.0

        # Steering offset: normalized steering angle [-35°, +35°] mapped to PWM diff
        steer_norm = max(-1.0, min(1.0, steering_angle_deg / 35.0))
        steer_pwm_diff = steer_norm * 120.0  # Differential bias

        pwm_l = base_pwm + steer_pwm_diff
        pwm_r = base_pwm - steer_pwm_diff

        # Clamp within hardware 8-bit motor driver range [-255, 255]
        pwm_l = int(max(-255, min(255, pwm_l)))
        pwm_r = int(max(-255, min(255, pwm_r)))

        return pwm_l, pwm_r

    def send_telemetry(self, speed_kmh, steering_angle_deg, state):
        """
        Formats IoT telemetry packet and transmits to physical car (or logs to mock buffer).
        """
        pwm_l, pwm_r = self.calculate_motor_pwm(speed_kmh, steering_angle_deg)

        packet = {
            'cmd': 'STOP' if state == 'STOP' else 'DRIVE',
            'pwml': 0 if state == 'STOP' else pwm_l,
            'pwmr': 0 if state == 'STOP' else pwm_r,
            'steer': round(steering_angle_deg, 1),
            'speed': round(speed_kmh, 1),
            'state': state,
            'ts': int(time.time() * 1000) % 100000
        }

        json_str = json.dumps(packet)

        # Log packet to mock history
        self.recent_packets.append(json_str)
        if len(self.recent_packets) > self.max_log_history:
            self.recent_packets.pop(0)

        # Transmit via real Serial port if available
        if self.is_connected and self.serial_inst:
            try:
                self.serial_inst.write((json_str + "\n").encode('utf-8'))
            except Exception as e:
                print(f"[IoTController] Serial write error: {e}")
                self.is_connected = False

        return packet
