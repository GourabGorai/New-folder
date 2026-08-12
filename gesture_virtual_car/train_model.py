import os
import math
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score

from preprocessing import normalize_landmarks, WRIST, INDEX_TIP, MIDDLE_MCP

DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset', 'gesture_data.csv')
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'steering_model.pkl')

def generate_synthetic_dataset(num_samples_per_angle=100):
    """
    Generates synthetic hand landmark dataset for 12 angles (0°, 30°, ..., 330°)
    and 2 gesture states ('CONTROL', 'STOP').
    This enables immediate model training without requiring webcam recording upfront.
    """
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    rows = []
    
    angles = np.arange(0, 360, 30)
    
    for angle_deg in angles:
        rad = math.radians(angle_deg)
        cos_val = math.cos(rad)
        sin_val = math.sin(rad)
        
        for _ in range(num_samples_per_angle):
            # Base 21 3D hand skeleton in neutral pose pointing right
            landmarks = np.zeros((21, 3), dtype=np.float32)
            
            # Palm base landmarks
            landmarks[0] = [0.0, 0.0, 0.0]  # Wrist
            landmarks[1] = [0.1, 0.1, 0.0]  # Thumb CMC
            landmarks[2] = [0.2, 0.2, 0.0]  # Thumb MCP
            landmarks[3] = [0.3, 0.25, 0.0] # Thumb IP
            landmarks[4] = [0.4, 0.3, 0.0]  # Thumb Tip
            
            # Finger MCPs
            landmarks[5] = [0.4, 0.15, 0.0] # Index MCP
            landmarks[9] = [0.45, 0.0, 0.0] # Middle MCP
            landmarks[13] = [0.4, -0.15, 0.0] # Ring MCP
            landmarks[17] = [0.35, -0.3, 0.0] # Pinky MCP
            
            # Finger Tips (pointing right towards positive x)
            landmarks[8] = [0.85, 0.15, 0.0]  # Index Tip
            landmarks[12] = [0.95, 0.0, 0.0]  # Middle Tip
            landmarks[16] = [0.85, -0.15, 0.0] # Ring Tip
            landmarks[20] = [0.75, -0.3, 0.0] # Pinky Tip
            
            # Intermediate phalanges
            landmarks[6] = [0.6, 0.15, 0.0]
            landmarks[7] = [0.75, 0.15, 0.0]
            landmarks[10] = [0.65, 0.0, 0.0]
            landmarks[11] = [0.8, 0.0, 0.0]
            landmarks[14] = [0.6, -0.15, 0.0]
            landmarks[15] = [0.75, -0.15, 0.0]
            landmarks[18] = [0.5, -0.3, 0.0]
            landmarks[19] = [0.65, -0.3, 0.0]

            # Rotate skeleton by angle_deg (in screen space where y is inverted)
            # dx' = x cos(r) - y sin(r), dy' = x sin(r) + y cos(r)
            rot_matrix = np.array([
                [cos_val, -sin_val, 0.0],
                [-sin_val, -cos_val, 0.0], # screen y reflection
                [0.0, 0.0, 1.0]
            ])
            
            rotated_pts = np.dot(landmarks, rot_matrix.T)
            
            # Add Gaussian noise for realistic tracking jitter
            noise = np.random.normal(0.0, 0.02, rotated_pts.shape)
            noisy_pts = rotated_pts + noise
            
            # Normalize features
            norm_feat = normalize_landmarks(noisy_pts)
            
            row = list(norm_feat) + [sin_val, cos_val, angle_deg, 'CONTROL']
            rows.append(row)

    # Generate STOP gesture (closed fist) samples
    for _ in range(num_samples_per_angle * 3):
        landmarks = np.zeros((21, 3), dtype=np.float32)
        landmarks[0] = [0.0, 0.0, 0.0]
        # Contracted fingertips close to wrist
        for i in [4, 8, 12, 16, 20]:
            landmarks[i] = np.random.normal(0.2, 0.04, 3)
        for i in range(1, 21):
            if i not in [4, 8, 12, 16, 20]:
                landmarks[i] = np.random.normal(0.15, 0.03, 3)

        norm_feat = normalize_landmarks(landmarks)
        row = list(norm_feat) + [0.0, 1.0, 90.0, 'STOP']
        rows.append(row)

    columns = [f'f_{i}' for i in range(63)] + ['sin_angle', 'cos_angle', 'angle_deg', 'state']
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(DATASET_PATH, index=False)
    print(f"Synthetic dataset created with {len(df)} samples at {DATASET_PATH}")
    return df

def train_gesture_model():
    """
    Trains ML models:
    1. Regressor predicting (sin_theta, cos_theta)
    2. Classifier predicting gesture state ('CONTROL', 'STOP')
    """
    df = generate_synthetic_dataset(num_samples_per_angle=100)

    X = df[[f'f_{i}' for i in range(63)]].values
    y_reg = df[['sin_angle', 'cos_angle']].values
    y_cls = df['state'].values

    X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = train_test_split(
        X, y_reg, y_cls, test_size=0.2, random_state=42
    )

    print("Training Random Forest Regressor for (sin, cos) continuous steering...")
    regressor = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
    regressor.fit(X_train, y_reg_train)

    print("Training Random Forest Classifier for gesture state...")
    classifier = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
    classifier.fit(X_train, y_cls_train)

    # Evaluate
    reg_pred = regressor.predict(X_test)
    mse = mean_squared_error(y_reg_test, reg_pred)

    cls_pred = classifier.predict(X_test)
    acc = accuracy_score(y_cls_test, cls_pred)

    print(f"Model Evaluation -> MSE (sin, cos): {mse:.6f} | State Accuracy: {acc*100:.2f}%")

    os.makedirs(MODEL_DIR, exist_ok=True)
    model_data = {
        'regressor': regressor,
        'classifier': classifier,
        'feature_names': [f'f_{i}' for i in range(63)]
    }
    joblib.dump(model_data, MODEL_PATH)
    print(f"Model saved successfully to {MODEL_PATH}")
    return model_data

if __name__ == '__main__':
    train_gesture_model()
