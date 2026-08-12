import cv2
import numpy as np

# Robust import handling across different MediaPipe versions (0.10.x vs 0.9.x)
try:
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.drawing_utils as mp_draw
    import mediapipe.python.solutions.drawing_styles as mp_drawing_styles
except ImportError:
    try:
        import mediapipe.solutions.hands as mp_hands
        import mediapipe.solutions.drawing_utils as mp_draw
        import mediapipe.solutions.drawing_styles as mp_drawing_styles
    except ImportError:
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles

from preprocessing import normalize_landmarks, compute_geometric_angle, is_closed_fist, compute_speed_factor

class HandTracker:
    def __init__(self, max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        self.mp_hands = mp_hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_draw = mp_draw
        self.mp_drawing_styles = mp_drawing_styles

    def process_frame(self, frame):
        """
        Processes an OpenCV BGR frame.
        
        Returns:
            dict containing:
                - 'detected': bool
                - 'raw_landmarks': list of (21, 3)
                - 'normalized_features': np.ndarray of shape (63,)
                - 'annotated_frame': frame with drawn landmarks
                - 'geometric_angle': float (0-360)
                - 'is_fist': bool
                - 'speed_factor': float (0.2-1.0)
                - 'hand_label': str ('Left', 'Right', 'NONE')
        """
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        annotated_frame = frame.copy()
        output = {
            'detected': False,
            'raw_landmarks': None,
            'normalized_features': None,
            'annotated_frame': annotated_frame,
            'geometric_angle': 90.0,
            'is_fist': False,
            'speed_factor': 0.0,
            'hand_label': 'NONE'
        }

        if results.multi_hand_landmarks:
            # Grab first detected hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # Extract handedness label ('Left' or 'Right')
            hand_label = 'Right'
            if results.multi_handedness and len(results.multi_handedness) > 0:
                try:
                    hand_label = results.multi_handedness[0].classification[0].label
                except Exception:
                    hand_label = 'Right'

            # Extract (x, y, z) points
            pts = []
            for lm in hand_landmarks.landmark:
                pts.append([lm.x, lm.y, lm.z])
            pts = np.array(pts, dtype=np.float32)

            # Draw landmarks on frame
            self.mp_draw.draw_landmarks(
                annotated_frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )

            # Overlay hand label text on frame
            badge_color = (0, 255, 180) if hand_label == 'Left' else (255, 180, 0)
            cv2.putText(
                annotated_frame,
                f"HAND: {hand_label.upper()}",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                badge_color,
                2
            )

            norm_features = normalize_landmarks(pts)
            geo_angle = compute_geometric_angle(pts)
            fist = is_closed_fist(pts)
            speed = compute_speed_factor(pts)

            output['detected'] = True
            output['raw_landmarks'] = pts
            output['normalized_features'] = norm_features
            output['annotated_frame'] = annotated_frame
            output['geometric_angle'] = geo_angle
            output['is_fist'] = fist
            output['speed_factor'] = speed
            output['hand_label'] = hand_label

        return output

    def close(self):
        self.hands.close()
