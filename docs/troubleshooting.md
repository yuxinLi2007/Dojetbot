# Troubleshooting Guide

> Common issues, diagnostic procedures, and fixes for DojetBot on Jetson Nano.

---

## 1. Startup Issues

### Node Won't Start

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `rosrun` exits with `ImportError` | Missing Python dependency | `pip3 install -r requirements.txt` |
| `rosparam load` fails | YAML syntax error | Validate: `python3 -c "import yaml; yaml.load(open('params.yaml'))"` |
| `RLException: file not found` | Wrong launch path | Run from workspace root: `source devel/setup.bash` |
| `[FATAL] [WallTime]` segfault | Model weight issue | Re-download weights, check file permissions |

### roscore Fails

```bash
# Common fix: reset ROS environment
killall roscore rosmaster
rm -rf /tmp/ros*
source devel/setup.bash
roscore &
```

### Service Doesn't Auto-Start

```bash
# Check unit status
systemctl status dojetbot

# Common issues:
# 1. User not in dialout group (no /dev/ttyTHS1 access)
sudo usermod -a -G dialout jetson

# 2. ROS_MASTER_URI not set in systemd env
sudo systemctl edit dojetbot
# Add:
# [Service]
# Environment="ROS_MASTER_URI=http://localhost:11311"
# Environment="ROS_IP=127.0.0.1"
```

---

## 2. Motor & Drive System

### Motor Not Moving

```bash
# Step 1: Check if motor driver is responding
echo -e "v\r" > /dev/ttyTHS1  # Should return firmware version
# Step 2: Check UART permissions
ls -l /dev/ttyTHS1  # Should be crw-rw----, group dialout
# Step 3: Check battery voltage
rostopic echo /dojetbot/battery  # Should be ≥ 12.0V under load
```

### Motor Jitters / Stalls

| Cause | Check | Fix |
|-------|-------|-----|
| Low battery | Voltage < 11.5V under load | Recharge |
| Encoder wiring | Pins A/B swapped | Swap encoder A/B in wiring |
| PID too aggressive | Response overshoots target | Reduce PID gains → half Kp |
| Gearbox binding | Audible grinding | Replace motor |

### Uneven Track Tension

Adjust idler: turn tension screw clockwise 1/4 turn per 5mm deflection. Both sides should deflect equally.

### Robot Drifts Left/Right

```bash
# Calibrate wheel speeds
rosrun island_clean calibrate_odometry.py --distance 5.0
# Expected: deviation < 0.1m over 5m
# If > 0.1m, check:
# - Wheel radii differ → adjust robot_params.yaml wheel_radius
# - One motor has different RPM → replace motor pair
```

---

## 3. Camera & Vision Issues

### No Camera Feed

```bash
# Check USB camera
ls /dev/video*                  # Should show /dev/video0 or similar
v4l2-ctl --list-devices         # Verify camera detected
# Check CSI camera
ls /sys/class/video4linux/      # Should show imx219 device
```

### Black / Frozen Frame

```bash
# Restart camera driver
rosnode kill /dojetbot/camera_node
roslaunch island_clean hardware/camera.launch
```

### Detection Model Not Running

