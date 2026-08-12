import cv2
import os
import math
import numpy as np
import pandas as pd
from hand_tracker import HandTracker

DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset', 'gesture_data.csv')

def run_data_collection():
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    tracker = HandTracker()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera not detected! Automated simulation dataset will be used.")
        return

    print("==========================================================")
    print("           LIVE HAND GESTURE DATA COLLECTION              ")
    print("==========================================================")
    print(" Controls:")
    print("  '0' to '9': Record sample for angle = (key * 36) degrees")
    print("  's': Record STOP gesture sample")
    print("  'q': Quit data collection")
    print("==========================================================")

    records = []
    
    # Load existing if available
    if os.path.exists(DATASET_PATH):
        df_existing = pd.read_csv(DATASET_PATH)
        records = df_existing.values.tolist()

    cols = [f'f_{i}' for i in range(63)] + ['sin_angle', 'cos_angle', 'angle_deg', 'state']

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        res = tracker.process_frame(frame)
        display_frame = res['annotated_frame']

        cv2.putText(display_frame, f"Collected: {len(records)} samples", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, "Press 0-9 for direction, S for stop, Q to save", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        if res['detected']:
            cv2.putText(display_frame, f"Hand Detected | Geo Angle: {res['geometric_angle']:.1f}deg",
                        (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

        cv2.imshow("Hand Gesture Data Collector", display_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif res['detected']:
            feat = list(res['normalized_features'])
            if ord('0') <= key <= ord('9'):
                target_deg = (key - ord('0')) * 36.0
                rad = math.radians(target_deg)
                records.append(feat + [math.sin(rad), math.cos(rad), target_deg, 'CONTROL'])
                print(f"Recorded sample for Angle: {target_deg}°")
            elif key == ord('s'):
                records.append(feat + [0.0, 1.0, 90.0, 'STOP'])
                print("Recorded sample for STOP gesture")

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()

    if records:
        df = pd.DataFrame(records, columns=cols)
        df.to_csv(DATASET_PATH, index=False)
        print(f"Saved {len(records)} total samples to {DATASET_PATH}")

if __name__ == '__main__':
    run_data_collection()
