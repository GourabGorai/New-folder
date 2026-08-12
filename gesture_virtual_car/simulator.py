import pygame
import cv2
import numpy as np
import math
import time
from car import Car
from iot_controller import IoTController

class CarSimulator:
    def __init__(self, width=1024, height=720):
        pygame.init()
        pygame.font.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Realistic IoT Gesture Controlled Car Simulator (ESP32/Arduino Ready)")

        self.clock = pygame.time.Clock()
        self.fps = 0

        # Create car object centered on 2D plane
        self.car = Car(x=width // 2, y=height // 2 + 50)
        self.iot = IoTController() # Hardware Controller interface

        # Control Mode ('GESTURE' or 'KEYBOARD')
        self.control_mode = 'GESTURE'
        self.hand_drive_mode = 'ALL_HANDS_FORWARD'

        # Fonts
        self.title_font = pygame.font.SysFont("Consolas", 18, bold=True)
        self.hud_font = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.val_font = pygame.font.SysFont("Segoe UI", 14)
        self.mon_font = pygame.font.SysFont("Consolas", 12)

    def draw_track_background(self):
        """Draws dark asphalt background with realistic lane lines and curb boundaries."""
        self.screen.fill((18, 22, 30))  # Dark asphalt bg

        # Grid / Track pavement markings
        grid_size = 50
        grid_color = (28, 34, 46)
        for x in range(0, self.width, grid_size):
            pygame.draw.line(self.screen, grid_color, (x, 110), (x, self.height))
        for y in range(110, self.height, grid_size):
            pygame.draw.line(self.screen, grid_color, (0, y), (self.width, y))

        # Track Outer Boundary Curb (Red/White curb pattern)
        margin = 15
        top_y = 115
        rect = pygame.Rect(margin, top_y, self.width - 2 * margin, self.height - top_y - margin)
        pygame.draw.rect(self.screen, (220, 50, 50), rect, width=4)

        # Center Start/Finish crosshair mark
        cx, cy = self.width // 2, (self.height + 115) // 2
        pygame.draw.circle(self.screen, (40, 50, 70), (cx, cy), 80, width=2)
        pygame.draw.line(self.screen, (40, 50, 70), (cx - 90, cy), (cx + 90, cy), 1)
        pygame.draw.line(self.screen, (40, 50, 70), (cx, cy - 90), (cx, cy + 90), 1)

    def draw_hud(self, gesture_data, camera_frame=None):
        """Draws top dashboard HUD, IoT motor PWM signals, serial telemetry log, and steering dial."""
        # Top HUD Banner container
        hud_bar = pygame.Rect(0, 0, self.width, 110)
        pygame.draw.rect(self.screen, (10, 14, 20), hud_bar)
        pygame.draw.line(self.screen, (0, 200, 255), (0, 109), (self.width, 109), 2)

        # Title
        title_txt = self.title_font.render("IOT GESTURE CAR SIMULATOR", True, (0, 255, 200))
        self.screen.blit(title_txt, (15, 8))

        # Active Mode & Keys Instruction
        active_mode_str = gesture_data.get('mode', 'MEDIAPIPE')
        mode_color = (0, 255, 150) if self.control_mode == 'GESTURE' else (255, 180, 0)
        
        hand_drive_mode_str = gesture_data.get('hand_drive_mode', self.hand_drive_mode)
        hand_mode_desc = "LEFT=FWD/RIGHT=REV" if hand_drive_mode_str == 'LEFT_FORWARD_RIGHT_REVERSE' else "ALL HANDS FWD"

        mode_txt = self.hud_font.render(f"MODE: {self.control_mode} [{active_mode_str}] | OPT: {hand_mode_desc}", True, mode_color)
        self.screen.blit(mode_txt, (15, 32))

        reset_txt = self.val_font.render("Keys: 'K'=Keyb | 'M'=Model | 'H'=Hand Option | 'R'=Reset | 'ESC'=Quit", True, (150, 165, 185))
        self.screen.blit(reset_txt, (15, 54))

        # IoT Hardware Status Pill & Hand Label
        hand_label_str = gesture_data.get('hand_label', 'NONE')
        iot_status = "PHYSICAL SERIAL: ON" if self.iot.is_connected else "ESP32 MOCK STREAM: READY"
        iot_color = (0, 255, 120) if self.iot.is_connected else (0, 200, 255)
        iot_txt = self.val_font.render(f"IoT: {iot_status} | HAND: {hand_label_str.upper()}", True, iot_color)
        self.screen.blit(iot_txt, (15, 76))

        # Telemetry Stats Panel (x: 320 to 520)
        state_str = gesture_data.get('state', 'STOP')
        if self.control_mode == 'KEYBOARD':
            state_color = (0, 220, 255)
        elif state_str == 'CONTROL':
            state_color = (50, 230, 90)
        elif state_str == 'REVERSE':
            state_color = (255, 140, 0)
        elif state_str == 'STOP':
            state_color = (255, 60, 60)
        else:
            state_color = (160, 160, 160)

        # State Pill Badge
        badge_rect = pygame.Rect(320, 12, 110, 26)
        pygame.draw.rect(self.screen, state_color, badge_rect, border_radius=13)
        state_txt = self.hud_font.render(state_str, True, (10, 10, 10))
        st_r = state_txt.get_rect(center=badge_rect.center)
        self.screen.blit(state_txt, st_r)

        # Steering Wheel Angle & Speed in km/h
        steer_angle_deg = self.car.physics.steering_delta
        speed_kmh = self.car.physics.speed_kmh

        angle_lbl = self.val_font.render(f"Steer Delta: {steer_angle_deg:+.1f}°", True, (240, 245, 255))
        self.screen.blit(angle_lbl, (320, 44))

        speed_lbl = self.val_font.render(f"Speed: {speed_kmh:.1f} km/h", True, (240, 245, 255))
        self.screen.blit(speed_lbl, (320, 66))

        # Send IoT Telemetry & Calculate Left/Right Motor PWM
        telemetry_pkt = self.iot.send_telemetry(speed_kmh, steer_angle_deg, state_str)
        pwm_l, pwm_r = telemetry_pkt['pwml'], telemetry_pkt['pwmr']

        # Differential Motor Speed Gauges (PWML and PWMR bars: x: 480 to 650)
        self._draw_motor_gauge("L-MOTOR", pwm_l, 460, 12)
        self._draw_motor_gauge("R-MOTOR", pwm_r, 460, 52)

        # Steering Wheel Compass Gauge (x: 620, y: 55)
        dial_cx, dial_cy = 615, 55
        pygame.draw.circle(self.screen, (35, 45, 60), (dial_cx, dial_cy), 36, width=3)
        pygame.draw.circle(self.screen, (0, 200, 255), (dial_cx, dial_cy), 4)

        # Target Pointer (Red) & Car Heading Pointer (Green)
        target_dir = gesture_data.get('angle', 90.0)
        rad_target = math.radians(target_dir)
        tx = dial_cx + 30 * math.cos(rad_target)
        ty = dial_cy - 30 * math.sin(rad_target)
        pygame.draw.line(self.screen, (255, 90, 90), (dial_cx, dial_cy), (int(tx), int(ty)), 3)

        rad_car = math.radians(self.car.physics.heading_psi)
        cx_line = dial_cx + 26 * math.cos(rad_car)
        cy_line = dial_cy - 26 * math.sin(rad_car)
        pygame.draw.line(self.screen, (50, 255, 120), (dial_cx, dial_cy), (int(cx_line), int(cy_line)), 2)

        # Live IoT Serial Monitor Box (Top Right: x=670, y=10, w=180, h=90)
        mon_rect = pygame.Rect(670, 10, 180, 90)
        pygame.draw.rect(self.screen, (15, 20, 30), mon_rect)
        pygame.draw.rect(self.screen, (0, 180, 220), mon_rect, width=1)
        
        mon_title = self.mon_font.render("ESP32 TELEMETRY MONITOR", True, (0, 200, 255))
        self.screen.blit(mon_title, (675, 14))

        y_offset = 32
        for pkt_str in self.iot.recent_packets[-4:]:
            # Display truncated packet JSON
            short_pkt = pkt_str.replace(" ", "")[:24]
            pkt_txt = self.mon_font.render(short_pkt, True, (160, 220, 180))
            self.screen.blit(pkt_txt, (675, y_offset))
            y_offset += 14

        # Picture-in-Picture Camera Feed Overlay (Top Far Right: x=860, y=10, w=150, h=90)
        if camera_frame is not None:
            try:
                pip_frame = cv2.resize(camera_frame, (150, 90))
                pip_rgb = cv2.cvtColor(pip_frame, cv2.COLOR_BGR2RGB)
                pip_surface = pygame.surfarray.make_surface(pip_rgb.swapaxes(0, 1))
                
                pip_rect = pygame.Rect(860, 10, 150, 90)
                self.screen.blit(pip_surface, pip_rect.topleft)
                pygame.draw.rect(self.screen, (0, 200, 255), pip_rect, width=2)
            except Exception as e:
                pass

        # FPS
        fps_lbl = self.mon_font.render(f"FPS: {int(self.fps)}", True, (200, 200, 200))
        self.screen.blit(fps_lbl, (self.width - 60, 95))

    def _draw_motor_gauge(self, label, pwm_value, x, y):
        """Draws a motor PWM speed gauge (-255 to +255)."""
        lbl = self.val_font.render(f"{label}: {pwm_value:+4d} PWM", True, (220, 230, 245))
        self.screen.blit(lbl, (x, y))

        bg_rect = pygame.Rect(x, y + 20, 120, 10)
        pygame.draw.rect(self.screen, (35, 45, 60), bg_rect, border_radius=3)

        # Center indicator
        center_x = x + 60
        pygame.draw.line(self.screen, (200, 200, 200), (center_x, y + 18), (center_x, y + 32), 1)

        fill_w = int((pwm_value / 255.0) * 60)
        if fill_w > 0:
            fg_rect = pygame.Rect(center_x, y + 20, fill_w, 10)
            color = (50, 230, 120)
        else:
            fg_rect = pygame.Rect(center_x + fill_w, y + 20, -fill_w, 10)
            color = (255, 120, 50)
            
        if abs(fill_w) > 0:
            pygame.draw.rect(self.screen, color, fg_rect, border_radius=2)

    def reset_car(self):
        self.car.physics.x = self.width // 2
        self.car.physics.y = (self.height + 115) // 2
        self.car.physics.speed_kmh = 0.0
        self.car.physics.heading_psi = 90.0
        self.car.physics.steering_delta = 0.0

    def render_frame(self, gesture_data, camera_frame=None):
        self.draw_track_background()
        
        is_braking = (gesture_data.get('state') == 'STOP')
        is_reversing = gesture_data.get('is_reverse', False) or (self.car.physics.speed_kmh < -0.1)
        self.car.draw(self.screen, is_braking=is_braking, is_reversing=is_reversing)
        
        self.draw_hud(gesture_data, camera_frame)
        
        pygame.display.flip()
        self.fps = self.clock.tick(60)

    def close(self):
        pygame.quit()
