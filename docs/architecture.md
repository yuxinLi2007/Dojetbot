# System Architecture

> Target: Jetson Nano (4GB) · ROS Noetic · Ubuntu 20.04

---

## 1. Layer Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Application Layer                         │
│  cleaning_mission  │  teleop_control  │  auto_docking        │
├──────────────────────────────────────────────────────────────┤
│                      ROS Node Layer                           │
│  litter_detector  │  coverage_planner  │  local_planner      │
│  chassis_controller │  gripper_controller │ battery_monitor   │
├──────────────────────────────────────────────────────────────┤
│                   Hardware Abstraction Layer (HAL)            │
│  motor_driver    │  imu_reader    │  camera_driver           │
│  vibration_ctrl  │  gps_reader    │  encoder_reader          │
├──────────────────────────────────────────────────────────────┤
│                        Linux Kernel                           │
│  I2C  │  SPI  │  UART  │  GPIO  │  USB  │  CSI              │
└──────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Role | Examples |
|-------|------|----------|
| Application | Mission-level logic, state machine | cleaning_mission.launch |
| ROS Node | Perception, planning, control nodes | detector.py, coverage_planner.py |
| HAL | Hardware abstraction, wraps kernel interfaces | motor_driver.py, imu_reader.py |
| Kernel | Physical bus and peripheral access | I2C, UART via Linux device files |

---

## 2. ROS Node Graph

### Node List

| Node | Package | Language | Purpose |
|------|---------|----------|---------|
| `litter_detector` | perception | Python | YOLOv8/Grounding DINO inference |
| `coverage_planner` | planning | Python | Boustrophedon coverage path |
| `local_planner` | planning | Python | DWA-based obstacle avoidance |
| `chassis_controller` | control | Python | PID velocity → motor PWM |
| `gripper_controller` | control | Python | Servo position control |
| `vibration_controller` | control | Python | Vibration motor on/off + freq |
| `battery_monitor` | hardware | Python | Voltage/current/SOC monitoring |
| `imu_reader` | hardware | Python | IMU data → odometry |
| `motor_driver` | hardware | Python | Encoder → wheel velocity |

### Topic Flow

```
[camera] ──/camera/image_raw──> [litter_detector]
                                     │
                              /detections (DetectionArray)
                                     │
                                     ▼
                            [coverage_planner]
                                     │
                              /cmd_vel (Twist)
                                     │
                                     ▼
                            [local_planner] ──/obstacles──> [lidar]
                                     │
                              /cmd_vel_safe (Twist)
                                     │
                                     ▼
                           [chassis_controller]
                                     │
                              /motor_pwm (Float32MultiArray)
                                     │
                                     ▼
                            [motor_driver] ──UART──> [DRV8833]
```

### Key Topics

| Topic | Type | Publisher | Subscriber |
|-------|------|-----------|------------|
| `/camera/image_raw` | `sensor_msgs/Image` | camera driver | litter_detector |
| `/detections` | `island_clean/DetectionArray` | litter_detector | coverage_planner |
| `/cmd_vel` | `geometry_msgs/Twist` | coverage_planner | local_planner |
| `/cmd_vel_safe` | `geometry_msgs/Twist` | local_planner | chassis_controller |
| `/odom` | `nav_msgs/Odometry` | imu_reader | local_planner, coverage_planner |
| `/battery` | `sensor_msgs/BatteryState` | battery_monitor | all nodes |
| `/tf` | `tf2_msgs/TFMessage` | imu_reader, camera | all nodes |

---

## 3. Data Pipeline

```mermaid
flowchart LR
    A[Camera<br/>320x240@30fps] --> B[CLAHE + Filter]
    B --> C[YOLOv8 inference<br/>~50ms/frame on Jetson]
    C --> D[NMS + threshold<br/>conf > 0.5]
    D --> E[Pinhole projection<br/>pixel → robot frame]
    E --> F[Grasp pose<br/>→ gripper_controller]
    F --> G[Servo actuation<br/>→ collect bin]
```

### Latency Budget

