import cv2
import pygame
import sys
import os
import math

from hand_tracker import HandTracker
from gesture_predictor import GesturePredictor
from simulator import CarSimulator
from train_model import train_gesture_model, MODEL_PATH

def main():
    print("==========================================================")
    print("      GESTURE CONTROLLED CAR SIMULATOR PROTOTYPE          ")
    print("==========================================================")
    
    # 1. Ensure baseline ML Model exists for option 2
    if not os.path.exists(MODEL_PATH):
        print("Pre-generating custom ML model fallback...")
        train_gesture_model()

    # 2. Initialize components (Defaulting to Pre-trained MediaPipe Hands Model)
    tracker = HandTracker()
    predictor = GesturePredictor(preferred_mode='MEDIAPIPE_PRETRAINED')
    sim = CarSimulator(width=1024, height=720)

    # 3. OpenCV Camera Capture
    cap = cv2.VideoCapture(0)
    camera_available = cap.isOpened()

    if camera_available:
        print("[Camera] OpenCV VideoCapture(0) opened. Using MediaPipe Pre-trained Model.")
    else:
        print("[Camera] Webcam not detected. Defaulting to KEYBOARD Mode (Press 'K' to toggle).")
        sim.control_mode = 'KEYBOARD'

    # Keyboard control persistent state variables
    kb_angle = 90.0
    kb_speed_ratio = 0.0

    running = True
    print("\n[Simulator] Controls:")
    print("  - Press 'H': Toggle Hand Drive Option (All Hands Forward vs Left=Forward / Right=Reverse)")
    print("  - Press 'M': Toggle between MediaPipe Pre-trained Model & Custom RF Model")
    print("  - Press 'K': Toggle Keyboard Mode")
    print("  - Press 'R': Reset Car Position")
    print("  - Press 'ESC': Quit Simulator\n")

    while running:
        # Handle Pygame UI events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_k:
                    # Toggle Control Mode (Gesture vs Keyboard)
                    if sim.control_mode == 'KEYBOARD':
                        sim.control_mode = 'GESTURE'
                        print(f"[Mode] Switched to GESTURE Mode ({predictor.preferred_mode}).")
                    else:
                        sim.control_mode = 'KEYBOARD'
                        print("[Mode] Switched to KEYBOARD Mode.")
                elif event.key == pygame.K_h:
                    # Toggle Hand Drive Option (All Hands Forward vs Left=Forward / Right=Reverse)
                    if sim.hand_drive_mode == 'ALL_HANDS_FORWARD':
                        sim.hand_drive_mode = 'LEFT_FORWARD_RIGHT_REVERSE'
                        print("[Hand Option] Switched to LEFT_FORWARD_RIGHT_REVERSE (Left Hand = Forward, Right Hand = Reverse).")
                    else:
                        sim.hand_drive_mode = 'ALL_HANDS_FORWARD'
                        print("[Hand Option] Switched to ALL_HANDS_FORWARD (All hands drive forward).")
                elif event.key == pygame.K_m:
                    # Toggle Model Mode (MediaPipe Pretrained vs Custom ML)
                    if predictor.preferred_mode == 'MEDIAPIPE_PRETRAINED':
                        predictor.preferred_mode = 'CUSTOM_ML'
                        print("[Model] Switched to CUSTOM_ML (Random Forest Model).")
                    else:
                        predictor.preferred_mode = 'MEDIAPIPE_PRETRAINED'
                        print("[Model] Switched to MEDIAPIPE_PRETRAINED (Pre-trained MediaPipe Model).")
                    sim.control_mode = 'GESTURE'
                elif event.key == pygame.K_r:
                    sim.reset_car()
                    print("[Car] Position reset to center.")

        # Process Camera Hand Tracking
        camera_frame = None
        gesture_data = {
            'angle': kb_angle,
            'speed': 0.0,
            'state': 'STOP',
            'confidence': 0.0,
            'mode': 'KEYBOARD',
            'hand_label': 'NONE',
            'hand_drive_mode': sim.hand_drive_mode,
            'is_reverse': False
        }

        if camera_available and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                hand_res = tracker.process_frame(frame)
                camera_frame = hand_res['annotated_frame']
                
                if sim.control_mode == 'GESTURE':
                    gesture_data = predictor.predict(hand_res, hand_drive_mode=sim.hand_drive_mode)

        # Process Keyboard Inputs if in KEYBOARD Mode
        if sim.control_mode == 'KEYBOARD':
            keys = pygame.key.get_pressed()
            dx_kb = 0.0
            dy_kb = 0.0
            
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy_kb += 1.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy_kb -= 1.0
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx_kb += 1.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx_kb -= 1.0

            if dx_kb != 0.0 or dy_kb != 0.0:
                rad = math.atan2(dy_kb, dx_kb)
                kb_angle = math.degrees(rad) % 360.0
                kb_speed_ratio = 0.8
                state_str = 'CONTROL'
            else:
                kb_speed_ratio = 0.0
                state_str = 'STOP'

            gesture_data = {
                'angle': kb_angle,
                'speed': kb_speed_ratio,
                'state': state_str,
                'confidence': 100.0,
                'mode': 'KEYBOARD'
            }

        # Update Car position & physics
        target_angle = gesture_data['angle']
        speed_ratio = gesture_data['speed']
        state = gesture_data['state']

        sim.car.update(
            target_angle=target_angle,
            target_speed_ratio=speed_ratio,
            state=state,
            bounds_w=sim.width,
            bounds_h=sim.height
        )

        # Render frame
        sim.render_frame(gesture_data, camera_frame)

    # Cleanup
    if cap:
        cap.release()
    tracker.close()
    sim.close()
    print("[Simulator] Closed successfully.")

if __name__ == '__main__':
    main()
