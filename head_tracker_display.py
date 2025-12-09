#!/usr/bin/env python3
"""
Head Tracking Display Application
Visualizes head orientation using pygame with a 3D head model
"""

import pygame
import math
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple

# Import our sensor modules (with fallback for development)
try:
    from sensor_fusion import HeadTracker, Orientation
    SENSOR_AVAILABLE = True
except (ImportError, OSError):
    SENSOR_AVAILABLE = False
    print("⚠ Sensor not available - running in simulation mode")

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """Application configuration"""
    # Display settings
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    FPS: int = 60
    
    # Colors - Cyberpunk/Synthwave theme
    BG_COLOR: Tuple[int, int, int] = (15, 10, 30)
    BG_GRADIENT_TOP: Tuple[int, int, int] = (20, 10, 45)
    BG_GRADIENT_BOTTOM: Tuple[int, int, int] = (10, 5, 25)
    
    GRID_COLOR: Tuple[int, int, int] = (40, 30, 70)
    GRID_HIGHLIGHT: Tuple[int, int, int] = (100, 50, 150)
    
    HEAD_COLOR: Tuple[int, int, int] = (0, 255, 200)
    HEAD_OUTLINE: Tuple[int, int, int] = (0, 180, 140)
    EYE_COLOR: Tuple[int, int, int] = (255, 50, 150)
    NOSE_COLOR: Tuple[int, int, int] = (200, 100, 255)
    
    ACCENT_PINK: Tuple[int, int, int] = (255, 50, 150)
    ACCENT_CYAN: Tuple[int, int, int] = (0, 255, 255)
    ACCENT_PURPLE: Tuple[int, int, int] = (180, 80, 255)
    
    TEXT_COLOR: Tuple[int, int, int] = (220, 220, 240)
    TEXT_DIM: Tuple[int, int, int] = (120, 100, 160)
    
    # Head model settings
    HEAD_SIZE: int = 200
    
    # Sensitivity multipliers
    PITCH_SENSITIVITY: float = 1.0
    ROLL_SENSITIVITY: float = 1.0
    YAW_SENSITIVITY: float = 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 3D Math Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def rotate_point_3d(point: Tuple[float, float, float], 
                    pitch: float, roll: float, yaw: float) -> Tuple[float, float, float]:
    """
    Rotate a 3D point around all three axes
    
    Args:
        point: (x, y, z) coordinates
        pitch: Rotation around X-axis (degrees)
        roll: Rotation around Y-axis (degrees)  
        yaw: Rotation around Z-axis (degrees)
        
    Returns:
        Rotated (x, y, z) coordinates
    """
    x, y, z = point
    
    # Convert to radians
    pitch_rad = math.radians(pitch)
    roll_rad = math.radians(roll)
    yaw_rad = math.radians(yaw)
    
    # Rotation around X-axis (pitch)
    y1 = y * math.cos(pitch_rad) - z * math.sin(pitch_rad)
    z1 = y * math.sin(pitch_rad) + z * math.cos(pitch_rad)
    x1 = x
    
    # Rotation around Y-axis (roll)
    x2 = x1 * math.cos(roll_rad) + z1 * math.sin(roll_rad)
    z2 = -x1 * math.sin(roll_rad) + z1 * math.cos(roll_rad)
    y2 = y1
    
    # Rotation around Z-axis (yaw)
    x3 = x2 * math.cos(yaw_rad) - y2 * math.sin(yaw_rad)
    y3 = x2 * math.sin(yaw_rad) + y2 * math.cos(yaw_rad)
    z3 = z2
    
    return (x3, y3, z3)


