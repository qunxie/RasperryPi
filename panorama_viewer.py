#!/usr/bin/env python3
"""
360° Panorama/Video Viewer with Head Tracking
Maps MPU6050 orientation to viewport position in panoramic content

Supports:
- 360° equirectangular images (JPG, PNG)
- 360° equirectangular videos (MP4, AVI)
- Standard wide-angle content with limited panning
"""

import pygame
import math
import sys
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# Try to import OpenCV for video support
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠ OpenCV not installed. Video playback disabled.")
    print("  Install with: pip install opencv-python")

# Try to import sensor modules
try:
    from sensor_fusion import HeadTracker
    SENSOR_AVAILABLE = True
except (ImportError, OSError):
    SENSOR_AVAILABLE = False
    print("⚠ Sensor not available - using mouse control")


@dataclass
class ViewerConfig:
    """Viewer configuration"""
    # Display settings
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    FPS: int = 30
    
    # Field of view (degrees)
    FOV_H: float = 90.0   # Horizontal FOV
    FOV_V: float = 60.0   # Vertical FOV
    
    # Sensitivity
    YAW_SENSITIVITY: float = 2.0
    PITCH_SENSITIVITY: float = 1.5
    
    # Colors
    BG_COLOR: Tuple[int, int, int] = (10, 10, 20)
    TEXT_COLOR: Tuple[int, int, int] = (200, 200, 220)
    ACCENT_COLOR: Tuple[int, int, int] = (0, 200, 255)


