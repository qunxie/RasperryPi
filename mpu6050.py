"""
MPU6050 Sensor Driver for Raspberry Pi
Communicates via I2C to read accelerometer and gyroscope data
"""

import smbus2
import time
import math
from dataclasses import dataclass


@dataclass
class SensorData:
    """Container for sensor readings"""
    accel_x: float  # g
    accel_y: float  # g
    accel_z: float  # g
    gyro_x: float   # degrees/sec
    gyro_y: float   # degrees/sec
    gyro_z: float   # degrees/sec
    temp: float     # Celsius


class MPU6050:
    """
    MPU6050 6-axis IMU sensor driver
    
    Wiring:
        VCC → 3.3V (Pin 1)
        GND → GND (Pin 6)
        SDA → GPIO 2 (Pin 3)
        SCL → GPIO 3 (Pin 5)
    """
    
    # MPU6050 Register Addresses
    PWR_MGMT_1 = 0x6B
    PWR_MGMT_2 = 0x6C
    SMPLRT_DIV = 0x19
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    INT_ENABLE = 0x38
    
    # Data Registers
    ACCEL_XOUT_H = 0x3B
    ACCEL_YOUT_H = 0x3D
    ACCEL_ZOUT_H = 0x3F
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43
    GYRO_YOUT_H = 0x45
    GYRO_ZOUT_H = 0x47
    
    # Default I2C address (AD0 pin low)
    DEFAULT_ADDRESS = 0x68
    ALT_ADDRESS = 0x69  # AD0 pin high
    
    # Scale factors
    ACCEL_SCALE = {
        0: 16384.0,  # ±2g
        1: 8192.0,   # ±4g
        2: 4096.0,   # ±8g
        3: 2048.0    # ±16g
    }
    
    GYRO_SCALE = {
        0: 131.0,    # ±250°/s
        1: 65.5,     # ±500°/s
        2: 32.8,     # ±1000°/s
        3: 16.4      # ±2000°/s
    }
    
    def __init__(self, bus_num: int = 1, address: int = DEFAULT_ADDRESS,
                 accel_range: int = 0, gyro_range: int = 0):
        """
        Initialize MPU6050 sensor
        
        Args:
            bus_num: I2C bus number (1 for Raspberry Pi 3/4)
            address: I2C address (0x68 or 0x69)
            accel_range: 0=±2g, 1=±4g, 2=±8g, 3=±16g
            gyro_range: 0=±250°/s, 1=±500°/s, 2=±1000°/s, 3=±2000°/s
        """
        self.bus = smbus2.SMBus(bus_num)
        self.address = address
        self.accel_scale = self.ACCEL_SCALE[accel_range]
        self.gyro_scale = self.GYRO_SCALE[gyro_range]
        
        # Calibration offsets
        self.accel_offset = [0.0, 0.0, 0.0]
        self.gyro_offset = [0.0, 0.0, 0.0]
        
        self._initialize()
    
    def _initialize(self):
        """Wake up and configure the sensor"""
        # Wake up the MPU6050 (clear sleep bit)
        self._write_byte(self.PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        
        # Set sample rate divider (sample rate = 8kHz / (1 + divider))
        self._write_byte(self.SMPLRT_DIV, 0x07)  # ~1kHz sample rate
        
        # Configure low-pass filter (DLPF)
        self._write_byte(self.CONFIG, 0x06)  # 5Hz bandwidth, 19ms delay
        
        # Set gyroscope range
        self._write_byte(self.GYRO_CONFIG, 0x00)  # ±250°/s
        
        # Set accelerometer range
        self._write_byte(self.ACCEL_CONFIG, 0x00)  # ±2g
        
        print("✓ MPU6050 initialized successfully")
    
    def _write_byte(self, register: int, value: int):
        """Write a byte to a register"""
        self.bus.write_byte_data(self.address, register, value)
    
    def _read_byte(self, register: int) -> int:
        """Read a byte from a register"""
        return self.bus.read_byte_data(self.address, register)
    
    def _read_word(self, register: int) -> int:
        """Read a 16-bit word from two consecutive registers"""
        high = self.bus.read_byte_data(self.address, register)
        low = self.bus.read_byte_data(self.address, register + 1)
        value = (high << 8) | low
        
        # Convert to signed value
        if value >= 0x8000:
            value = -((65535 - value) + 1)
        return value
    
    def _read_raw_data(self) -> tuple:
        """Read all raw sensor data in one burst"""
        # Read 14 bytes starting from ACCEL_XOUT_H
        data = self.bus.read_i2c_block_data(self.address, self.ACCEL_XOUT_H, 14)
        
        def to_signed(high, low):
            value = (high << 8) | low
            if value >= 0x8000:
                value = -((65535 - value) + 1)
            return value
        
        accel_x = to_signed(data[0], data[1])
        accel_y = to_signed(data[2], data[3])
        accel_z = to_signed(data[4], data[5])
        temp = to_signed(data[6], data[7])
        gyro_x = to_signed(data[8], data[9])
        gyro_y = to_signed(data[10], data[11])
        gyro_z = to_signed(data[12], data[13])
        
        return accel_x, accel_y, accel_z, temp, gyro_x, gyro_y, gyro_z
    
    def read(self) -> SensorData:
        """
        Read and return calibrated sensor data
        
        Returns:
            SensorData with accelerometer (g), gyroscope (°/s), and temperature (°C)
        """
        raw = self._read_raw_data()
        
        return SensorData(
            accel_x=(raw[0] / self.accel_scale) - self.accel_offset[0],
            accel_y=(raw[1] / self.accel_scale) - self.accel_offset[1],
            accel_z=(raw[2] / self.accel_scale) - self.accel_offset[2],
            temp=(raw[3] / 340.0) + 36.53,  # Temperature formula from datasheet
            gyro_x=(raw[4] / self.gyro_scale) - self.gyro_offset[0],
            gyro_y=(raw[5] / self.gyro_scale) - self.gyro_offset[1],
            gyro_z=(raw[6] / self.gyro_scale) - self.gyro_offset[2]
        )
    
    def calibrate(self, samples: int = 500, delay: float = 0.005):
        """
        Calibrate sensor by averaging readings while stationary
        
        Args:
            samples: Number of samples to average
            delay: Delay between samples in seconds
        """
        print(f"🔧 Calibrating... Keep sensor still for {samples * delay:.1f} seconds")
        
        accel_sum = [0.0, 0.0, 0.0]
        gyro_sum = [0.0, 0.0, 0.0]
        
        for i in range(samples):
            raw = self._read_raw_data()
            
            accel_sum[0] += raw[0] / self.accel_scale
            accel_sum[1] += raw[1] / self.accel_scale
            accel_sum[2] += raw[2] / self.accel_scale
            gyro_sum[0] += raw[4] / self.gyro_scale
            gyro_sum[1] += raw[5] / self.gyro_scale
            gyro_sum[2] += raw[6] / self.gyro_scale
            
            time.sleep(delay)
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Progress: {(i + 1) / samples * 100:.0f}%")
        
        # Calculate offsets (assuming Z-axis should read 1g when flat)
        self.accel_offset = [
            accel_sum[0] / samples,
            accel_sum[1] / samples,
            (accel_sum[2] / samples) - 1.0  # Subtract 1g for Z-axis
        ]
        self.gyro_offset = [
            gyro_sum[0] / samples,
            gyro_sum[1] / samples,
            gyro_sum[2] / samples
        ]
        
        print("✓ Calibration complete!")
        print(f"  Accel offset: X={self.accel_offset[0]:.4f}, "
              f"Y={self.accel_offset[1]:.4f}, Z={self.accel_offset[2]:.4f}")
        print(f"  Gyro offset:  X={self.gyro_offset[0]:.4f}, "
              f"Y={self.gyro_offset[1]:.4f}, Z={self.gyro_offset[2]:.4f}")
    
    def get_accel_angles(self) -> tuple:
        """
        Calculate pitch and roll from accelerometer data only
        
        Returns:
            (pitch, roll) in degrees
        """
        data = self.read()
        
        # Calculate angles using atan2 for full 360° range
        pitch = math.atan2(data.accel_y, 
                          math.sqrt(data.accel_x**2 + data.accel_z**2))
        roll = math.atan2(-data.accel_x, data.accel_z)
        
        return math.degrees(pitch), math.degrees(roll)
    
    def close(self):
        """Close the I2C bus connection"""
        self.bus.close()
        print("✓ MPU6050 connection closed")


# Test the sensor if run directly
if __name__ == "__main__":
    try:
        print("=" * 50)
        print("MPU6050 Sensor Test")
        print("=" * 50)
        
        sensor = MPU6050()
        sensor.calibrate(samples=200)
        
        print("\n📊 Reading sensor data (Ctrl+C to stop):\n")
        
        while True:
            data = sensor.read()
            pitch, roll = sensor.get_accel_angles()
            
            print(f"\rAccel: X={data.accel_x:+.2f}g Y={data.accel_y:+.2f}g Z={data.accel_z:+.2f}g | "
                  f"Gyro: X={data.gyro_x:+.1f}°/s Y={data.gyro_y:+.1f}°/s Z={data.gyro_z:+.1f}°/s | "
                  f"Pitch={pitch:+.1f}° Roll={roll:+.1f}° | Temp={data.temp:.1f}°C", end="")
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n⏹ Stopped by user")
    except FileNotFoundError:
        print("❌ I2C bus not found. Make sure I2C is enabled:")
        print("   sudo raspi-config → Interface Options → I2C → Enable")
    except OSError as e:
        print(f"❌ Could not connect to MPU6050: {e}")
        print("   Check wiring and I2C address (0x68 or 0x69)")
    finally:
        if 'sensor' in locals():
            sensor.close()

