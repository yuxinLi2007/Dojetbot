# Deployment Guide

> Field deployment procedures for DojetBot on Jetson Nano.

---

## 1. Pre-Deployment Checklist

### Hardware

- [ ] Battery charged (≥12.6V on 4S LiPo)
- [ ] Battery voltage verified via `battery_monitor` node
- [ ] All connectors seated (XT60, JST, USB, CSI ribbon)
- [ ] Camera lens clean, no condensation inside housing
- [ ] Track tension checked — belt can deflect ~10mm at midpoint
- [ ] Gripper servo range tested: open/close full stroke
- [ ] Vibration motor functional (if dry sand mode)
- [ ] IP54 seals inspected (gaskets, vent membrane, cable glands)
- [ ] Emergency stop button functional
- [ ] Desiccant in battery compartment not saturated (blue → pink = replace)

### Software

- [ ] `roscore` running — `rosnode ping /rosout`
- [ ] All launch files parse — `roslaunch island_clean robot_bringup.launch` no errors
- [ ] Camera publishing — `rostopic hz /dojetbot/camera/image_raw`
- [ ] IMU publishing — `rostopic echo /dojetbot/imu` (verify stable values at rest)
- [ ] Detector model loaded — `rosparam get /dojetbot/detector/model`
- [ ] GPS lock (if GPS equipped) — fix quality ≥ 2
- [ ] Disk space ≥ 2GB free — `df -h /`
- [ ] System time synchronized — `timedatectl status`

### Environment

- [ ] Operating area mapped (if using known map)
- [ ] Boundaries defined: no-drop zones, cliff edges marked in costmap
- [ ] Charging station positioned, IR beacon active
- [ ] Sand condition assessed: dry / wet / mixed
- [ ] Weather forecast: no rain expected within mission window
- [ ] Beach cleanup: remove large obstacles (>15cm) that robot cannot handle

---

## 2. Sensor Calibration

### Camera Intrinsics

```bash
# Print a chessboard pattern (9×6, 25mm squares)
# Place on flat surface, capture 20+ images from different angles
rosrun island_clean calibrate_camera.py \
  --rows 9 --cols 6 --square 0.025 \
  --device 0 --out config/camera_params.yaml
```

Verification: reprojection error < 0.5 px.

### Camera-to-Robot Extrinsics

The camera is mounted at a fixed position. Transform published in URDF (`models/island_clean.urdf`):

```xml
<joint name="camera_joint" type="fixed">
  <origin xyz="0.15 0 0.12" rpy="0 0.5236 0"/>  <!-- 30° downward tilt -->
  <parent link="base_link"/>
  <child link="camera_link"/>
</joint>
```

To verify: Place a known object 1m in front of robot. Run `rosrun tf tf_echo /base_link /camera_link`. Expected: translation z ≈ 0.12m, rotation pitch ≈ 0.5236 rad.

### IMU Offset

```bash
# With robot stationary on level ground:
rosparam set /dojetbot/imu/gyro_offset_x <value>
rosparam set /dojetbot/imu/accel_offset_z <value>
# Values obtained from 60-second stationary recording
```

### Wheel Odometry Calibration

```bash
# Run a 5m straight-line test:
rosrun island_clean calibrate_odometry.py --distance 5.0 --speed 0.3
# Adjust wheel_radius in robot_params.yaml until error < 2%
```

Rotation calibration: Spin in place 360°, adjust `wheel_base` until heading error < 3°.

---

## 3. Field Startup Procedure

### Step 1: Power On

```bash
# 1. Connect battery (XT60 — expect spark from capacitor inrush, normal)
# 2. Wait for Jetson boot (~30s)
# 3. SSH into robot:
ssh jetson@dojetbot.local
# 4. Verify services:
systemctl status dojetbot  # auto-start service
```

### Step 2: Launch

```bash
# If auto-start is off, launch manually:
roslaunch island_clean robot_bringup.launch
# In a second terminal:
roslaunch island_clean cleaning_mission.launch
```

### Step 3: Pre-Mission Checks

