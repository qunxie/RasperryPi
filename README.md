# 🎮 Raspberry Pi Head Tracker with MPU6050

A complete head tracking system using Raspberry Pi and MPU6050 IMU sensor. The system reads accelerometer and gyroscope data, applies sensor fusion filtering, and displays a real-time 3D head visualization that follows your movements.

![Head Tracker Demo](https://img.shields.io/badge/Status-Ready-brightgreen) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)

---

## 📋 Table of Contents

- [Features](#-features)
- [Hardware Requirements](#-hardware-requirements)
- [Wiring Diagram](#-wiring-diagram)
- [Software Setup](#-software-setup)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Customization](#-customization)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

- **Real-time head tracking** with 3-axis orientation (pitch, roll, yaw)
- **Sensor fusion** using Complementary Filter or Kalman Filter
- **Cyberpunk-themed 3D visualization** with animated wireframe head
- **Live orientation gauges** and data display
- **Simulation mode** for development without hardware
- **Auto-calibration** for drift compensation
- **Low latency** optimized for 60 FPS display

---

## 🔧 Hardware Requirements

| Component | Description | Notes |
|-----------|-------------|-------|
| **Raspberry Pi** | Pi 3, 4, or 5 | Any model with I²C support |
| **MPU6050** | 6-axis IMU (accel + gyro) | ~$3-5 module |
| **Jumper wires** | Female-to-female, 4 pcs | For I²C connection |
| **Display** | HDMI monitor or Pi display | For visualization |

### Optional Additions
- **Headband/mount** - To attach MPU6050 to your head
- **Power bank** - For portable operation
- **MPU9250** - 9-axis upgrade with magnetometer for yaw stability

---

## 📌 Wiring Diagram

Connect the MPU6050 to Raspberry Pi GPIO:

```
MPU6050          Raspberry Pi
───────          ─────────────
VCC    ────────► Pin 1  (3.3V)
GND    ────────► Pin 6  (GND)
SDA    ────────► Pin 3  (GPIO 2 / SDA)
SCL    ────────► Pin 5  (GPIO 3 / SCL)
```

### Visual Wiring Diagram

```
                    ┌─────────────────────────────────┐
                    │         RASPBERRY PI            │
                    │                                 │
┌──────────┐        │  [1] 3.3V ◄──── VCC            │
│  MPU6050 │        │  [3] SDA  ◄──── SDA            │
│          │        │  [5] SCL  ◄──── SCL            │
│ VCC SDA  │        │  [6] GND  ◄──── GND            │
│ GND SCL  │        │                                 │
└──────────┘        └─────────────────────────────────┘
```

---

## 💻 Software Setup

### Step 1: Enable I²C on Raspberry Pi

```bash
# Open configuration tool
sudo raspi-config

# Navigate to:
# → Interface Options → I2C → Enable → Yes

# Reboot to apply changes
sudo reboot
```

### Step 2: Verify I²C Connection

```bash
# Install I²C tools
sudo apt-get update
sudo apt-get install -y i2c-tools

# Detect MPU6050 (should show 0x68)
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

### Step 3: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv head_tracker_env
source head_tracker_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Test the Sensor

```bash
# Test MPU6050 connection
python3 mpu6050.py
```

---

## 🚀 Usage

### Run the Head Tracker Display

```bash
# With sensor connected
python3 head_tracker_display.py

# Simulation mode (for development without sensor)
python3 head_tracker_display.py --sim
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--sim` | Run in simulation mode (mouse control) |
| `--width <pixels>` | Set display width (default: 1280) |
| `--height <pixels>` | Set display height (default: 720) |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `ESC` | Quit application |
| `R` | Reset orientation to center |
| `C` | Recalibrate sensor |

---

## 📁 Project Structure

```
Raspberry Pi/
├── mpu6050.py              # MPU6050 sensor driver
├── sensor_fusion.py        # Complementary & Kalman filters
├── head_tracker_display.py # Main pygame display application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### File Descriptions

| File | Purpose |
|------|---------|
| `mpu6050.py` | Low-level I²C driver for MPU6050. Reads raw accelerometer and gyroscope data, handles calibration. |
| `sensor_fusion.py` | Implements Complementary Filter and Kalman Filter to combine sensor data into stable orientation. |
| `head_tracker_display.py` | Pygame application with 3D head visualization, orientation gauges, and animated UI. |

---

## ⚙️ How It Works

### 1. Sensor Reading
The MPU6050 provides:
- **Accelerometer**: Measures gravitational force (orientation reference)
- **Gyroscope**: Measures angular velocity (rotation speed)

### 2. Sensor Fusion
Raw sensor data has limitations:
- **Accelerometer**: Stable long-term but noisy and affected by motion
- **Gyroscope**: Fast and smooth but drifts over time

We combine them using a **Complementary Filter**:

```
Orientation = α × (Gyro Integration) + (1-α) × (Accel Angle)
```

Where α = 0.96 (trust gyro for 96% of short-term, accel for 4%)

### 3. Orientation Mapping

| Axis | Movement | Display Effect |
|------|----------|----------------|
| **Pitch** (X) | Nodding up/down | Head tilts forward/backward |
| **Roll** (Y) | Tilting side-to-side | Head tilts left/right |
| **Yaw** (Z) | Turning left/right | Head rotates horizontally |

### 4. Display Output
The pygame visualization renders a 3D wireframe head that mirrors your movements in real-time.

---

## 🎨 Customization

### Adjust Sensitivity
Edit `head_tracker_display.py`:

```python
@dataclass
class Config:
    # Sensitivity multipliers
    PITCH_SENSITIVITY: float = 1.0  # Increase for more responsive pitch
    ROLL_SENSITIVITY: float = 1.0
    YAW_SENSITIVITY: float = 1.0
```

### Change Filter Parameters
Edit `sensor_fusion.py`:

```python
# Higher alpha = faster response, more gyro trust
tracker = HeadTracker(filter_type="complementary", alpha=0.98)

# Or use Kalman filter for smoother output
tracker = HeadTracker(filter_type="kalman")
```

### Modify Display Theme
Edit colors in `Config` class:

```python
# Cyberpunk theme colors
ACCENT_PINK: Tuple[int, int, int] = (255, 50, 150)
ACCENT_CYAN: Tuple[int, int, int] = (0, 255, 255)
HEAD_COLOR: Tuple[int, int, int] = (0, 255, 200)
```

---

## 🔍 Troubleshooting

### "I2C bus not found"
```bash
# Make sure I2C is enabled
sudo raspi-config
# Go to Interface Options → I2C → Enable

# Check if kernel module is loaded
lsmod | grep i2c
```

### "Could not connect to MPU6050"
1. Check wiring connections
2. Verify I²C address:
   ```bash
   i2cdetect -y 1
   ```
3. If address is `0x69` instead of `0x68`, update in code:
   ```python
   sensor = MPU6050(address=0x69)
   ```

### "pygame not found" or display issues
```bash
# Install pygame dependencies
sudo apt-get install -y python3-pygame

# For headless Pi (SSH), set display
export DISPLAY=:0
```

### Drift in Yaw Axis
Yaw drift is expected without a magnetometer. The gyroscope integrates rotation but accumulates error. Solutions:
1. Press `R` to reset periodically
2. Upgrade to MPU9250 (includes magnetometer)
3. Add external magnetometer (e.g., HMC5883L)

### Jittery Movement
1. Increase filter alpha (e.g., 0.98 instead of 0.96)
2. Add physical stabilization to sensor mounting
3. Check for electrical interference

---

## 📚 References

- [MPU6050 Datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf)
- [Raspberry Pi I2C Documentation](https://www.raspberrypi.com/documentation/computers/os.html#i2c)
- [Complementary Filter Explained](https://www.pieter-jan.com/node/11)
- [Kalman Filter Tutorial](https://www.kalmanfilter.net/)

---

## 📄 License

MIT License - Feel free to use and modify for your projects!

---

## 🙏 Credits

Built with:
- [smbus2](https://github.com/kplindegaard/smbus2) - I²C library
- [pygame](https://www.pygame.org/) - Graphics and display
- [numpy](https://numpy.org/) - Numerical operations

---

**Happy Head Tracking! 🎯**

