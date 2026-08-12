import numpy as np
import math

# MediaPipe Landmark Index Constants
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20

def normalize_landmarks(landmarks):
    """
    Normalizes 21 MediaPipe hand landmarks (x, y, z):
    1. Wrist normalization: subtract wrist (x, y, z) from all landmarks.
    2. Scale normalization: divide by distance between wrist and middle finger MCP.
    
    Args:
        landmarks: numpy array or list of shape (21, 3) or 63 values.
        
    Returns:
        np.ndarray of shape (63,) normalized feature vector.
    """
    pts = np.array(landmarks, dtype=np.float32)
    if pts.shape == (63,):
        pts = pts.reshape(21, 3)
    elif pts.shape != (21, 3):
        raise ValueError(f"Expected shape (21, 3) or (63,), got {pts.shape}")

    # Step 1: Wrist normalization (wrist at origin 0,0,0)
    wrist = pts[WRIST].copy()
    norm_pts = pts - wrist

    # Step 2: Scale normalization based on palm size (distance from wrist to middle finger MCP)
    palm_size = np.linalg.norm(norm_pts[MIDDLE_MCP])
    if palm_size > 1e-6:
        norm_pts = norm_pts / palm_size

    return norm_pts.flatten()

def compute_geometric_angle(landmarks):
    """
    Computes direct geometric steering angle (in degrees 0-360) from index finger vector
    relative to wrist.
    
    Returns:
        angle_deg: angle in degrees [0, 360).
                   90° = Up (Forward), 0° = Right, 270° = Down (Backward), 180° = Left.
    """
    pts = np.array(landmarks, dtype=np.float32)
    if pts.shape == (63,):
        pts = pts.reshape(21, 3)

    wrist = pts[WRIST]
    index_tip = pts[INDEX_TIP]

    # In screen coordinates, y increases downwards.
    # dx = index_tip.x - wrist.x
    # dy = wrist.y - index_tip.y  (invert y so up is positive y)
    dx = index_tip[0] - wrist[0]
    dy = wrist[1] - index_tip[1]

    rad = math.atan2(dy, dx)
    deg = math.degrees(rad) % 360.0
    return float(deg)

def is_closed_fist(landmarks):
    """
    Determines if hand forms a closed fist (STOP gesture).
    Checks average distance of fingertips to wrist compared to palm scale.
    """
    pts = np.array(landmarks, dtype=np.float32)
    if pts.shape == (63,):
        pts = pts.reshape(21, 3)

    wrist = pts[WRIST]
    palm_size = np.linalg.norm(pts[MIDDLE_MCP] - wrist)
    if palm_size < 1e-6:
        return False

    tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    avg_tip_dist = np.mean([np.linalg.norm(pts[t] - wrist) for t in tips])

    # If average fingertip distance is less than ~1.2x palm size, fist is closed
    return bool((avg_tip_dist / palm_size) < 1.25)

def compute_speed_factor(landmarks):
    """
    Estimates speed factor [0.0, 1.0] based on thumb-index pinch distance relative to palm scale.
    Small distance -> Slow (~0.3), Large open hand -> Fast (~1.0).
    """
    pts = np.array(landmarks, dtype=np.float32)
    if pts.shape == (63,):
        pts = pts.reshape(21, 3)

    wrist = pts[WRIST]
    palm_size = np.linalg.norm(pts[MIDDLE_MCP] - wrist)
    if palm_size < 1e-6:
        return 0.5

    pinch_dist = np.linalg.norm(pts[THUMB_TIP] - pts[INDEX_TIP])
    ratio = pinch_dist / palm_size

    # Map ratio from [0.2, 1.2] to speed [0.2, 1.0]
    speed = np.clip((ratio - 0.2) / 1.0, 0.2, 1.0)
    return float(speed)