def project_3d_to_2d(point: Tuple[float, float, float], 
                     center: Tuple[int, int],
                     scale: float = 1.0,
                     perspective: float = 500) -> Tuple[int, int]:
    """
    Project 3D point to 2D screen coordinates with perspective
    
    Args:
        point: 3D (x, y, z) coordinates
        center: 2D screen center (x, y)
        scale: Scale factor
        perspective: Perspective depth factor
        
    Returns:
        2D screen coordinates (x, y)
    """
    x, y, z = point
    
    # Apply perspective projection
    factor = perspective / (perspective + z)
    
    screen_x = int(center[0] + x * scale * factor)
    screen_y = int(center[1] - y * scale * factor)  # Flip Y for screen coords
    
    return (screen_x, screen_y)


# ═══════════════════════════════════════════════════════════════════════════════
# Head Model
# ═══════════════════════════════════════════════════════════════════════════════

class HeadModel:
    """3D wireframe head model for visualization"""
    
    def __init__(self, size: int = 200):
        self.size = size
        self.vertices = self._create_vertices()
        self.faces = self._create_faces()
        self.features = self._create_features()
        
    def _create_vertices(self) -> List[Tuple[float, float, float]]:
        """Create head outline vertices (oval shape)"""
        vertices = []
        s = self.size
        
        # Head outline - ellipsoid points
        for i in range(12):
            angle = i * 30 * math.pi / 180
            x = s * 0.7 * math.sin(angle)
            y = s * 1.0 * math.cos(angle)
            vertices.append((x, y, 0))
        
        return vertices
    
    def _create_faces(self) -> List[List[int]]:
        """Create face connections (line indices)"""
        faces = []
        n = len(self.vertices)
        
        # Connect head outline
        for i in range(n):
            faces.append([i, (i + 1) % n])
            
        return faces
    
    def _create_features(self) -> dict:
        """Create facial features with 3D depth"""
        s = self.size
        
        return {
            # Eyes (circles at z=30 for depth)
            'left_eye': {'center': (-s * 0.25, s * 0.25, 50), 'radius': s * 0.12},
            'right_eye': {'center': (s * 0.25, s * 0.25, 50), 'radius': s * 0.12},
            
            # Pupils (smaller, more depth)
            'left_pupil': {'center': (-s * 0.25, s * 0.25, 60), 'radius': s * 0.05},
            'right_pupil': {'center': (s * 0.25, s * 0.25, 60), 'radius': s * 0.05},
            
            # Nose (triangle pointing forward)
            'nose': [
                (0, s * 0.1, 70),      # Tip
                (-s * 0.08, s * 0.0, 30),  # Left base
                (s * 0.08, s * 0.0, 30)    # Right base
            ],
            
            # Mouth (curved line)
            'mouth': [
                (-s * 0.2, -s * 0.25, 40),
                (-s * 0.1, -s * 0.3, 50),
                (0, -s * 0.32, 55),
                (s * 0.1, -s * 0.3, 50),
                (s * 0.2, -s * 0.25, 40)
            ],
            
            # Ears
            'left_ear': [
                (-s * 0.68, s * 0.15, -10),
                (-s * 0.8, s * 0.25, -20),
                (-s * 0.82, s * 0.1, -20),
                (-s * 0.78, -s * 0.05, -15),
                (-s * 0.68, -s * 0.05, -10)
            ],
            'right_ear': [
                (s * 0.68, s * 0.15, -10),
                (s * 0.8, s * 0.25, -20),
                (s * 0.82, s * 0.1, -20),
                (s * 0.78, -s * 0.05, -15),
                (s * 0.68, -s * 0.05, -10)
            ]
        }
    
    def draw(self, screen: pygame.Surface, center: Tuple[int, int],
             pitch: float, roll: float, yaw: float, config: Config):
        """
        Draw the head model with rotation
        
        Args:
            screen: Pygame surface to draw on
            center: Center point for the head
            pitch, roll, yaw: Rotation angles in degrees
            config: Visual configuration
        """
        # Apply sensitivity
        pitch *= config.PITCH_SENSITIVITY
        roll *= config.ROLL_SENSITIVITY
        yaw *= config.YAW_SENSITIVITY
        
        # Draw head outline with glow effect
        rotated_vertices = []
        for v in self.vertices:
            rotated = rotate_point_3d(v, pitch, roll, yaw)
            screen_pos = project_3d_to_2d(rotated, center)
            rotated_vertices.append(screen_pos)
        
        # Draw outer glow
        if len(rotated_vertices) > 2:
            pygame.draw.polygon(screen, config.HEAD_OUTLINE, rotated_vertices, 4)
            pygame.draw.polygon(screen, config.HEAD_COLOR, rotated_vertices, 2)
        
        # Draw eyes
        for eye_name in ['left_eye', 'right_eye']:
            eye = self.features[eye_name]
            rotated = rotate_point_3d(eye['center'], pitch, roll, yaw)
            pos = project_3d_to_2d(rotated, center)
            
            # Eye visibility based on z-depth (hide if facing away)
            if rotated[2] > -50:
                # Glow effect
                pygame.draw.circle(screen, config.ACCENT_PINK, pos, int(eye['radius'] * 1.3), 2)
                pygame.draw.circle(screen, config.EYE_COLOR, pos, int(eye['radius']), 2)
        
        # Draw pupils
        for pupil_name in ['left_pupil', 'right_pupil']:
            pupil = self.features[pupil_name]
            rotated = rotate_point_3d(pupil['center'], pitch, roll, yaw)
            pos = project_3d_to_2d(rotated, center)
            
            if rotated[2] > -30:
                pygame.draw.circle(screen, config.EYE_COLOR, pos, int(pupil['radius']))
        
        # Draw nose
        nose_points = self.features['nose']
        rotated_nose = [rotate_point_3d(p, pitch, roll, yaw) for p in nose_points]
        screen_nose = [project_3d_to_2d(p, center) for p in rotated_nose]
        
        if rotated_nose[0][2] > -20:  # Only draw if facing forward
            pygame.draw.lines(screen, config.NOSE_COLOR, True, screen_nose, 2)
        
        # Draw mouth
        mouth_points = self.features['mouth']
        rotated_mouth = [rotate_point_3d(p, pitch, roll, yaw) for p in mouth_points]
        screen_mouth = [project_3d_to_2d(p, center) for p in rotated_mouth]
        
        if rotated_mouth[2][2] > -20:
            pygame.draw.lines(screen, config.ACCENT_PURPLE, False, screen_mouth, 2)
        
        # Draw ears
        for ear_name in ['left_ear', 'right_ear']:
            ear_points = self.features[ear_name]
            rotated_ear = [rotate_point_3d(p, pitch, roll, yaw) for p in ear_points]
            screen_ear = [project_3d_to_2d(p, center) for p in rotated_ear]
            pygame.draw.lines(screen, config.HEAD_OUTLINE, False, screen_ear, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# UI Components
# ═══════════════════════════════════════════════════════════════════════════════

class OrientationDisplay:
    """Displays orientation data as gauges and text"""
    
    def __init__(self, config: Config):
        self.config = config
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        
    def init_fonts(self):
        """Initialize fonts after pygame init"""
        pygame.font.init()
        
        # Try to use a nice monospace font
        font_names = ['JetBrains Mono', 'Fira Code', 'Source Code Pro', 'Consolas', 'monospace']
        font_path = None
        
        for name in font_names:
            try:
                font_path = pygame.font.match_font(name)
                if font_path:
                    break
            except:
                continue
        
        if font_path:
            self.font_large = pygame.font.Font(font_path, 36)
            self.font_medium = pygame.font.Font(font_path, 24)
            self.font_small = pygame.font.Font(font_path, 16)
        else:
            self.font_large = pygame.font.Font(None, 42)
            self.font_medium = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 20)
    
    def draw_gauge(self, screen: pygame.Surface, center: Tuple[int, int],
                   value: float, max_value: float, label: str, 
                   color: Tuple[int, int, int], radius: int = 80):
        """Draw a circular gauge"""
        # Background circle
        pygame.draw.circle(screen, self.config.GRID_COLOR, center, radius, 2)
        
        # Value arc
        angle = (value / max_value) * 180 - 90  # Map to -90 to 90 degrees
        angle_rad = math.radians(angle)
        
        # Draw indicator line
        end_x = center[0] + int((radius - 10) * math.sin(angle_rad))
        end_y = center[1] - int((radius - 10) * math.cos(angle_rad))
        
        pygame.draw.line(screen, color, center, (end_x, end_y), 3)
        pygame.draw.circle(screen, color, (end_x, end_y), 6)
        
        # Draw tick marks
        for tick in range(-90, 91, 30):
            tick_rad = math.radians(tick)
            inner = (center[0] + int((radius - 5) * math.sin(tick_rad)),
                    center[1] - int((radius - 5) * math.cos(tick_rad)))
            outer = (center[0] + int(radius * math.sin(tick_rad)),
                    center[1] - int(radius * math.cos(tick_rad)))
            pygame.draw.line(screen, self.config.GRID_HIGHLIGHT, inner, outer, 2)
        
        # Label
        label_surf = self.font_small.render(label, True, self.config.TEXT_DIM)
        label_rect = label_surf.get_rect(center=(center[0], center[1] + radius + 20))
        screen.blit(label_surf, label_rect)
        
        # Value text
        value_text = f"{value:+.1f}°"
        value_surf = self.font_medium.render(value_text, True, color)
        value_rect = value_surf.get_rect(center=(center[0], center[1] + 25))
        screen.blit(value_surf, value_rect)
    
    def draw_orientation_panel(self, screen: pygame.Surface, 
                               orientation, x: int, y: int):
        """Draw full orientation info panel"""
        cfg = self.config
        
        # Panel background
        panel_rect = pygame.Rect(x, y, 350, 180)
        pygame.draw.rect(screen, (20, 15, 40), panel_rect, border_radius=10)
        pygame.draw.rect(screen, cfg.GRID_HIGHLIGHT, panel_rect, 2, border_radius=10)
        
        # Title
        title = self.font_medium.render("◆ ORIENTATION", True, cfg.ACCENT_CYAN)
        screen.blit(title, (x + 15, y + 15))
        
        # Data rows
        data = [
            ("PITCH", orientation.pitch, cfg.ACCENT_PINK, "↕"),
            ("ROLL", orientation.roll, cfg.ACCENT_CYAN, "↔"),
            ("YAW", orientation.yaw, cfg.ACCENT_PURPLE, "⟳")
        ]
        
        for i, (label, value, color, icon) in enumerate(data):
            row_y = y + 55 + i * 40
            
            # Icon and label
            icon_surf = self.font_medium.render(icon, True, color)
            screen.blit(icon_surf, (x + 20, row_y))
            
            label_surf = self.font_small.render(label, True, cfg.TEXT_DIM)
            screen.blit(label_surf, (x + 55, row_y + 4))
            
            # Value bar background
            bar_x = x + 130
            bar_width = 150
            pygame.draw.rect(screen, cfg.GRID_COLOR, 
                           (bar_x, row_y + 5, bar_width, 14), border_radius=3)
            
            # Value bar (normalized to -90 to +90)
            normalized = (value + 90) / 180  # 0 to 1
            normalized = max(0, min(1, normalized))
            fill_width = int(bar_width * normalized)
            
            if fill_width > 0:
                pygame.draw.rect(screen, color, 
                               (bar_x, row_y + 5, fill_width, 14), border_radius=3)
            
            # Value text
            value_text = f"{value:+6.1f}°"
            value_surf = self.font_small.render(value_text, True, cfg.TEXT_COLOR)
            screen.blit(value_surf, (x + 295, row_y + 3))


