import math
import numpy as np

def shortest_angular_difference(from_deg, to_deg):
    """
    Computes shortest difference between two angles in degrees [-180, 180].
    """
    diff = (to_deg - from_deg + 180.0) % 360.0 - 180.0
    return float(diff)

def lerp_angle(current_deg, target_deg, alpha=0.15):
    """
    Smoothly interpolates current_deg towards target_deg using circular shortest path.
    """
    diff = shortest_angular_difference(current_deg, target_deg)
    new_deg = (current_deg + alpha * diff) % 360.0
    return float(new_deg)

class RealisticAckermannPhysics:
    """
    Implements realistic Ackermann Vehicle Steering Kinematics:
    - Wheelbase (L): Distance between front and rear axle.
    - Steering Angle (delta): Turning angle of front wheels [-35°, +35°].
    - Vehicle Heading (psi): Physical orientation direction of vehicle [0°, 360°].
    - Velocity (v): Forward/Reverse vehicle speed with momentum and tire friction.
    """
    def __init__(self, x=400, y=300, max_speed_kmh=30.0, wheelbase=36.0):
        self.x = float(x)
        self.y = float(y)
        self.heading_psi = 90.0         # Vehicle orientation angle (90° = Up/Forward)
        self.steering_delta = 0.0       # Front wheel turn angle [-35°, +35°]
        self.speed_kmh = 0.0            # Vehicle speed in km/h
        
        self.wheelbase = float(wheelbase)
        self.max_speed_kmh = float(max_speed_kmh)
        self.max_steer_angle_deg = 35.0 # Max front wheel turn angle
        
        self.acceleration_rate = 0.5
        self.brake_rate = 0.8
        self.friction_rate = 0.12
        self.steering_return_speed = 0.15 # Self-centering steering wheel rate

    def update(self, target_direction_deg, target_throttle_ratio, state, bounds_w=1024, bounds_h=720, car_radius=20):
        """
        Updates realistic Ackermann vehicle kinematics for one frame.
        
        Args:
            target_direction_deg: Target steering direction angle from hand gesture [0, 360).
            target_throttle_ratio: Desired speed scale [0.0, 1.0].
            state: Gesture state ('CONTROL', 'STOP', 'NO_HAND').
        """
        # 1. Calculate relative steering wheel offset [-35°, +35°] relative to vehicle heading
        diff_to_target = shortest_angular_difference(self.heading_psi, target_direction_deg)
        target_steer_delta = np.clip(diff_to_target, -self.max_steer_angle_deg, self.max_steer_angle_deg)

        if state == 'STOP' or state == 'NO_HAND':
            # Active Braking / Kinetic Friction Deceleration
            if self.speed_kmh > 0:
                self.speed_kmh = max(0.0, self.speed_kmh - self.brake_rate * 2.0)
            elif self.speed_kmh < 0:
                self.speed_kmh = min(0.0, self.speed_kmh + self.brake_rate * 2.0)
            
            # Steering self-centers to 0°
            self.steering_delta *= (1.0 - self.steering_return_speed)
        else:
            # Active Throttle & Steering
            desired_speed_kmh = self.max_speed_kmh * max(0.0, min(1.0, target_throttle_ratio))

            if self.speed_kmh < desired_speed_kmh:
                self.speed_kmh = min(desired_speed_kmh, self.speed_kmh + self.acceleration_rate)
            elif self.speed_kmh > desired_speed_kmh:
                self.speed_kmh = max(desired_speed_kmh, self.speed_kmh - self.brake_rate)

            # Smooth front wheel turn response towards target steer angle
            self.steering_delta += 0.25 * (target_steer_delta - self.steering_delta)

        # Apply tire rolling friction
        if self.speed_kmh > 0:
            self.speed_kmh = max(0.0, self.speed_kmh - self.friction_rate)

        # 2. Ackermann Kinematics: Calculate turning angular velocity omega = (v / L) * tan(delta)
        speed_px = self.speed_kmh * 0.35  # Scale km/h to canvas pixels per frame
        
        if abs(self.speed_kmh) > 0.1 and abs(self.steering_delta) > 0.5:
            rad_steer = math.radians(self.steering_delta)
            angular_velocity_rad = (speed_px / self.wheelbase) * math.tan(rad_steer)
            angular_velocity_deg = math.degrees(angular_velocity_rad)
            self.heading_psi = (self.heading_psi + angular_velocity_deg) % 360.0

        # 3. Compute movement vector along vehicle heading orientation
        rad_heading = math.radians(self.heading_psi)
        dx = speed_px * math.cos(rad_heading)
        dy = -speed_px * math.sin(rad_heading)  # Invert dy for Pygame y-down screen coordinates

        self.x += dx
        self.y += dy

        # 4. Canvas Boundary Clamping
        self.x = float(np.clip(self.x, car_radius + 15, bounds_w - car_radius - 15))
        self.y = float(np.clip(self.y, car_radius + 115, bounds_h - car_radius - 15))

        return self.x, self.y, self.heading_psi, self.steering_delta, self.speed_kmh

# Backwards compatibility alias
VehiclePhysics = RealisticAckermannPhysics
