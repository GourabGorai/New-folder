import os
import unittest
import numpy as np
import math
import joblib

# Set Pygame headless driver before importing Pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"

from preprocessing import normalize_landmarks, compute_geometric_angle, is_closed_fist, compute_speed_factor
from physics import VehiclePhysics, shortest_angular_difference, lerp_angle
from car import Car
from train_model import generate_synthetic_dataset, train_gesture_model, MODEL_PATH, DATASET_PATH
from gesture_predictor import GesturePredictor

class TestGestureCarSimulator(unittest.TestCase):

    def test_preprocessing_normalization(self):
        # Create dummy 21 landmarks
        raw_pts = np.zeros((21, 3), dtype=np.float32)
        raw_pts[0] = [10.0, 20.0, 5.0]  # Wrist offset
        raw_pts[9] = [10.0, 25.0, 5.0]  # Middle MCP 5 units away in y
        
        norm_feat = normalize_landmarks(raw_pts)
        self.assertEqual(norm_feat.shape, (63,))
        # Wrist at origin
        self.assertAlmostEqual(norm_feat[0], 0.0)
        self.assertAlmostEqual(norm_feat[1], 0.0)
        self.assertAlmostEqual(norm_feat[2], 0.0)

    def test_geometric_angle_calculation(self):
        # Index tip directly above wrist -> 90 degrees (Up / Forward)
        pts_up = np.zeros((21, 3), dtype=np.float32)
        pts_up[0] = [0.0, 0.0, 0.0]   # Wrist
        pts_up[8] = [0.0, -1.0, 0.0]  # Index tip (y is negative in screen coordinates)
        deg_up = compute_geometric_angle(pts_up)
        self.assertAlmostEqual(deg_up, 90.0, places=1)

        # Index tip to the right of wrist -> 0 degrees (Right)
        pts_right = np.zeros((21, 3), dtype=np.float32)
        pts_right[0] = [0.0, 0.0, 0.0]
        pts_right[8] = [1.0, 0.0, 0.0]
        deg_right = compute_geometric_angle(pts_right)
        self.assertAlmostEqual(deg_right, 0.0, places=1)

    def test_circular_angle_math(self):
        # Shortest difference from 355° to 5° should be +10°
        diff = shortest_angular_difference(355.0, 5.0)
        self.assertAlmostEqual(diff, 10.0, places=2)

        # Lerp from 355° to 5°
        lerped = lerp_angle(355.0, 5.0, alpha=0.5)
        self.assertAlmostEqual(lerped, 0.0, places=2)

    def test_vehicle_physics_movement_and_boundary(self):
        phys = VehiclePhysics(x=400, y=300, max_speed=10.0)
        
        # Heading 0° (Right), speed ratio 1.0, CONTROL state
        phys.update(target_angle_deg=0.0, target_speed_ratio=1.0, state='CONTROL', bounds_width=800, bounds_height=600)
        self.assertGreater(phys.speed, 0.0)
        self.assertGreater(phys.x, 400.0)
        self.assertAlmostEqual(phys.y, 300.0, delta=2.0)  # dy near 0 for turning towards 0 degrees

        # STOP state should decelerate speed
        initial_speed = phys.speed
        phys.update(target_angle_deg=0.0, target_speed_ratio=1.0, state='STOP', bounds_width=800, bounds_height=600)
        self.assertLess(phys.speed, initial_speed)

    def test_model_training_and_prediction(self):
        print("\n[Test] Running ML Dataset Generation and Model Training...")
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
        self.assertEqual(res['state'], 'CONTROL')

if __name__ == '__main__':
    unittest.main()