class GridBackground:
    """Animated perspective grid background"""
    
    def __init__(self, config: Config):
        self.config = config
        self.offset = 0
        
    def draw(self, screen: pygame.Surface, orientation):
        """Draw animated grid background"""
        cfg = self.config
        w, h = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        
        # Gradient background
        for y in range(h):
            factor = y / h
            r = int(cfg.BG_GRADIENT_TOP[0] * (1 - factor) + cfg.BG_GRADIENT_BOTTOM[0] * factor)
            g = int(cfg.BG_GRADIENT_TOP[1] * (1 - factor) + cfg.BG_GRADIENT_BOTTOM[1] * factor)
            b = int(cfg.BG_GRADIENT_TOP[2] * (1 - factor) + cfg.BG_GRADIENT_BOTTOM[2] * factor)
            pygame.draw.line(screen, (r, g, b), (0, y), (w, y))
        
        # Horizontal grid lines with perspective
        horizon_y = h // 2 - int(orientation.pitch * 2)
        
        for i in range(20):
            y_offset = 20 + i * 25
            y = horizon_y + y_offset
            
            if 0 < y < h:
                alpha = max(0, 255 - i * 12)
                color = (cfg.GRID_COLOR[0], cfg.GRID_COLOR[1], cfg.GRID_COLOR[2])
                pygame.draw.line(screen, color, (0, y), (w, y))
        
        # Vertical grid lines
        center_x = w // 2 + int(orientation.yaw * 3)
        for i in range(-10, 11):
            x = center_x + i * 80
            if 0 < x < w:
                pygame.draw.line(screen, cfg.GRID_COLOR, 
                               (x, horizon_y), (x, h))


