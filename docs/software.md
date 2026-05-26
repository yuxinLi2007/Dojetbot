# Software Documentation

> ROS Noetic · Ubuntu 20.04 LTS · JetPack 4.6.1 · Python 3.8

---

## 1. System Dependencies

### Required Packages

```bash
# ROS Noetic base
sudo apt install ros-noetic-ros-base ros-noetic-cv-bridge ros-noetic-image-transport

# Python ML stack
sudo apt install python3-pip python3-numpy python3-opencv
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip3 install ultralytics  # YOLOv8
pip3 install transformers  # Grounding DINO dependency

# ROS control
sudo apt install ros-noetic-diff-drive-controller ros-noetic-controller-manager
sudo apt install ros-noetic-robot-localization  # EKF for sensor fusion

# Navigation
sudo apt install ros-noetic-move-base ros-noetic-dwa-local-planner
sudo apt install ros-noetic-gmapping  # optional, for mapping

# Utilities
sudo apt install ros-noetic-rosbag ros-noetic-tf2-tools
sudo apt install ros-noetic-rqt ros-noetic-rqt-graph
```

### Jetson-Specific

```bash
# JetPack includes GPU-accelerated OpenCV and CUDA
# Verify CUDA:
nvcc --version
# Verify OpenCV CUDA:
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep CUDA
```

### Arduino (for MicroROS co-processor, optional)

```bash
sudo apt install arduino
# Install MicroROS library via Arduino Library Manager
```

---

## 2. Build & Install

```bash
# Clone
git clone https://github.com/yuxinLi2007/Dojetbot.git
cd Dojetbot

# Make scripts executable
chmod +x scripts/*.sh

# Install ROS dependencies
./scripts/install_deps.sh

# Build workspace
catkin_make
source devel/setup.bash

# Verify build
rospack list | grep island_clean
```

### CMakeLists.txt Structure

```
CMakeLists.txt                    # Top-level catkin build
├── src/perception/               # Python: no compile needed
├── src/planning/                 # Python: no compile needed
├── src/control/                  # Python: no compile needed
├── src/hardware/                 # Python: no compile needed
└── src/utils/                    # Python: no compile needed
```

All nodes written in Python 3 — no C++ compilation required. `catkin_make` only generates the package manifests and message types.

---

## 3. ROS Package Structure

```
src/
├── perception/
│   ├── __init__.py
│   ├── detector.py           # Main ROS node: subscribes to camera, publishes detections
│   ├── grounding_dino_wrapper.py  # Grounding DINO model loader & infer
│   ├── yolov8_wrapper.py     # YOLOv8 model loader & infer
│   ├── preprocess.py         # CLAHE + sand filtering
│   └── postprocess.py        # NMS, confidence threshold, coordinate transform
│
├── planning/
│   ├── __init__.py
│   ├── coverage_planner.py   # Boustrophedon coverage path generator
│   ├── local_planner.py      # DWA obstacle avoidance
│   └── return_to_dock.py     # A* path to charging station
│
├── control/
│   ├── __init__.py
│   ├── chassis_controller.py # Twist → motor velocity PID
│   ├── vibration_controller.py # On/off + frequency control
│   └── gripper_controller.py # Servo position commands
│
├── hardware/
│   ├── __init__.py
│   ├── motor_driver.py       # Serial protocol to DRV8833
│   ├── imu_reader.py         # MPU6050 I2C → odometry
│   └── battery_monitor.py    # Voltage divider ADC → BatteryState
│
└── utils/
    ├── __init__.py
    ├── logger.py              # rospy.loginfo wrapper + file rotation
    ├── config_loader.py       # YAML parameter loader with validation
    └── ros_utils.py           # TF helpers, quaternion math
```

---

## 4. Launch Files

| File | Starts | Use Case |
|------|--------|----------|
| `robot_bringup.launch` | Hardware drivers + TF tree | Power-on, always run |
| `cleaning_mission.launch` | Perception → Planning → Control | Mission start |
| `sim_sand.launch` | Gazebo + all nodes | Simulation / testing |
| `mapping.launch` | SLAM (gmapping) + teleop | Map building |

### Launch File Inheritance

```xml
<!-- robot_bringup.launch loads the base hardware layer -->
<launch>
  <include file="$(find island_clean)/launch/hardware/imu.launch"/>
  <include file="$(find island_clean)/launch/hardware/motor.launch"/>
  <include file="$(find island_clean)/launch/hardware/camera.launch"/>
  <node name="battery_monitor" pkg="island_clean" type="battery_monitor.py"/>
</launch>
```

