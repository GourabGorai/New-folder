import os
import math
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import classification_report, accuracy_score
from physics import shortest_angular_difference

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'steering_model.pkl')
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset', 'gesture_data.csv')

def evaluate():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(DATASET_PATH):
        print("Model or dataset missing. Please run train_model.py first.")
        return

    model_data = joblib.load(MODEL_PATH)
    regressor = model_data['regressor']
    classifier = model_data['classifier']

    df = pd.read_csv(DATASET_PATH)
    X = df[[f'f_{i}' for i in range(63)]].values
    y_sin_cos = df[['sin_angle', 'cos_angle']].values
    y_angle_actual = df['angle_deg'].values
    y_state_actual = df['state'].values

    # Angle predictions
    pred_sin_cos = regressor.predict(X)
    pred_angles = []
    angular_errors = []

    for i in range(len(X)):
        sin_v, cos_v = pred_sin_cos[i]
        rad = math.atan2(sin_v, cos_v)
        deg = math.degrees(rad) % 360.0
        pred_angles.append(deg)

        actual_deg = y_angle_actual[i]
        err = abs(shortest_angular_difference(actual_deg, deg))
        angular_errors.append(err)

    maae = np.mean(angular_errors)
    max_err = np.max(angular_errors)

    # State predictions
    pred_states = classifier.predict(X)
    acc = accuracy_score(y_state_actual, pred_states)
    report = classification_report(y_state_actual, pred_states)

    print("==================================================")
    print("      GESTURE CONTROLLED CAR ML EVALUATION        ")
    print("==================================================")
    print(f"Mean Absolute Angular Error (MAAE): {maae:.2f}°")
    print(f"Max Angular Error:                {max_err:.2f}°")
    print(f"Gesture State Classification Acc:  {acc * 100:.2f}%")
    print("\nDetailed Classification Report:")
    print(report)

if __name__ == '__main__':
    evaluate()
