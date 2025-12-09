"""
Sensor Fusion Algorithms for Head Tracking
Implements Complementary Filter and Kalman Filter for stable orientation
"""

import math
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional

from mpu6050 import MPU6050, SensorData


@dataclass
class Orientation:
    """3D orientation in degrees"""
    pitch: float  # Rotation around X-axis (nodding)
    roll: float   # Rotation around Y-axis (tilting)
    yaw: float    # Rotation around Z-axis (turning)
    
    def __repr__(self):
        return f"Orientation(pitch={self.pitch:+.1f}°, roll={self.roll:+.1f}°, yaw={self.yaw:+.1f}°)"


class ComplementaryFilter:
    """
    Complementary Filter for sensor fusion
    
    Combines gyroscope (short-term accuracy) with accelerometer 
    (long-term stability) using a weighted average.
    
    The gyroscope provides angular velocity which we integrate for 
    fast response, but it drifts over time. The accelerometer gives
    absolute orientation reference but is noisy and affected by 
    linear acceleration. Combining them gives us the best of both.
    """
    
    def __init__(self, alpha: float = 0.98):
        """
        Initialize the complementary filter
        
        Args:
            alpha: Weight for gyroscope data (0.0 - 1.0)
                   Higher = faster response, more drift
                   Lower = smoother, but slower response
                   Typical values: 0.95 - 0.98
        """
        self.alpha = alpha
        self.orientation = Orientation(0.0, 0.0, 0.0)
        self.last_time: Optional[float] = None
        
    def update(self, sensor_data: SensorData) -> Orientation:
        """
        Update orientation estimate with new sensor readings
        
        Args:
            sensor_data: Current sensor readings
            
        Returns:
            Updated orientation estimate
        """
        current_time = time.time()
        
        # Initialize on first call
        if self.last_time is None:
            self.last_time = current_time
            # Start with accelerometer-based angles
            self.orientation.pitch, self.orientation.roll = self._accel_angles(sensor_data)
            return self.orientation
        
        # Calculate time delta
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Protect against division issues
        if dt <= 0 or dt > 1.0:
            return self.orientation
        
        # Get accelerometer angles (absolute reference)
        accel_pitch, accel_roll = self._accel_angles(sensor_data)
        
        # Integrate gyroscope data (relative change)
        gyro_pitch = self.orientation.pitch + sensor_data.gyro_x * dt
        gyro_roll = self.orientation.roll + sensor_data.gyro_y * dt
        gyro_yaw = self.orientation.yaw + sensor_data.gyro_z * dt
        
        # Apply complementary filter
        # High-pass filter on gyro (trust short-term) + Low-pass filter on accel (trust long-term)
        self.orientation.pitch = self.alpha * gyro_pitch + (1 - self.alpha) * accel_pitch
        self.orientation.roll = self.alpha * gyro_roll + (1 - self.alpha) * accel_roll
        
        # Yaw can only come from gyroscope (accelerometer can't measure it)
        # This will drift over time without a magnetometer
        self.orientation.yaw = gyro_yaw
        
        # Normalize yaw to [-180, 180]
        while self.orientation.yaw > 180:
            self.orientation.yaw -= 360
        while self.orientation.yaw < -180:
            self.orientation.yaw += 360
            
        return self.orientation
    
    def _accel_angles(self, data: SensorData) -> tuple:
        """Calculate pitch and roll from accelerometer data"""
        # Using atan2 for correct quadrant handling
        pitch = math.atan2(data.accel_y, 
                          math.sqrt(data.accel_x**2 + data.accel_z**2))
        roll = math.atan2(-data.accel_x, data.accel_z)
        
        return math.degrees(pitch), math.degrees(roll)
    
    def reset(self):
        """Reset the filter state"""
        self.orientation = Orientation(0.0, 0.0, 0.0)
        self.last_time = None


class KalmanFilter1D:
    """
    Simple 1D Kalman Filter for angle estimation
    
    Provides optimal state estimation by combining predictions
    with measurements, considering their respective uncertainties.
    """
    
    def __init__(self, process_noise: float = 0.001, 
                 measurement_noise: float = 0.03,
                 estimation_error: float = 1.0):
        """
        Initialize Kalman filter parameters
        
        Args:
            process_noise: Q - How much we expect the true value to change
            measurement_noise: R - How noisy our measurements are
            estimation_error: P - Initial uncertainty in our estimate
        """
        self.Q = process_noise       # Process noise covariance
        self.R = measurement_noise   # Measurement noise covariance
        self.P = estimation_error    # Estimation error covariance
        self.K = 0.0                 # Kalman gain
        self.angle = 0.0             # Estimated angle
        self.bias = 0.0              # Gyroscope bias
        
    def update(self, new_angle: float, new_rate: float, dt: float) -> float:
        """
        Update the Kalman filter with new measurements
        
        Args:
            new_angle: Angle from accelerometer (measurement)
            new_rate: Angular rate from gyroscope
            dt: Time delta
            
        Returns:
            Filtered angle estimate
        """
        # Predict
        rate = new_rate - self.bias
        self.angle += dt * rate
        
        # Update estimation error
        self.P += self.Q
        
        # Calculate Kalman gain
        self.K = self.P / (self.P + self.R)
        
        # Update estimate with measurement
        self.angle += self.K * (new_angle - self.angle)
        
        # Update estimation error
        self.P = (1 - self.K) * self.P
        
        return self.angle


