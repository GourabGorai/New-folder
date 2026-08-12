import pygame
import cv2
import numpy as np
import math
import time
from car import Car

class CarSimulator:
    def __init__(self, width=1024, height=720):
        pygame.init()
        pygame.font.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Gesture Controlled Car Simulator (ML + CV + Pygame)")

        self.clock = pygame.time.Clock()
        self.fps = 0

        # Create car object centered on 2D plane
        self.car = Car(x=width // 2, y=height // 2 + 50)

        # Control Mode ('GESTURE' or 'KEYBOARD')
        self.control_mode = 'GESTURE'

        # Fonts
        self.title_font = pygame.font.SysFont("Consolas", 20, bold=True)
        self.hud_font = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.val_font = pygame.font.SysFont("Segoe UI", 15)

    def draw_track_background(self):
        """Draws a dark futuristic race track grid & boundaries."""
        self.screen.fill((20, 24, 32))  # Dark sleek asphalt bg

        # Draw grid pattern
        grid_size = 50
        grid_color = (30, 36, 48)
        for x in range(0, self.width, grid_size):
            pygame.draw.line(self.screen, grid_color, (x, 100), (x, self.height))
        for y in range(100, self.height, grid_size):
            pygame.draw.line(self.screen, grid_color, (0, y), (self.width, y))

        # Track Outer Boundary Wall (Red/White curb pattern)
        margin = 15
        top_y = 110
        rect = pygame.Rect(margin, top_y, self.width - 2 * margin, self.height - top_y - margin)
        pygame.draw.rect(self.screen, (220, 50, 50), rect, width=4)

        # Center Start/Finish crosshair mark
        cx, cy = self.width // 2, (self.height + 100) // 2
        pygame.draw.circle(self.screen, (45, 55, 75), (cx, cy), 80, width=2)
        pygame.draw.line(self.screen, (45, 55, 75), (cx - 90, cy), (cx + 90, cy), 1)
        pygame.draw.line(self.screen, (45, 55, 75), (cx, cy - 90), (cx, cy + 90), 1)

    def draw_hud(self, gesture_data, camera_frame=None):
        """Draws top dashboard HUD, telemetry, steering dial, and picture-in-picture camera feed."""
        # Top HUD Banner container
        hud_bar = pygame.Rect(0, 0, self.width, 100)
        pygame.draw.rect(self.screen, (12, 16, 24), hud_bar)
        pygame.draw.line(self.screen, (0, 200, 255), (0, 99), (self.width, 99), 2)

        # Title
        title_txt = self.title_font.render("GESTURE CONTROLLED CAR SIMULATOR", True, (0, 255, 200))
        self.screen.blit(title_txt, (20, 12))

        # Mode Badge & Toggle Instructions
        active_mode_str = gesture_data.get('mode', 'MEDIAPIPE')
        mode_color = (0, 255, 150) if self.control_mode == 'GESTURE' else (255, 180, 0)
        mode_txt = self.hud_font.render(f"MODE: {self.control_mode} [{active_mode_str}]", True, mode_color)
        self.screen.blit(mode_txt, (20, 38))

        reset_txt = self.val_font.render("Keys: 'K'=Keyboard | 'M'=Model | 'R'=Reset | 'ESC'=Quit", True, (150, 165, 185))
        self.screen.blit(reset_txt, (20, 64))

        # Telemetry Stats Panel (x: 420 to 650)
        state_str = gesture_data.get('state', 'STOP')
        if self.control_mode == 'KEYBOARD':
            state_str = 'KEYBOARD'
            state_color = (0, 220, 255)
        elif state_str == 'CONTROL':
            state_color = (50, 230, 90)
        elif state_str == 'STOP':
            state_color = (255, 60, 60)
        else:
            state_color = (160, 160, 160)

        # State Pill Badge
        badge_rect = pygame.Rect(440, 15, 110, 28)
        pygame.draw.rect(self.screen, state_color, badge_rect, border_radius=14)
        state_txt = self.hud_font.render(state_str, True, (10, 10, 10))
        st_r = state_txt.get_rect(center=badge_rect.center)
        self.screen.blit(state_txt, st_r)

        # Angle & Speed text
        angle_deg = gesture_data.get('angle', 90.0)
        speed_ratio = gesture_data.get('speed', 0.0)
        car_speed = self.car.physics.speed

        angle_lbl = self.val_font.render(f"Angle: {angle_deg:.1f}°", True, (240, 245, 255))
        self.screen.blit(angle_lbl, (440, 48))

        speed_pct = int((car_speed / self.car.physics.max_speed) * 100)
        speed_lbl = self.val_font.render(f"Speed: {speed_pct}% ({car_speed:.1f} px/f)", True, (240, 245, 255))
        self.screen.blit(speed_lbl, (440, 70))

        # Speed Progress Bar
        bar_bg = pygame.Rect(590, 72, 100, 12)
        bar_fg = pygame.Rect(590, 72, int(speed_pct), 12)
        pygame.draw.rect(self.screen, (40, 50, 70), bar_bg, border_radius=4)
        pygame.draw.rect(self.screen, (0, 220, 130), bar_fg, border_radius=4)

        # Steering Wheel Compass Gauge (x: 720, y: 50)
        dial_cx, dial_cy = 740, 50
        pygame.draw.circle(self.screen, (35, 45, 60), (dial_cx, dial_cy), 36, width=3)
        pygame.draw.circle(self.screen, (0, 200, 255), (dial_cx, dial_cy), 4)

        # Steering Target Pointer (Red) & Car Heading Pointer (Green)
        rad_target = math.radians(angle_deg)
        tx = dial_cx + 30 * math.cos(rad_target)
        ty = dial_cy - 30 * math.sin(rad_target)
        pygame.draw.line(self.screen, (255, 90, 90), (dial_cx, dial_cy), (int(tx), int(ty)), 3)

        rad_car = math.radians(self.car.physics.heading_angle)
        cx_line = dial_cx + 26 * math.cos(rad_car)
        cy_line = dial_cy - 26 * math.sin(rad_car)
        pygame.draw.line(self.screen, (50, 255, 120), (dial_cx, dial_cy), (int(cx_line), int(cy_line)), 2)

        dial_lbl = self.val_font.render("Steering Compass", True, (170, 185, 205))
        self.screen.blit(dial_lbl, (700, 80))

        # FPS Display
        fps_lbl = self.val_font.render(f"FPS: {int(self.fps)}", True, (255, 255, 255))
        self.screen.blit(fps_lbl, (self.width - 190, 10))

        # Picture-in-Picture Camera Feed Overlay (Top Right: x=width-170, y=30, w=150, h=100)
        if camera_frame is not None:
            try:
                # Resize OpenCV frame for PIP overlay
                pip_frame = cv2.resize(camera_frame, (160, 110))
                pip_rgb = cv2.cvtColor(pip_frame, cv2.COLOR_BGR2RGB)
                # Transpose for Pygame image format (width, height, channels)
                pip_surface = pygame.surfarray.make_surface(pip_rgb.swapaxes(0, 1))
                
                pip_rect = pygame.Rect(self.width - 170, 30, 160, 110)
                self.screen.blit(pip_surface, pip_rect.topleft)
                pygame.draw.rect(self.screen, (0, 200, 255), pip_rect, width=2)
            except Exception as e:
                pass

    def reset_car(self):
        self.car.physics.x = self.width // 2
        self.car.physics.y = (self.height + 100) // 2
        self.car.physics.speed = 0.0
        self.car.physics.heading_angle = 90.0

    def render_frame(self, gesture_data, camera_frame=None):
        self.draw_track_background()
        self.car.draw(self.screen)
        self.draw_hud(gesture_data, camera_frame)
        
        pygame.display.flip()
        self.fps = self.clock.tick(60)

    def close(self):
        pygame.quit()