```bash
# In a monitoring terminal:
rostopic list                    # verify all topics exist
rostopic echo /dojetbot/battery  # check voltage (≥12.0V)
rostopic hz /dojetbot/odom       # verify odometry (~50Hz)
rqt_image_view /dojetbot/camera/image_raw  # verify camera feed
```

### Step 4: Start Mission

```bash
# Send start signal via ROS service:
rosservice call /dojetbot/start_mission "{}"
# Robot transitions from IDLE → CLEANING
```

### Step 5: Monitor

```bash
# On monitoring terminal:
rostopic echo /dojetbot/detections  # see what robot detects
rqt_graph                           # verify node connectivity
# Log for later analysis:
rosbag record -a -o logs/field_$(date +%Y%m%d_%H%M).bag
```

---

## 4. Operating Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| IDLE | Startup, mission complete | All nodes running, motors disabled |
| CLEANING | `/start_mission` service | Full coverage + detection + collection |
| RETURNING | Battery < 25% | Interrupt cleaning, navigate to dock |
| CHARGING | Dock connected | Motors off, battery charging, monitoring on |
| EMERGENCY_STOP | Hardware ESTOP or `/estop` service | Kill motor power, log state |
| BLIND | Vision timeout > 30s | Continue coverage without detection |
| MANUAL | `/manual_override` service | Teleop mode via gamepad/keyboard |

Switch modes via:

```bash
rosservice call /dojetbot/set_mode "mode: 'RETURNING'"
```

---

## 5. Charging Station Setup

### Station Placement

- Flat, hard surface (not deep sand)
- Within 50m of operating area
- IR beacon within ±30° of robot approach angle
- Station secured against tide/wind

### Docking Sequence

```
1. Robot navigates to ~2m in front of station (A* global path)
2. Switches to IR-homing mode (±5° acquisition cone)
3. Approaches at reduced speed (0.1 m/s)
4. Mechanical latch engages → charging circuit enabled
5. Battery monitor confirms charging current > 0.5A
6. State transitions: RETURNING → CHARGING
```

### Troubleshooting Docking

| Symptom | Check |
|---------|-------|
| Robot stops 1m short | IR sensor misaligned — adjust beacon angle |
| Latch doesn't engage | Dock height mismatch — verify ground clearance |
| No charging current | Check dock power supply and contact pins |
| Repeated re-docking | Costmap blocked — clear debris from dock area |

---

## 6. Maintenance Schedule

| Interval | Task |
|----------|------|
| **After each mission** | Clean track belts, remove debris from sprockets. Wipe camera lens. Check desiccant color. |
| **Every 10 hours** | Inspect track tension. Lubricate bearing points (dry PTFE spray). Check propeller connectors for corrosion. |
| **Every 50 hours** | Replace desiccant pack. Inspect IP gaskets for wear. Re-torque chassis fasteners (2 N·m). Re-calibrate IMU offset. |
| **Every 100 hours** | Replace track belts if worn. Inspect motor brushes (if brushed motors). Re-calibrate camera intrinsics. Update keepout zones if environment changed. |

---

## 7. Log Collection & Analysis

### On-robot logs

```
logs/
├── rosbag/             # Full ROS bag recordings
├── mission/            # Mission summaries (JSON)
│   └── 2026-05-26.json  # detections, path, battery, errors
└── crash/              # Core dumps / emergency stop traces
```

### Mission Summary JSON Format

```json
{
  "date": "2026-05-26",
  "duration_min": 45,
  "area_covered_m2": 320,
  "items_collected": 47,
  "items_by_type": {"cigarette_butt": 32, "bottle_cap": 8, "plastic": 5, "paper": 2},
  "battery_start_v": 16.4,
  "battery_end_v": 12.1,
  "errors": [],
  "path_length_m": 185
}
```

### Log Download

```bash
# After mission, from PC:
scp -r jetson@dojetbot.local:~/Dojetbot/logs/ ./field_logs/
```

---

## 8. OTA Update Procedure

```bash
# On development PC, push new code:
git push origin main

# On robot:
cd ~/Dojetbot
git pull
catkin_make
sudo systemctl restart dojetbot
```

For model weight updates:

```bash
scp new_model.pt jetson@dojetbot.local:~/Dojetbot/src/perception/weights/
# Update detector_params.yaml model path
```