# ═══════════════════════════════════════════════════════════════════════════════
# Simulation Mode (for development without sensor)
# ═══════════════════════════════════════════════════════════════════════════════

class SimulatedOrientation:
    """Simulates head orientation using mouse/keyboard input"""
    
    def __init__(self):
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.target_pitch = 0.0
        self.target_roll = 0.0
        self.target_yaw = 0.0
        self.smoothing = 0.1
        
    def update(self, mouse_pos: Tuple[int, int], 
               screen_size: Tuple[int, int]) -> 'SimulatedOrientation':
        """Update orientation based on mouse position"""
        cx, cy = screen_size[0] // 2, screen_size[1] // 2
        
        # Map mouse position to orientation
        self.target_yaw = (mouse_pos[0] - cx) / cx * 45  # ±45 degrees
        self.target_pitch = -(mouse_pos[1] - cy) / cy * 30  # ±30 degrees
        
        # Smooth interpolation
        self.pitch += (self.target_pitch - self.pitch) * self.smoothing
        self.roll += (self.target_roll - self.roll) * self.smoothing
        self.yaw += (self.target_yaw - self.yaw) * self.smoothing
        
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════════

class HeadTrackerApp:
    """Main application class"""
    
    def __init__(self, use_sensor: bool = True):
        self.config = Config()
        self.running = True
        self.use_sensor = use_sensor and SENSOR_AVAILABLE
        
        # Initialize pygame
        pygame.init()
        pygame.display.set_caption("🎮 Head Tracker - MPU6050")
        
        self.screen = pygame.display.set_mode(
            (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        
        # Initialize components
        self.head_model = HeadModel(self.config.HEAD_SIZE)
        self.orientation_display = OrientationDisplay(self.config)
        self.orientation_display.init_fonts()
        self.grid = GridBackground(self.config)
        
        # Sensor or simulation
        if self.use_sensor:
            print("🎯 Initializing head tracker with MPU6050 sensor...")
            self.tracker = HeadTracker(filter_type="complementary", alpha=0.96)
            self.tracker.calibrate(samples=200)
        else:
            print("🖱 Running in simulation mode (move mouse to control)")
            self.simulated = SimulatedOrientation()
        
        # Current orientation
        self.orientation = type('Orientation', (), {'pitch': 0, 'roll': 0, 'yaw': 0})()
        
    def handle_events(self) -> bool:
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_r:
                    # Reset orientation
                    if self.use_sensor:
                        self.tracker.reset()
                    else:
                        self.simulated = SimulatedOrientation()
                    print("✓ Orientation reset")
                elif event.key == pygame.K_c:
                    # Recalibrate
                    if self.use_sensor:
                        self.tracker.calibrate(samples=200)
        
        return True
    
    def update(self):
        """Update orientation data"""
        if self.use_sensor:
            self.orientation = self.tracker.get_orientation()
        else:
            mouse_pos = pygame.mouse.get_pos()
            screen_size = (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT)
            self.orientation = self.simulated.update(mouse_pos, screen_size)
    
    def draw(self):
        """Render the display"""
        cfg = self.config
        
        # Draw animated background
        self.grid.draw(self.screen, self.orientation)
        
        # Draw head model in center
        head_center = (cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
        self.head_model.draw(
            self.screen, head_center,
            self.orientation.pitch,
            self.orientation.roll, 
            self.orientation.yaw,
            cfg
        )
        
        # Draw orientation panel
        self.orientation_display.draw_orientation_panel(
            self.screen, self.orientation, 30, 30
        )
        
        # Draw gauges
        gauge_y = cfg.SCREEN_HEIGHT - 120
        self.orientation_display.draw_gauge(
            self.screen, (cfg.SCREEN_WIDTH - 280, gauge_y),
            self.orientation.pitch, 90, "PITCH", cfg.ACCENT_PINK, 70
        )
        self.orientation_display.draw_gauge(
            self.screen, (cfg.SCREEN_WIDTH - 150, gauge_y),
            self.orientation.roll, 90, "ROLL", cfg.ACCENT_CYAN, 70
        )
        
        # Draw help text
        help_text = "ESC: Quit | R: Reset | C: Calibrate" if self.use_sensor else "ESC: Quit | R: Reset | Move mouse to control"
        help_surf = self.orientation_display.font_small.render(help_text, True, cfg.TEXT_DIM)
        self.screen.blit(help_surf, (30, cfg.SCREEN_HEIGHT - 30))
        
        # Mode indicator
        mode = "🔴 LIVE" if self.use_sensor else "🔵 SIMULATION"
        mode_surf = self.orientation_display.font_medium.render(mode, True, 
                    cfg.ACCENT_PINK if self.use_sensor else cfg.ACCENT_CYAN)
        self.screen.blit(mode_surf, (cfg.SCREEN_WIDTH - 180, 30))
        
        # FPS counter
        fps = self.clock.get_fps()
        fps_surf = self.orientation_display.font_small.render(
            f"FPS: {fps:.0f}", True, cfg.TEXT_DIM
        )
        self.screen.blit(fps_surf, (cfg.SCREEN_WIDTH - 100, 60))
        
        pygame.display.flip()
    
    def run(self):
        """Main application loop"""
        print("\n" + "═" * 60)
        print("  HEAD TRACKER DISPLAY")
        print("═" * 60)
        print(f"  Mode: {'Sensor (MPU6050)' if self.use_sensor else 'Simulation'}")
        print("  Controls:")
        print("    ESC - Quit")
        print("    R   - Reset orientation")
        print("    C   - Recalibrate sensor")
        print("═" * 60 + "\n")
        
        try:
            while self.running:
                self.running = self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(self.config.FPS)
                
        except KeyboardInterrupt:
            print("\n⏹ Stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.use_sensor and hasattr(self, 'tracker'):
            self.tracker.close()
        pygame.quit()
        print("✓ Application closed")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Head Tracking Display")
    parser.add_argument('--sim', action='store_true', 
                       help='Force simulation mode (use mouse instead of sensor)')
    parser.add_argument('--width', type=int, default=1280,
                       help='Screen width (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                       help='Screen height (default: 720)')
    
    args = parser.parse_args()
    
    # Create and run application
    app = HeadTrackerApp(use_sensor=not args.sim)
    
    if args.width != 1280 or args.height != 720:
        app.config.SCREEN_WIDTH = args.width
        app.config.SCREEN_HEIGHT = args.height
        app.screen = pygame.display.set_mode((args.width, args.height))
    
    app.run()


if __name__ == "__main__":
    main()

