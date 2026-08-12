import os
import math
import numpy as np
import joblib
from physics import shortest_angular_difference, lerp_angle

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'steering_model.pkl')

class GesturePredictor:
    def __init__(self, model_path=MODEL_PATH, preferred_mode='MEDIAPIPE_PRETRAINED'):
        """
        GesturePredictor interprets hand landmarks using:
        1. 'MEDIAPIPE_PRETRAINED': Direct real-time inference from MediaPipe's pre-trained 3D Neural Net model.
        2. 'CUSTOM_ML': Custom Random Forest model trained on normalized landmarks.
        """
        self.model_path = model_path
        self.preferred_mode = preferred_mode
        self.regressor = None
        self.classifier = None
        self.smoothed_angle = 90.0  # Initial angle pointing forward (90°)
        self.smoothing_alpha = 0.25 # Circular angle exponential filter coefficient
        self.is_custom_loaded = False
        self.is_loaded = False
        
        self.load_custom_model()

    def load_custom_model(self):
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.regressor = data['regressor']
                self.classifier = data['classifier']
                self.is_custom_loaded = True
                self.is_loaded = True
                print(f"[GesturePredictor] Loaded custom ML model from {self.model_path}")
            except Exception as e:
                print(f"[GesturePredictor] Custom model load error: {e}.")
                self.is_custom_loaded = False
                self.is_loaded = False
        else:
            self.is_custom_loaded = False
            self.is_loaded = False

    def predict(self, hand_tracking_result, mode=None):
        """
        Args:
            hand_tracking_result: dict output from HandTracker.process_frame()
            mode: optional override ('MEDIAPIPE_PRETRAINED' or 'CUSTOM_ML')
            
        Returns:
            dict containing:
                - 'angle': float (0-360)
                - 'speed': float (0.0 - 1.0)
                - 'state': str ('CONTROL', 'STOP', 'NO_HAND')
                - 'confidence': float (0-100)
                - 'mode': str ('MEDIAPIPE_PRETRAINED', 'CUSTOM_ML')
        """
        active_mode = mode or self.preferred_mode

        if not hand_tracking_result['detected']:
            return {
                'angle': self.smoothed_angle,
                'speed': 0.0,
                'state': 'NO_HAND',
                'confidence': 0.0,
                'mode': 'NO_HAND'
            }

        norm_feat = hand_tracking_result['normalized_features']
        is_fist = hand_tracking_result['is_fist']
        speed_factor = hand_tracking_result['speed_factor']
        geo_angle = hand_tracking_result['geometric_angle']

        # Closed fist detection (STOP gesture)
        if is_fist:
            return {
                'angle': self.smoothed_angle,
                'speed': 0.0,
                'state': 'STOP',
                'confidence': 98.0,
                'mode': 'MEDIAPIPE_PRETRAINED' if active_mode == 'MEDIAPIPE_PRETRAINED' else 'CUSTOM_ML'
            }

        # MODE 1: Direct MediaPipe Pre-trained Neural Network Inference
        if active_mode == 'MEDIAPIPE_PRETRAINED' or not self.is_custom_loaded:
            target_angle = geo_angle
            state = 'CONTROL'
            confidence = 95.0
            used_mode = 'MEDIAPIPE_PRETRAINED'

        # MODE 2: Custom Random Forest Model on top of MediaPipe Landmarks
        else:
            try:
                X = norm_feat.reshape(1, -1)
                sin_cos_pred = self.regressor.predict(X)[0]
                sin_val, cos_val = sin_cos_pred[0], sin_cos_pred[1]
                
                rad = math.atan2(sin_val, cos_val)
                target_angle = math.degrees(rad) % 360.0

                state_pred = self.classifier.predict(X)[0]
                state = str(state_pred)
                used_mode = 'CUSTOM_ML'
                confidence = 97.5
            except Exception as e:
                target_angle = geo_angle
                state = 'CONTROL'
                used_mode = 'MEDIAPIPE_PRETRAINED'
                confidence = 90.0

        # Apply circular angle smoothing across consecutive frames
        self.smoothed_angle = lerp_angle(self.smoothed_angle, target_angle, alpha=self.smoothing_alpha)

        return {
            'angle': self.smoothed_angle,
            'speed': speed_factor if state == 'CONTROL' else 0.0,
            'state': state,
            'confidence': confidence,
            'mode': used_mode
        }
