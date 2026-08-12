import os
import unittest
import numpy as np
import math

# Set Pygame headless driver before importing Pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"

from preprocessing import normalize_landmarks, compute_geometric_angle, is_closed_fist, compute_speed_factor
from physics import RealisticAckermannPhysics, shortest_angular_difference, lerp_angle
from car import Car
from iot_controller import IoTController
from train_model import generate_synthetic_dataset, train_gesture_model, MODEL_PATH, DATASET_PATH
from gesture_predictor import GesturePredictor

class TestGestureCarSimulator(unittest.TestCase):

    def test_preprocessing_normalization(self):
        raw_pts = np.zeros((21, 3), dtype=np.float32)
        raw_pts[0] = [10.0, 20.0, 5.0]  # Wrist offset
        raw_pts[9] = [10.0, 25.0, 5.0]  # Middle MCP 5 units away
        
        norm_feat = normalize_landmarks(raw_pts)
        self.assertEqual(norm_feat.shape, (63,))
        self.assertAlmostEqual(norm_feat[0], 0.0)

    def test_ackermann_physics_kinematics(self):
        phys = RealisticAckermannPhysics(x=400, y=300, max_speed_kmh=30.0)
        
        # Heading 90° (Up), target direction 90° (Up), CONTROL state
        x, y, psi, delta, speed_kmh = phys.update(
            target_direction_deg=90.0,
            target_throttle_ratio=1.0,
            state='CONTROL',
            bounds_w=1024,
            bounds_h=720
        )
        
        self.assertGreater(speed_kmh, 0.0)
        self.assertLess(y, 300.0) # Moving Up decreases y coordinate in Pygame

        # Turning test
        phys.update(target_direction_deg=45.0, target_throttle_ratio=1.0, state='CONTROL')
        self.assertNotEqual(phys.steering_delta, 0.0)

    def test_iot_motor_pwm_calculation(self):
        iot = IoTController()
        
        # Straight forward at 25 km/h -> PWML = 255, PWMR = 255
        pwml, pwmr = iot.calculate_motor_pwm(speed_kmh=25.0, steering_angle_deg=0.0)
        self.assertEqual(pwml, 255)
        self.assertEqual(pwmr, 255)

        # Turning right (+35° steer) -> PWML > PWMR
        pwml_r, pwmr_r = iot.calculate_motor_pwm(speed_kmh=20.0, steering_angle_deg=35.0)
        self.assertGreater(pwml_r, pwmr_r)

        # Telemetry packet format check
        pkt = iot.send_telemetry(speed_kmh=15.0, steering_angle_deg=10.0, state='CONTROL')
        self.assertEqual(pkt['cmd'], 'DRIVE')
        self.assertIn('pwml', pkt)
        self.assertIn('pwmr', pkt)

    def test_model_training_and_prediction(self):
        print("\n[Test] Running ML Model Training and Inference Test...")
        df = generate_synthetic_dataset(num_samples_per_angle=20)
        self.assertTrue(os.path.exists(DATASET_PATH))

        model_data = train_gesture_model()
        self.assertTrue(os.path.exists(MODEL_PATH))

        predictor = GesturePredictor()
        self.assertTrue(predictor.is_loaded)

        dummy_tracking = {
            'detected': True,
            'normalized_features': np.zeros(63, dtype=np.float32),
            'is_fist': False,
            'speed_factor': 0.75,
            'geometric_angle': 90.0
        }
        res = predictor.predict(dummy_tracking)
        self.assertIn('angle', res)
        self.assertIn('speed', res)
        self.assertIn('state', res)

    def test_left_right_hand_driving_option(self):
        print("\n[Test] Testing Left Hand (Forward) & Right Hand (Reverse) Driving Option...")
        predictor = GesturePredictor()

        # Left Hand Tracking Result
        left_hand_tracking = {
            'detected': True,
            'normalized_features': np.zeros(63, dtype=np.float32),
            'is_fist': False,
            'speed_factor': 0.8,
            'geometric_angle': 90.0,
            'hand_label': 'Left'
        }

        # Right Hand Tracking Result
        right_hand_tracking = {
            'detected': True,
            'normalized_features': np.zeros(63, dtype=np.float32),
            'is_fist': False,
            'speed_factor': 0.8,
            'geometric_angle': 90.0,
            'hand_label': 'Right'
        }

        # Test LEFT_FORWARD_RIGHT_REVERSE mode
        res_left = predictor.predict(left_hand_tracking, hand_drive_mode='LEFT_FORWARD_RIGHT_REVERSE')
        self.assertGreater(res_left['speed'], 0.0)
        self.assertEqual(res_left['state'], 'CONTROL')
        self.assertFalse(res_left['is_reverse'])

        res_right = predictor.predict(right_hand_tracking, hand_drive_mode='LEFT_FORWARD_RIGHT_REVERSE')
        self.assertLess(res_right['speed'], 0.0) # Speed is negative for Reverse
        self.assertEqual(res_right['state'], 'REVERSE')
        self.assertTrue(res_right['is_reverse'])

        # Test Reverse Motor PWM calculation for physical ESP32 car
        iot = IoTController()
        pwml_rev, pwmr_rev = iot.calculate_motor_pwm(speed_kmh=-20.0, steering_angle_deg=0.0)
        self.assertLess(pwml_rev, 0)
        self.assertLess(pwmr_rev, 0)
        print(f"[Test] Reverse speed (-20.0 km/h) -> PWML: {pwml_rev}, PWMR: {pwmr_rev} (DC motors reverse rotation)")

if __name__ == '__main__':
    unittest.main()