```bash
# Verify model file exists
ls -la src/perception/weights/
# Check CUDA availability
python3 -c "import torch; print(torch.cuda.is_available())"
# If false: install CUDA-compatible PyTorch:
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Low Detection Accuracy

| Observation | Likely Cause | Fix |
|-------------|-------------|-----|
| Misses small objects in bright sun | Glare washes out image | Enable CLAHE: set `clahe_clip_limit: 2.0` |
| False positives on shells | Model hasn't seen enough non-litter beach items | Collect more negative samples and retrain |
| Detections at wrong distance | Camera intrinsics out of date | Re-run camera calibration |
| Low FPS (< 5) | Inference too slow | Switch to YOLOv8n, reduce `input_size: 224` |

---

## 4. Navigation & Planning

### Robot Gets Stuck

```bash
# Check if local planner is receiving /odom
rostopic echo /dojetbot/odom -n1
# Check if obstacles are detected
rostopic echo /dojetbot/obstacles -n1
# Check cmd_vel output
rostopic echo /dojetbot/cmd_vel_safe -n1
```

### Stuck Recovery Procedure

```bash
# 1. Send manual override
rosservice call /dojetbot/set_mode "mode: 'MANUAL'"
# 2. Teleop away from obstacle
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
# 3. Resume mission
rosservice call /dojetbot/set_mode "mode: 'CLEANING'"
```

### Path Coverage Gaps

- **Cause:** Overlap ratio too small
- **Fix:** Increase `planner.coverage.overlap` to 0.4 in `planner_params.yaml`
- **Verify:** Run coverage simulation, check coverage heatmap in RViz

### Robot Avoids Clean Sand

- **Cause:** Costmap has outdated obstacles
- **Fix:** Clear costmap: `rosservice call /move_base/clear_costmaps`

---

## 5. Battery & Power

### Sudden Shutdown

```bash
# Check minimum voltage from log
grep "battery" logs/mission/latest.json
# If < 10.5V: LVC (Low Voltage Cutoff) triggered
# Fix: Set safe shutdown threshold higher
# In robot_params.yaml:
# battery:
#   critical: 0.25  # was 0.20
```

### Battery Swells

- **Stop using immediately.** Replace battery.
- Check charger: LiPo balance charger must show cell voltages within 0.1V of each other.

### Short Run Time

| Condition | Expected | Check |
|-----------|----------|-------|
| Dry sand, no vibration | ~120 min | Battery capacity ≥ 5000mAh |
| Dry sand, vibration | ~45 min | Motor current draw |
| Wet sand | ~90 min | Track binding |

To log power consumption during a mission:

```bash
rosbag record /dojetbot/battery /dojetbot/odom -O logs/power_test.bag
# Post-process:
rosrun island_clean analyze_power.py logs/power_test.bag
```

---

## 6. Communication

### SSH Connection Fails

```bash
# Check if robot is on network
ping dojetbot.local
# If unreachable: check WiFi connection
# If robot has no display, use serial console over UART
# J11 header (UART): 115200 baud, 3.3V logic
```

### ROS Topics Not Visible Remotely

```bash
# On robot:
echo $ROS_MASTER_URI   # Should be http://localhost:11311
# On PC:
export ROS_MASTER_URI=http://<robot-ip>:11311
export ROS_IP=<pc-ip>
# Firewall:
sudo ufw allow 11311/tcp
```

### Intermittent WiFi Drops

Sand and saltwater degrade WiFi signal significantly.

```bash
# Mitigation: use 5GHz band (shorter range but less interference)
nmcli dev wifi list
sudo nmcli connection modify DojetBot 802-11-wireless.band a
# Or: use directional antenna + keep robot within 30m of AP
```

---

## 7. Environmental Issues

### Overheating

```bash
# Check current temperature
cat /sys/devices/virtual/thermal/thermal_zone0/temp
# Divide by 1000 → temperature in °C
# If > 80°C: Jetson will throttle to ~400MHz
# Fix: increase fan speed
echo 255 > /sys/devices/pwm-fan/target_pwm  # max fan
```

### Camera Lens Fogging

- **Cause:** Thermal shock (cold beach air + warm internal electronics)
- **Fix:** Apply anti-fog coating to lens. Add desiccant pack inside camera housing.

### Sand Ingestion

- **Check:** After each mission, open enclosure and check for sand.
- **If found:** Clean with compressed air. Replace labyrinth vent filter.
- **Root cause:** Vent filter clogged → positive pressure failed.
- **Fix:** Clean/replace GORE vent membrane.

---

## 8. Diagnostic Commands Quick Reference

```bash
# === Node Status ===
rosnode list                    # All running nodes
rosnode info /dojetbot/litter_detector  # Node connections
rosnode ping /dojetbot/litter_detector  # Latency check

# === Topic Monitoring ===
rostopic list                   # All active topics
rostopic hz /dojetbot/odom      # Frequency check
rostopic bw /dojetbot/camera/image_raw  # Bandwidth
rostopic echo /dojetbot/detections -n1  # Last detection

# === Parameter Debug ===
rosparam list                   # All parameters
rosparam get /dojetbot/pid      # Specific param

# === TF Tree ===
rosrun tf view_frames           # Generate tf PDF
rosrun tf tf_echo /base_link /camera_link  # Transform check

# === Log Analysis ===
rosbag info logs/mission.bag    # Duration, topics, size
rosbag play logs/mission.bag --clock  # Replay
rqt_bag                         # GUI inspection

# === Performance ===
htop                            # CPU / memory
jtop                            # Jetson-specific: GPU, RAM, temp
nvidia-smi                      # GPU utilization
```

---

## 9. Recovery Procedures

### Emergency Stop Recovery

1. Press hardware ESTOP
2. Wait 5 seconds
3. Release ESTOP (twist clockwise)
4. Re-enable motors: `rosservice call /dojetbot/enable_motors`
5. Robot is in IDLE state — resume with `/start_mission`

### ROS Master Crash Recovery

```bash
# Robot will stop all motion when ROS connection drops
# Restore:
killall roslaunch
roscore &
# Wait for roscore ready, then:
roslaunch island_clean robot_bringup.launch
roslaunch island_clean cleaning_mission.launch
# Robot does NOT auto-resume — must restart mission
```

### Lost Communication Recovery

If robot drives out of WiFi range:

1. Robot continues mission autonomously (pre-programmed behavior)
2. When battery < 25%, robot returns to dock (no WiFi required for docking)
3. After charging, waits for connection to resume
4. To force recovery: go to last known position with USB serial console

---

## 10. Frequently Asked Questions

**Q: Can I use a Raspberry Pi instead of Jetson Nano?**

AI inference (YOLOv8) runs at ~2 FPS on Raspberry Pi 4 — not usable for real-time. Use Jetson Nano or Orin NX.

**Q: How do I reset the robot if it's stuck mid-mission?**

Hold the ESTOP button for 3 seconds. All motors disengage. Manually move robot to safe position, release ESTOP, restart mission.

**Q: What does the error LED pattern mean?**

| Blinks | Meaning |
|--------|---------|
| 1 blink | Normal operation |
| 2 blinks | Battery low |
| 3 blinks | Motor stall |
| 4 blinks | Vision failure |
| Solid | System error — check logs |

**Q: Why does the robot stop at the water line?**

The moisture sensor in the chassis detects conductivity change. Configure threshold in `robot_params.yaml`:

```yaml
safety:
  moisture_sensor_threshold: 500  # ADC value, lower = wetter
```
