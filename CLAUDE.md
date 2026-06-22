# Dojetbot — Jetson Nano 智能小车

## 硬件平台

| 项目 | 详情 |
|------|------|
| **主控** | NVIDIA Jetson Nano (Tegra X1, 4× Cortex-A57) |
| **系统** | Ubuntu 18.04.6 LTS (Bionic Beaver) |
| **内核** | Linux 4.9.253-tegra aarch64 |
| **内存** | 4GB RAM，1.9GB Swap |
| **扩展板** | Waveshare JetBot Board |
| **摄像头** | IMX219 CSI 相机 (通过 nvarguscamerasrc GStreamer 驱动) |

## 已安装的库

### 手动安装
- `Adafruit-MotorHAT` 1.4.0 — Adafruit 电机驱动库
- `Adafruit-PCA9685` 1.0.1 — PCA9685 PWM 控制器库
- `Adafruit-GPIO` 1.0.3
- `spidev` 3.8

### 板载预装
- `Jetson.GPIO` 2.0.17 — Jetson GPIO 库
- `jetbot` — JetBot 项目模块 (`/home/yuxin/jetbot/`)
- OpenCV 4.1.1 — 计算机视觉库
- numpy, matplotlib, pandas, Python 3.6.9

## 硬件接口

### I2C 总线
| 总线 | 设备 | 地址 |
|------|------|------|
| i2c-1 | PCA9685 (电机PWM控制器) | **0x40** |
| i2c-1 | I2C 多路器 | 0x70 |
| i2c-0 | IMX219 摄像头 | 0x3c |

### 其他接口
- `/dev/video0` — CSI 摄像头
- `/dev/ttyTHS1`, `/dev/ttyTHS2` — UART 串口
- gpiochip0 (tegra-gpio, 256 pins)
- pwmchip0, pwmchip4

## 电机驱动方案

### 硬件架构
```
Jetson Nano I2C Bus 1 → PCA9685 @ 0x40 → H桥 → 左右DC电机
```

### 当前通道映射（待验证）
Waveshare JetBot Board 使用 PCA9685 通道 0-3：

| 电机 | INA | INB | 正转(PWM) | 反转(PWM) |
|------|-----|-----|-----------|-----------|
| M1 (左) | ch1 | ch0 | ch1=ON, ch0=OFF | ch1=OFF, ch0=ON |
| M2 (右) | ch2 | ch3 | ch2=ON, ch3=OFF | ch2=OFF, ch3=ON |

### 已知问题
- 标准 Adafruit MotorHAT 通道（8-13）也能驱动电机，当前不确定哪组通道实际连接
- **电机极性反向**：代码中正值=电机向后转，负值=电机向前转
- 需进一步确认 PCA9685 各通道与物理电机的对应关系

## 已完成功能

### Step 1: 摄像头 ✅
- 使用 GStreamer pipeline 驱动 IMX219
- 分辨率 640x480 @ 30FPS
- 成功捕获并保存画面

### Step 2: 障碍物检测 ✅
- 三重检测：亮度下降 + 纹理分析 + 边缘密度
- 左/中/右三区障碍物判断
- 自动校准参考亮度
- 验证：成功检测到前方物体

### Step 3: 避障控制 🚧 (进行中)
- 前进/后退/左转/右转/停止 功能已实现
- 电机极性映射待最终确认
- 避障逻辑：前进 → 遇障碍 → 停车转向 → 继续前进

## 使用说明

### SSH 连接
```bash
ssh yuxin@10.1.41.174  # 密码: 123456
```

### 运行避障
```bash
cd ~/Dojetbot
python3 dojetbot.py forward    # 前进测试
python3 dojetbot.py avoid      # 避障模式 (120秒)
```

### 电机测试
```bash
python3 dojetbot.py test_motor     # 快速电机测试
python3 simple_motor_test.py        # 详细的通道测试
```

### 摄像头测试
```bash
python3 step1b_test_camera_jetpack.py  # 验证摄像头
python3 step2_obstacle_detection.py 8  # 障碍物检测测试
```

## 待办事项

- [ ] **完成电机通道映射调试** — 确认 PCA9685 各通道与电机的对应关系
- [ ] 验证避障逻辑完整流程
- [ ] 添加键盘遥控模式
- [ ] 添加 Web 控制界面

## 注意事项
- 小车插网线，测试速度和距离要控制
- 先在桌面用 `test_motor` 模式验证方向，再运行避障
- Jetson Nano 是 ARM64 架构
