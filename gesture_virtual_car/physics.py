import math
import numpy as np

def shortest_angular_difference(from_deg, to_deg):
    """
    Computes shortest difference between two angles in degrees [-180, 180].
    Prevents wrap-around jumps across 0/360 degrees.
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

class VehiclePhysics:
    def __init__(self, x=400, y=300, max_speed=8.0, acceleration=0.4, deceleration=0.6, friction=0.15):
        self.x = float(x)
        self.y = float(y)
        self.heading_angle = 90.0  # Initial heading pointing Up (90 degrees)
        self.speed = 0.0
        
        self.max_speed = float(max_speed)
        self.acceleration = float(acceleration)
        self.deceleration = float(deceleration)
        self.friction = float(friction)
        self.dead_zone_deg = 4.0

    def update(self, target_angle_deg, target_speed_ratio, state, bounds_width=800, bounds_height=600, car_radius=20):
        """
        Updates car physics for one frame.
        
        Args:
            target_angle_deg: Steering angle requested by gesture/keyboard [0, 360).
            target_speed_ratio: Desired speed multiplier [0.0, 1.0].
            state: Gesture state string ('CONTROL', 'STOP', 'NO_HAND').
            bounds_width: Simulator boundary width.
            bounds_height: Simulator boundary height.
            car_radius: Collision margin from edges.
        """
        if state == 'STOP' or state == 'NO_HAND':
            # Decelerate to stop due to friction / brakes
            if self.speed > 0:
                self.speed = max(0.0, self.speed - self.deceleration)
            elif self.speed < 0:
                self.speed = min(0.0, self.speed + self.deceleration)
        else:
            # Active control
            desired_speed = self.max_speed * max(0.0, min(1.0, target_speed_ratio))
            
            # Accelerate or decelerate towards desired speed
            if self.speed < desired_speed:
                self.speed = min(desired_speed, self.speed + self.acceleration)
            elif self.speed > desired_speed:
                self.speed = max(desired_speed, self.speed - self.deceleration)

            # Apply dead-zone filter to steering
            diff = shortest_angular_difference(self.heading_angle, target_angle_deg)
            if abs(diff) > self.dead_zone_deg:
                self.heading_angle = lerp_angle(self.heading_angle, target_angle_deg, alpha=0.18)

        # Apply friction
        if self.speed > 0:
            self.speed = max(0.0, self.speed - self.friction)

        # Compute movement vector (0° = Right, 90° = Up, 180° = Left, 270° = Down)
        rad = math.radians(self.heading_angle)
        dx = self.speed * math.cos(rad)
        dy = -self.speed * math.sin(rad)  # Invert dy for Pygame screen coordinates

        self.x += dx
        self.y += dy

        # Boundary collision enforcement (clamp within canvas)
        self.x = float(np.clip(self.x, car_radius, bounds_width - car_radius))
        self.y = float(np.clip(self.y, car_radius, bounds_height - car_radius))

        return self.x, self.y, self.heading_angle, self.speed