| Stage | Budget | Measured (Jetson Nano) |
|-------|--------|------------------------|
| Camera capture | 33ms | ~30ms |
| Preprocessing (CLAHE) | 15ms | ~12ms |
| YOLOv8n inference | 80ms | ~55ms |
| NMS + postprocess | 5ms | ~3ms |
| Total per frame | 133ms | ~100ms → ~10 FPS |

---

## 4. Hardware-Software Boundary

```
┌─────────────────┐     ┌──────────────────────┐
│   Jetson Nano   │     │   Peripheral Board   │
│                  │     │                      │
│  GPIO  (J41:12) │────▶│  Vibration MOSFET    │
│  UART  (J41:8)  │◀───▶│  Motor Driver UART   │
│  I2C   (J41:3)  │◀───▶│  IMU (MPU6050)       │
│  SPI   (J41:19) │◀───▶│  RC522 / Radar(opt)  │
│  USB   (type-A) │────▶│  USB Camera           │
│  CSI   (15-pin) │────▶│  Raspberry Pi Cam v2 │
│  PWM   (J41:32) │────▶│  Servo (gripper)      │
└─────────────────┘     └──────────────────────┘
```

Jetson Nano J41 GPIO header pin assignments: See [hardware.md](hardware.md#jetson-nano-j41-pinout).

---

## 5. Startup Sequence

```
Power ON
  │
  ▼
[Kernel boot] → Ubuntu 20.04 login
  │
  ▼
[roscore]  (auto-start via systemd)
  ├── roslaunch island_clean robot_bringup.launch
  │     ├── hardware drivers (imu, battery, motor)
  │     ├── camera node
  │     └── tf tree
  │
  ├── roslaunch island_clean cleaning_mission.launch
  │     ├── litter_detector
  │     ├── coverage_planner
  │     ├── local_planner
  │     └── chassis_controller
  │
  └── [State: IDLE]  ← waits for mission start signal
```

### systemd Unit (auto-start)

File: `/etc/systemd/system/dojetbot.service`

```
[Unit]
Description=DojetBot ROS Startup
After=network.target

[Service]
Type=simple
User=jetson
ExecStart=/home/jetson/Dojetbot/scripts/startup.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 6. ROS Namespace Convention

All nodes run under `/dojetbot/` namespace to allow multi-robot coordination:

```
/dojetbot/camera/image_raw
/dojetbot/detections
/dojetbot/cmd_vel
/dojetbot/odom
/dojetbot/battery
```

Launch files set the namespace via the `ns` attribute:

```xml
<group ns="dojetbot">
  <node name="litter_detector" pkg="island_clean" type="detector.py"/>
</group>
```

---

## 7. Configuration Sources

| Source | File | Parameters |
|--------|------|------------|
| ROS parameter server | `config/robot_params.yaml` | PID gains, max speed, battery thresholds |
| Camera calibration | `config/camera_params.yaml` | Intrinsics, distortion, FOV |
| Planner tuning | `config/planner_params.yaml` | DWA weights, coverage overlap |
| Control gains | `config/control_params.yaml` | Motor PID, servo limits |

YAML parameters are loaded at launch via `rosparam`:

```bash
rosparam load config/robot_params.yaml
```

---

## 8. Fail-Safe States

```
            ┌──────────┐
            │  IDLE    │
            └────┬─────┘
                 │ start_mission
                 ▼
          ┌──────────┐
   ┌──────│ CLEANING │◀──────────────┐
   │      └────┬─────┘               │
   │           │ battery < 25%       │ battery > 90%
   │           ▼                     │
   │      ┌──────────┐               │
   │      │ RETURNING│───────────────┘
   │      └────┬─────┘
   │           │ docked + charged
   │           ▼
   │      ┌──────────┐
   └──────│ CHARGING │
          └──────────┘
```

| State | Action |
|-------|--------|
| ESTOP (hardware) | Kill motor power, log last pose |
| LOW_BATTERY | Interrupt cleaning, run return_to_dock |
| MOTOR_STALL | Retry 3×, then mark stuck position, skip |
| VISION_TIMEOUT | Switch to blind coverage mode |
