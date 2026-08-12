import pygame
import math
from physics import VehiclePhysics

class Car:
    def __init__(self, x=400, y=300, width=50, height=26, color=(235, 50, 50)):
        self.width = width
        self.height = height
        self.color = color
        self.physics = VehiclePhysics(x=x, y=y)
        
        # Create base vehicle surface pointing right (0 degrees)
        self.base_surface = self._create_procedural_car_surface()

    def _create_procedural_car_surface(self):
        """
        Procedurally draws a stylized sports car sprite pointing to the right (0 degrees).
        """
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Main Body (sleek rounded rectangle)
        body_rect = pygame.Rect(4, 2, self.width - 8, self.height - 4)
        pygame.draw.rect(surf, self.color, body_rect, border_radius=6)
        pygame.draw.rect(surf, (180, 20, 20), body_rect, width=2, border_radius=6)

        # Wheels (4 black rectangles)
        wheel_color = (30, 30, 35)
        pygame.draw.rect(surf, wheel_color, (6, 0, 10, 4), border_radius=2)
        pygame.draw.rect(surf, wheel_color, (6, self.height - 4, 10, 4), border_radius=2)
        pygame.draw.rect(surf, wheel_color, (self.width - 16, 0, 10, 4), border_radius=2)
        pygame.draw.rect(surf, wheel_color, (self.width - 16, self.height - 4, 10, 4), border_radius=2)

        # Windshield & Roof (dark blue/grey transparent tint)
        windshield_rect = pygame.Rect(self.width // 2 - 4, 5, 14, self.height - 10)
        pygame.draw.rect(surf, (40, 80, 120), windshield_rect, border_radius=4)
        
        # Headlights (yellow glow at front right)
        pygame.draw.circle(surf, (255, 235, 100), (self.width - 4, 6), 3)
        pygame.draw.circle(surf, (255, 235, 100), (self.width - 4, self.height - 6), 3)

        # Direction hood stripe
        pygame.draw.line(surf, (255, 255, 255), (20, self.height // 2), (self.width - 6, self.height // 2), 2)

        return surf

    def update(self, target_angle, target_speed_ratio, state, bounds_w=800, bounds_h=600):
        self.physics.update(target_angle, target_speed_ratio, state, bounds_w, bounds_h, car_radius=self.width // 2)

    def draw(self, surface):
        """
        Rotates car surface to physics.heading_angle and blits to screen.
        Note: Pygame rotates counter-clockwise; 0° points right.
        """
        rotated_surf = pygame.transform.rotate(self.base_surface, self.physics.heading_angle)
        rect = rotated_surf.get_rect(center=(int(self.physics.x), int(self.physics.y)))
        surface.blit(rotated_surf, rect.topleft)

        # Draw trajectory indicator arrow line
        rad = math.radians(self.physics.heading_angle)
        end_x = self.physics.x + 30 * math.cos(rad)
        end_y = self.physics.y - 30 * math.sin(rad)
        pygame.draw.line(surface, (0, 255, 200), (int(self.physics.x), int(self.physics.y)), (int(end_x), int(end_y)), 2)
        pygame.draw.circle(surface, (0, 255, 200), (int(end_x), int(end_y)), 3)