---

## 5. Configuration Reference

### robot_params.yaml

```yaml
# === Robot geometry ===
robot:
  wheel_base: 0.23          # meters
  wheel_radius: 0.035       # meters
  max_linear_speed: 0.5     # m/s
  max_angular_speed: 1.0    # rad/s

# === Battery thresholds ===
battery:
  critical: 0.20            # 20% — emergency stop
  low: 0.25                 # 25% — return to dock
  full: 0.90                # 90% — resume mission

# === PID gains ===
pid:
  linear_kp: 0.8
  linear_ki: 0.1
  linear_kd: 0.05
  angular_kp: 1.2
  angular_ki: 0.2
  angular_kd: 0.08
```

### camera_params.yaml

```yaml
camera:
  device: 0                  # /dev/video0 (USB), or "imx219" (CSI)
  width: 1280
  height: 720
  fps: 30
  fov: 120                   # degrees
  tilt_angle: -30            # degrees (negative = downward)
  clahe_clip_limit: 2.0
  clahe_grid_size: 8
```

### detector_params.yaml

```yaml
detector:
  model: "yolov8n.pt"        # or "grounding_dino_base.pth"
  confidence_threshold: 0.5
  nms_iou_threshold: 0.45
  input_size: 320            # inference resolution
  use_cuda: true             # false = CPU fallback
  max_detections: 20
```

### planner_params.yaml

```yaml
planner:
  coverage:
    overlap: 0.3             # 30% path overlap
    speed: 0.3               # m/s during coverage
  dwa:
    max_vel_x: 0.5
    min_vel_x: -0.1
    max_vel_theta: 1.0
    acc_lim_x: 0.5
    acc_lim_theta: 0.8
    xy_goal_tolerance: 0.1
    yaw_goal_tolerance: 0.1
```

---

## 6. Detection Model Setup

### YOLOv8 (Default)

```bash
# Model is downloaded automatically on first run
# Cache location: ~/.config/Ultralytics/
# To use a custom trained model:
cp your_model.pt src/perception/weights/
# Then set detector.model in detector_params.yaml
```

### Grounding DINO (Alternative)

```bash
# Download pretrained weights (~2GB)
wget -P src/perception/weights/ \
  https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0/groundingdino_swint_ogc.pth

# Set detector.model = "groundingdino_swint_ogc.pth" in params
```

**Performance note:** Grounding DINO yields higher accuracy but runs at ~2 FPS on Jetson Nano. YOLOv8n runs at ~18 FPS. Use YOLOv8 for real-time, Grounding DINO for offline verification.

---

## 7. Training Pipeline

### Data Preparation

```bash
# Convert TACO dataset to YOLO format
python3 scripts/convert_taco_to_yolo.py \
  --input data/datasets/taco \
  --output data/datasets/yolo_format

# Generate synthetic beach data (Blender)
blender --background worlds/beach.blend \
  --python scripts/generate_synthetic_data.py \
  -- --output data/datasets/synthetic --count 1000
```

### Training

```bash
# YOLOv8 fine-tuning
yolo train model=yolov8n.pt \
  data=data/datasets/beach.yaml \
  epochs=100 \
  imgsz=320 \
  batch=8 \
  device=0  # GPU
```

Training dataset YAML (`data/datasets/beach.yaml`):

```yaml
train: data/datasets/beach/train
val: data/datasets/beach/val

nc: 4
names: ['cigarette_butt', 'bottle_cap', 'plastic_fragment', 'paper']
```

---

## 8. ROS Message Definitions

Custom message types defined in `msg/`:

**Detection.msg**

```
Header header
string class_id
float32 confidence
float32 x            # center x (pixels)
float32 y            # center y (pixels)
float32 width        # bbox width (pixels)
float32 height       # bbox height (pixels)
float32 distance     # estimated distance (meters)
```

**DetectionArray.msg**

```
Header header
Detection[] detections
```

---

## 9. Development Workflow

### Jetson → PC Remote Development

```bash
# On PC: set ROS master to Jetson
export ROS_MASTER_URI=http://jetson-ip:11311
export ROS_IP=pc-ip

# Verify connection
rostopic list

# Monitor topics remotely
rostopic echo /dojetbot/detections
```

### Logging

```bash
# Record a mission
rosbag record -a -o logs/mission_2026-05-26.bag

# Play back for debugging
rosbag play logs/mission_2026-05-26.bag --clock
```
