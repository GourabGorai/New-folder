import pygame
import math
from physics import RealisticAckermannPhysics

class Car:
    def __init__(self, x=400, y=300, width=54, height=28, color=(235, 50, 50)):
        self.width = width
        self.height = height
        self.color = color
        self.physics = RealisticAckermannPhysics(x=x, y=y)

    def draw(self, surface, is_braking=False):
        """
        Renders a realistic sports car chassis with articulated front turning wheels,
        headlight beams, brake tail-lights, and trajectory pointer.
        """
        # Create chassis surface
        car_surf = pygame.Surface((self.width + 20, self.height + 20), pygame.SRCALPHA)
        offset_x, offset_y = 10, 10

        # Rear Fixed Wheels (2 black rounded rects)
        wheel_w, wheel_h = 11, 5
        pygame.draw.rect(car_surf, (20, 20, 25), (offset_x + 8, offset_y + 0, wheel_w, wheel_h), border_radius=2)
        pygame.draw.rect(car_surf, (20, 20, 25), (offset_x + 8, offset_y + self.height - wheel_h, wheel_w, wheel_h), border_radius=2)

        # Front Articulated Turning Wheels (pivot dynamically by steering_delta)
        steer_angle = self.physics.steering_delta
        
        for wy in [offset_y + 0, offset_y + self.height - wheel_h]:
            wheel_surf = pygame.Surface((wheel_w, wheel_h), pygame.SRCALPHA)
            pygame.draw.rect(wheel_surf, (35, 35, 40), (0, 0, wheel_w, wheel_h), border_radius=2)
            pygame.draw.rect(wheel_surf, (200, 200, 200), (3, 1, 5, 3), border_radius=1) # Rim accent
            
            # Rotate front wheel by front steering angle
            rot_wheel = pygame.transform.rotate(wheel_surf, -steer_angle) # Pygame rotation direction
            w_rect = rot_wheel.get_rect(center=(offset_x + self.width - 12, wy + wheel_h // 2))
            car_surf.blit(rot_wheel, w_rect.topleft)

        # Main Vehicle Body (sleek aerodynamic chassis)
        body_rect = pygame.Rect(offset_x + 6, offset_y + 3, self.width - 12, self.height - 6)
        pygame.draw.rect(car_surf, self.color, body_rect, border_radius=7)
        pygame.draw.rect(car_surf, (160, 20, 20), body_rect, width=2, border_radius=7)

        # Windshield & Roof Canopy (Dark glass tint)
        roof_rect = pygame.Rect(offset_x + 20, offset_y + 6, 16, self.height - 12)
        pygame.draw.rect(car_surf, (30, 60, 95), roof_rect, border_radius=4)
        pygame.draw.rect(car_surf, (180, 220, 255), (offset_x + 30, offset_y + 7, 5, self.height - 14), border_radius=2) # Glass reflection

        # Headlight Beams (Front right glow)
        hl_color = (255, 240, 150)
        pygame.draw.circle(car_surf, hl_color, (offset_x + self.width - 5, offset_y + 7), 3)
        pygame.draw.circle(car_surf, hl_color, (offset_x + self.width - 5, offset_y + self.height - 7), 3)

        # Rear Brake Tail-lights (Bright red glow when braking/stopped)
        brake_color = (255, 20, 20) if is_braking else (140, 20, 20)
        pygame.draw.rect(car_surf, brake_color, (offset_x + 5, offset_y + 5, 3, 5), border_radius=1)
        pygame.draw.rect(car_surf, brake_color, (offset_x + 5, offset_y + self.height - 10, 3, 5), border_radius=1)

        # Rotate entire car surface to physical heading orientation angle
        rotated_car = pygame.transform.rotate(car_surf, self.physics.heading_psi)
        rect = rotated_car.get_rect(center=(int(self.physics.x), int(self.physics.y)))
        surface.blit(rotated_car, rect.topleft)

        # Draw Headlight Cone Beams onto world plane
        rad_heading = math.radians(self.physics.heading_psi)
        cos_h, sin_h = math.cos(rad_heading), -math.sin(rad_heading)
        
        beam_len = 70
        fx, fy = self.physics.x + 25 * cos_h, self.physics.y + 25 * sin_h
        left_beam = (fx + beam_len * math.cos(rad_heading + 0.25), fy - beam_len * math.sin(rad_heading + 0.25))
        right_beam = (fx + beam_len * math.cos(rad_heading - 0.25), fy - beam_len * math.sin(rad_heading - 0.25))

        beam_surf = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (255, 255, 200, 35), [(fx, fy), left_beam, right_beam])
        surface.blit(beam_surf, (0, 0))

    def update(self, target_angle, target_speed_ratio, state, bounds_w=1024, bounds_h=720):
        return self.physics.update(target_angle, target_speed_ratio, state, bounds_w, bounds_h, car_radius=self.width // 2)