class KalmanFilterOrientation:
    """
    Full 3-axis Kalman filter for orientation estimation
    """
    
    def __init__(self, process_noise: float = 0.001,
                 measurement_noise: float = 0.03):
        """
        Initialize the 3-axis Kalman filter
        
        Args:
            process_noise: Process noise (gyro drift)
            measurement_noise: Measurement noise (accel noise)
        """
        self.pitch_filter = KalmanFilter1D(process_noise, measurement_noise)
        self.roll_filter = KalmanFilter1D(process_noise, measurement_noise)
        self.yaw = 0.0
        self.last_time: Optional[float] = None
        
    def update(self, sensor_data: SensorData) -> Orientation:
        """
        Update orientation with new sensor data
        
        Args:
            sensor_data: Current sensor readings
            
        Returns:
            Filtered orientation estimate
        """
        current_time = time.time()
        
        if self.last_time is None:
            self.last_time = current_time
            return Orientation(0.0, 0.0, 0.0)
        
        dt = current_time - self.last_time
        self.last_time = current_time
        
        if dt <= 0 or dt > 1.0:
            return Orientation(
                self.pitch_filter.angle,
                self.roll_filter.angle,
                self.yaw
            )
        
        # Calculate accelerometer angles
        accel_pitch = math.degrees(math.atan2(
            sensor_data.accel_y,
            math.sqrt(sensor_data.accel_x**2 + sensor_data.accel_z**2)
        ))
        accel_roll = math.degrees(math.atan2(
            -sensor_data.accel_x,
            sensor_data.accel_z
        ))
        
        # Update Kalman filters
        pitch = self.pitch_filter.update(accel_pitch, sensor_data.gyro_x, dt)
        roll = self.roll_filter.update(accel_roll, sensor_data.gyro_y, dt)
        
        # Integrate yaw (no accelerometer reference)
        self.yaw += sensor_data.gyro_z * dt
        
        # Normalize yaw
        while self.yaw > 180:
            self.yaw -= 360
        while self.yaw < -180:
            self.yaw += 360
        
        return Orientation(pitch, roll, self.yaw)
    
    def reset(self):
        """Reset the filter state"""
        self.pitch_filter = KalmanFilter1D()
        self.roll_filter = KalmanFilter1D()
        self.yaw = 0.0
        self.last_time = None


class HeadTracker:
    """
    High-level head tracking class that combines sensor reading
    and fusion filtering for easy integration
    """
    
    def __init__(self, filter_type: str = "complementary", alpha: float = 0.96):
        """
        Initialize head tracker
        
        Args:
            filter_type: "complementary" or "kalman"
            alpha: Complementary filter weight (ignored for Kalman)
        """
        self.sensor = MPU6050()
        
        if filter_type.lower() == "kalman":
            self.filter = KalmanFilterOrientation()
            self.filter_name = "Kalman"
        else:
            self.filter = ComplementaryFilter(alpha=alpha)
            self.filter_name = "Complementary"
        
        print(f"✓ Head tracker initialized with {self.filter_name} filter")
    
    def calibrate(self, samples: int = 300):
        """Calibrate the sensor"""
        self.sensor.calibrate(samples=samples)
        
    def get_orientation(self) -> Orientation:
        """
        Get current head orientation
        
        Returns:
            Orientation with pitch, roll, and yaw
        """
        sensor_data = self.sensor.read()
        return self.filter.update(sensor_data)
    
    def get_raw_data(self) -> SensorData:
        """Get raw sensor data"""
        return self.sensor.read()
    
    def reset(self):
        """Reset the filter to initial state"""
        self.filter.reset()
        print("✓ Filter reset")
    
    def close(self):
        """Clean up resources"""
        self.sensor.close()


# Demo/test code
if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Sensor Fusion Demo")
        print("=" * 60)
        
        # Test both filters
        print("\n🔄 Testing Complementary Filter...")
        tracker_comp = HeadTracker(filter_type="complementary", alpha=0.96)
        tracker_comp.calibrate(samples=200)
        
        print("\n📊 Reading orientation (Ctrl+C to stop):\n")
        
        while True:
            orientation = tracker_comp.get_orientation()
            print(f"\r{orientation}", end="")
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\n\n⏹ Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'tracker_comp' in locals():
            tracker_comp.close()