class PanoramaViewer:
    """
    360° Panorama viewer with head tracking support
    
    Supports equirectangular projection images/videos where:
    - Full width = 360° horizontal
    - Full height = 180° vertical
    """
    
    def __init__(self, media_path: str, use_sensor: bool = True):
        self.config = ViewerConfig()
        self.media_path = media_path
        self.use_sensor = use_sensor and SENSOR_AVAILABLE
        
        # View angles (degrees)
        self.yaw = 0.0      # Horizontal look angle (-180 to 180)
        self.pitch = 0.0    # Vertical look angle (-90 to 90)
        
        # Mouse control fallback
        self.mouse_yaw = 0.0
        self.mouse_pitch = 0.0
        
        # Initialize pygame
        pygame.init()
        pygame.display.set_caption("🎬 360° Panorama Viewer - Head Tracking")
        
        self.screen = pygame.display.set_mode(
            (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        
        # Load media
        self.is_video = False
        self.video_capture = None
        self.panorama_surface = None
        self.current_frame = None
        
        self._load_media(media_path)
        
        # Initialize head tracker
        if self.use_sensor:
            print("🎯 Initializing head tracker...")
            self.tracker = HeadTracker(filter_type="complementary", alpha=0.96)
            self.tracker.calibrate(samples=200)
        
        self.running = True
    
    def _load_media(self, path: str):
        """Load image or video file"""
        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            self._create_demo_panorama()
            return
        
        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            if CV2_AVAILABLE:
                self._load_video(path)
            else:
                print("❌ Video playback requires OpenCV")
                self._create_demo_panorama()
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            self._load_image(path)
        else:
            print(f"❌ Unsupported format: {ext}")
            self._create_demo_panorama()
    
    def _load_video(self, path: str):
        """Load video file with OpenCV"""
        self.video_capture = cv2.VideoCapture(path)
        
        if not self.video_capture.isOpened():
            print(f"❌ Could not open video: {path}")
            self._create_demo_panorama()
            return
        
        self.is_video = True
        
        # Get video properties
        self.video_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        
        print(f"✓ Loaded video: {self.video_width}x{self.video_height} @ {self.video_fps:.1f} FPS")
        
        # Read first frame
        self._read_video_frame()
    
    def _load_image(self, path: str):
        """Load image file"""
        try:
            self.panorama_surface = pygame.image.load(path).convert()
            self.pano_width = self.panorama_surface.get_width()
            self.pano_height = self.panorama_surface.get_height()
            print(f"✓ Loaded image: {self.pano_width}x{self.pano_height}")
        except pygame.error as e:
            print(f"❌ Could not load image: {e}")
            self._create_demo_panorama()
    
    def _read_video_frame(self):
        """Read next video frame"""
        if self.video_capture is None:
            return
        
        ret, frame = self.video_capture.read()
        
        if not ret:
            # Loop video
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_capture.read()
        
        if ret:
            # Convert BGR to RGB and create pygame surface
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_frame = frame_rgb
            self.panorama_surface = pygame.surfarray.make_surface(
                frame_rgb.swapaxes(0, 1)
            )
            self.pano_width = self.panorama_surface.get_width()
            self.pano_height = self.panorama_surface.get_height()
    
    def _create_demo_panorama(self):
        """Create a demo panorama pattern for testing"""
        print("📐 Creating demo panorama pattern...")
        
        width, height = 4096, 2048  # 2:1 ratio for equirectangular
        
        self.panorama_surface = pygame.Surface((width, height))
        
        # Create gradient background
        for y in range(height):
            # Sky gradient (top half)
            if y < height // 2:
                factor = y / (height // 2)
                r = int(20 + 40 * factor)
                g = int(20 + 80 * factor)
                b = int(80 + 100 * (1 - factor))
            # Ground gradient (bottom half)
            else:
                factor = (y - height // 2) / (height // 2)
                r = int(40 + 30 * factor)
                g = int(60 + 40 * (1 - factor))
                b = int(30 + 20 * (1 - factor))
            
            pygame.draw.line(self.panorama_surface, (r, g, b), (0, y), (width, y))
        
        # Draw direction markers
        font_large = pygame.font.Font(None, 120)
        font_small = pygame.font.Font(None, 48)
        
        directions = [
            ("NORTH", 0, (255, 100, 100)),
            ("EAST", 90, (100, 255, 100)),
            ("SOUTH", 180, (100, 100, 255)),
            ("WEST", 270, (255, 255, 100)),
        ]
        
        for name, angle, color in directions:
            x = int((angle / 360.0) * width)
            y = height // 2
            
            # Draw vertical line
            pygame.draw.line(self.panorama_surface, color, (x, 0), (x, height), 3)
            
            # Draw direction label
            text = font_large.render(name, True, color)
            text_rect = text.get_rect(center=(x, y))
            self.panorama_surface.blit(text, text_rect)
            
            # Draw angle
            angle_text = font_small.render(f"{angle}°", True, color)
            angle_rect = angle_text.get_rect(center=(x, y + 80))
            self.panorama_surface.blit(angle_text, angle_rect)
        
        # Draw grid lines
        for i in range(0, 360, 30):
            x = int((i / 360.0) * width)
            pygame.draw.line(self.panorama_surface, (60, 60, 80), (x, 0), (x, height), 1)
        
        for i in range(-90, 91, 30):
            y = int(((90 - i) / 180.0) * height)
            pygame.draw.line(self.panorama_surface, (60, 60, 80), (0, y), (width, y), 1)
            
            # Label pitch
            pitch_text = font_small.render(f"{i}°", True, (150, 150, 180))
            self.panorama_surface.blit(pitch_text, (10, y - 15))
        
        # Draw some landmarks
        landmarks = [
            ("🏔️ Mountain", 45, 10, (200, 200, 255)),
            ("🌳 Forest", 135, -10, (100, 200, 100)),
            ("🏠 House", 225, -5, (255, 200, 150)),
            ("🌊 Ocean", 315, 0, (100, 150, 255)),
        ]
        
        for name, yaw_deg, pitch_deg, color in landmarks:
            x = int((yaw_deg / 360.0) * width)
            y = int(((90 - pitch_deg) / 180.0) * height)
            
            text = font_small.render(name, True, color)
            self.panorama_surface.blit(text, (x - 50, y))
        
        self.pano_width = width
        self.pano_height = height
        
        print(f"✓ Demo panorama created: {width}x{height}")
    
    def _get_viewport_rect(self) -> pygame.Rect:
        """
        Calculate the viewport rectangle based on current yaw/pitch
        
        Maps view angles to pixel coordinates in the equirectangular panorama
        """
        cfg = self.config
        
        # Normalize yaw to 0-360 range
        norm_yaw = (self.yaw + 180) % 360
        
        # Calculate viewport size in panorama pixels
        # FOV determines what fraction of the full panorama we see
        view_width = int((cfg.FOV_H / 360.0) * self.pano_width)
        view_height = int((cfg.FOV_V / 180.0) * self.pano_height)
        
        # Calculate viewport center position
        center_x = int((norm_yaw / 360.0) * self.pano_width)
        center_y = int(((90 - self.pitch) / 180.0) * self.pano_height)
        
        # Calculate top-left corner
        x = center_x - view_width // 2
        y = center_y - view_height // 2
        
        # Clamp vertical position
        y = max(0, min(y, self.pano_height - view_height))
        
        return pygame.Rect(x, y, view_width, view_height)
    
    def _render_viewport(self):
        """Render the current viewport from the panorama"""
        if self.panorama_surface is None:
            return
        
        cfg = self.config
        viewport = self._get_viewport_rect()
        
        # Handle horizontal wrapping for 360° content
        if viewport.x < 0:
            # Wrap around left edge
            left_width = -viewport.x
            right_width = viewport.width - left_width
            
            # Create composite surface
            composite = pygame.Surface((viewport.width, viewport.height))
            
            # Right portion (from end of panorama)
            right_rect = pygame.Rect(
                self.pano_width - left_width, viewport.y,
                left_width, viewport.height
            )
            composite.blit(self.panorama_surface, (0, 0), right_rect)
            
            # Left portion (from start of panorama)
            left_rect = pygame.Rect(0, viewport.y, right_width, viewport.height)
            composite.blit(self.panorama_surface, (left_width, 0), left_rect)
            
            view_surface = composite
            
        elif viewport.x + viewport.width > self.pano_width:
            # Wrap around right edge
            right_width = self.pano_width - viewport.x
            left_width = viewport.width - right_width
            
            composite = pygame.Surface((viewport.width, viewport.height))
            
            # Left portion (from end of panorama)
            left_rect = pygame.Rect(viewport.x, viewport.y, right_width, viewport.height)
            composite.blit(self.panorama_surface, (0, 0), left_rect)
            
            # Right portion (from start of panorama)
            right_rect = pygame.Rect(0, viewport.y, left_width, viewport.height)
            composite.blit(self.panorama_surface, (right_width, 0), right_rect)
            
            view_surface = composite
        else:
            # Normal case - no wrapping needed
            view_surface = self.panorama_surface.subsurface(viewport)
        
        # Scale to screen size
        scaled = pygame.transform.scale(
            view_surface, 
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
        )
        
        self.screen.blit(scaled, (0, 0))
    
    def _render_hud(self):
        """Render heads-up display overlay"""
        cfg = self.config
        
        # Semi-transparent overlay for text
        overlay = pygame.Surface((250, 100), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (10, 10))
        
        # Orientation info
        mode = "SENSOR" if self.use_sensor else "MOUSE"
        texts = [
            f"Mode: {mode}",
            f"Yaw:   {self.yaw:+.1f}°",
            f"Pitch: {self.pitch:+.1f}°",
        ]
        
        for i, text in enumerate(texts):
            surf = self.font.render(text, True, cfg.TEXT_COLOR)
            self.screen.blit(surf, (20, 20 + i * 28))
        
        # Compass indicator
        compass_x = cfg.SCREEN_WIDTH // 2
        compass_y = 30
        
        # Draw compass background
        pygame.draw.circle(self.screen, (0, 0, 0, 150), (compass_x, compass_y), 25)
        pygame.draw.circle(self.screen, cfg.ACCENT_COLOR, (compass_x, compass_y), 25, 2)
        
        # Draw north indicator
        angle_rad = math.radians(-self.yaw - 90)
        nx = compass_x + int(18 * math.cos(angle_rad))
        ny = compass_y + int(18 * math.sin(angle_rad))
        pygame.draw.line(self.screen, (255, 100, 100), (compass_x, compass_y), (nx, ny), 3)
        
        # Draw N label
        n_surf = self.font.render("N", True, (255, 100, 100))
        self.screen.blit(n_surf, (nx - 6, ny - 10))
        
        # Help text
        help_text = "ESC: Quit | R: Reset | Space: Recalibrate"
        help_surf = self.font.render(help_text, True, (150, 150, 170))
        self.screen.blit(help_surf, (10, cfg.SCREEN_HEIGHT - 35))
        
        # FPS
        fps = self.clock.get_fps()
        fps_surf = self.font.render(f"FPS: {fps:.0f}", True, (150, 150, 170))
        self.screen.blit(fps_surf, (cfg.SCREEN_WIDTH - 100, 10))
    
    def handle_events(self) -> bool:
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_r:
                    self.yaw = 0.0
                    self.pitch = 0.0
                    self.mouse_yaw = 0.0
                    self.mouse_pitch = 0.0
                    if self.use_sensor:
                        self.tracker.reset()
                    print("✓ View reset")
                elif event.key == pygame.K_SPACE:
                    if self.use_sensor:
                        self.tracker.calibrate(samples=200)
        
        return True
    
    def update(self):
        """Update view angles from sensor or mouse"""
        cfg = self.config
        
        if self.use_sensor:
            # Get orientation from MPU6050
            orientation = self.tracker.get_orientation()
            self.yaw = orientation.yaw * cfg.YAW_SENSITIVITY
            self.pitch = orientation.pitch * cfg.PITCH_SENSITIVITY
        else:
            # Mouse control
            mouse_pos = pygame.mouse.get_pos()
            screen_center = (cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
            
            # Map mouse position to angles
            self.yaw = ((mouse_pos[0] - screen_center[0]) / screen_center[0]) * 180
            self.pitch = -((mouse_pos[1] - screen_center[1]) / screen_center[1]) * 60
        
        # Clamp pitch
        self.pitch = max(-85, min(85, self.pitch))
        
        # Update video frame if playing video
        if self.is_video:
            self._read_video_frame()
    
    def run(self):
        """Main application loop"""
        print("\n" + "═" * 60)
        print("  360° PANORAMA VIEWER")
        print("═" * 60)
        print(f"  Mode: {'Sensor (MPU6050)' if self.use_sensor else 'Mouse Control'}")
        print(f"  Content: {'Video' if self.is_video else 'Image'}")
        print("  Controls:")
        print("    ESC   - Quit")
        print("    R     - Reset view to center")
        print("    SPACE - Recalibrate sensor")
        print("═" * 60 + "\n")
        
        while self.running:
            self.running = self.handle_events()
            self.update()
            
            # Render
            self.screen.fill(self.config.BG_COLOR)
            self._render_viewport()
            self._render_hud()
            
            pygame.display.flip()
            self.clock.tick(self.config.FPS)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.video_capture:
            self.video_capture.release()
        if self.use_sensor and hasattr(self, 'tracker'):
            self.tracker.close()
        pygame.quit()
        print("✓ Viewer closed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="360° Panorama/Video Viewer with Head Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python panorama_viewer.py                     # Demo mode
  python panorama_viewer.py my_360_photo.jpg    # View 360° image
  python panorama_viewer.py my_360_video.mp4    # Play 360° video
  python panorama_viewer.py --sim photo.jpg     # Mouse control mode
  
Supported formats:
  Images: JPG, PNG, BMP
  Videos: MP4, AVI, MOV, MKV, WEBM (requires OpenCV)
  
For best results, use equirectangular projection content (2:1 aspect ratio).
        """
    )
    
    parser.add_argument('media', nargs='?', default=None,
                       help='Path to 360° image or video file')
    parser.add_argument('--sim', action='store_true',
                       help='Use mouse control instead of sensor')
    parser.add_argument('--fov', type=float, default=90,
                       help='Horizontal field of view in degrees (default: 90)')
    
    args = parser.parse_args()
    
    # Create viewer
    if args.media:
        viewer = PanoramaViewer(args.media, use_sensor=not args.sim)
    else:
        print("No media file specified - running demo mode")
        viewer = PanoramaViewer("demo", use_sensor=not args.sim)
    
    if args.fov != 90:
        viewer.config.FOV_H = args.fov
        viewer.config.FOV_V = args.fov * 0.67  # Maintain aspect ratio
    
    viewer.run()


if __name__ == "__main__":
    main()

