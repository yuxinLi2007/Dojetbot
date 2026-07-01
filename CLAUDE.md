# Dojetbot — Jetson Nano 智能小车

## 硬件平台

| 项目 | 详情 |
|------|------|
| **主控** | NVIDIA Jetson Nano (Tegra X1, 4× Cortex-A57) |
| **系统** | Ubuntu 18.04.6 LTS (Bionic Beaver) |
| **内核** | Linux 4.9.253-tegra aarch64 |
| **内存** | 4GB RAM，1.9GB Swap |
| **存储** | 板载eMMC |
| **扩展板** | Waveshare JetBot Board |

## 已安装的库

### Python 系统包
- Python 3.6.9
- pip 9.0.1
- numpy 1.13.3
- matplotlib 2.1.1
- pandas 0.22.0

### 电机控制相关（手动安装）
- `Adafruit-MotorHAT` 1.4.0
- `Adafruit-PCA9685` 1.0.1
- `Adafruit-GPIO` 1.0.3

### 板载已预装
- `Jetson.GPIO` 2.0.17 — Jetson GPIO库
- `jetbot` — JetBot项目模块 (位于 `/home/yuxin/jetbot/`)

### 未安装但可能需要
- `smbus` / `smbus2` — 原始 I2C 访问
- `opencv-python` 4.1.1 — 图像处理 (含 DNN 模块)
- `Flask` 2.0.3 — HTTP 串流服务
- `torch` / `torchvision` — PyTorch（JetBot AI相关，未安装）

## 硬件接口

### I2C 总线

| 总线 | 设备地址 | 说明 |
|------|---------|------|
| i2c-0 | 0x3c | 摄像头 IMX219 |
| i2c-1 | 0x1b, 0x40 (PCA9685), 0x70 | 电机PWM控制、I2C多路器 |
| i2c-2 | 0x50, 0x57 | EEPROM |
| i2c-3 | — | 未使用 |
| i2c-4 | max77620 | PMIC |
| i2c-5 | — | 未使用 |
| i2c-6 | — | 未使用 |

### GPIO

- **gpiochip0**: tegra-gpio, 256 pins, base 0 (Jetson Nano主GPIO)
- **gpiochip504**: max77620-gpio, 8 pins, base 504 (PMIC GPIO)

用户 `yuxin` 在 `gpio` 和 `i2c` 组中，可直接访问GPIO和I2C。

### PWM

- `pwmchip0` — 7000a000.pwm
- `pwmchip4` — 70110000.pwm

### 其他接口

| 接口 | 路径 | 说明 |
|------|------|------|
| 摄像头 | `/dev/video0` | IMX219 CSI摄像头 |
| 串口 | `/dev/ttyTHS1`, `/dev/ttyTHS2` | UART串口 |
| SPI | 设备树已注册未导出 | /dev/spi* 不存在 |

## 电机驱动方案

### 硬件架构

```
Jetson Nano (I2C Bus 1)
    ↓
PCA9685 PWM控制器 @ 0x40  (16通道, 12位PWM, 60Hz)
    ↓
H桥电机驱动 (Waveshare JetBot Board)
    ↓
左右2路DC电机
```

### PCA9685 通道映射（Waveshare JetBot Board）

根据 `jetbot/motor.py` 源代码：

| 电机 | 通道 | 说明 |
|------|------|------|
| M1 (左) | INA = ch1, INB = ch0 | 正转: ch1=PWM, ch0=0; 反转: ch1=0, ch0=PWM |
| M2 (右) | INA = ch2, INB = ch3 | 正转: ch2=PWM, ch3=0; 反转: ch2=0, ch3=PWM |

### 标准 MotorHAT 通道（可能未连接）

标准 Adafruit Motor HAT 映射（PCA9685通道）：
- Motor 1: PWM=ch8, IN1=ch9, IN2=ch10
- Motor 2: PWM=ch13, IN1=ch11, IN2=ch12

注意：Waveshare版上这些通道可能未连接，实际控制通过通道0-3。

### 控制方式

有两种控制方式：
1. **直接PCA9685控制** — 通过 Adafruit_PCA9685 直接设置通道0-3的PWM
2. **Adafruit MotorHAT + Waveshare覆盖** — 使用 MotorHAT 库同时覆盖通道0-3

## 已验证可运行代码

### `detection/app.py` — YOLOv3-tiny 实时检测串流服务器 (MVP v0.2.0)
```bash
cd ~/Dojetbot/detection
nohup python3 app.py > /tmp/yolo_server.log 2>&1 &
```
浏览器打开 `http://10.1.41.174:5000` 查看实时检测画面。

### `detection/test_app.py` — 环境测试
```bash
python3 ~/Dojetbot/detection/test_app.py
```
测试摄像头 + YOLOv3-tiny 模型加载。

### `jetbot_control.py` — 主控制脚本
```bash
python3 ~/Dojetbot/jetbot_control.py forward 1.0 0.3   # 前进1秒，速度30%
python3 ~/Dojetbot/jetbot_control.py backward 1.0 0.3  # 后退1秒，速度30%
python3 ~/Dojetbot/jetbot_control.py left 1.0 0.3      # 左转1秒
python3 ~/Dojetbot/jetbot_control.py right 1.0 0.3     # 右转1秒
python3 ~/Dojetbot/jetbot_control.py demo 1.5 0.4      # 演示序列
```

注意：当前电机极性映射还有待调试，后退方向有动作（略带转弯），前进方向无动作。需要进一步调整 INA/INB 的映射关系。

### `test_motor_channels.py` — 电机通道诊断
测试每个PCA9685通道的电机响应，确定正确的通道映射。

### `test_car_hw.py` — 硬件检测
检测PCA9685、MotorHAT初始化、I2C设备探测。

## 待办/下一步计划

- [ ] 修正电机方向映射（前进无动作问题）
- [ ] 确认左右电机对应的通道
- [ ] 调整左转/右转逻辑（差速转向）
- [ ] 添加速度PID控制
- [x] 集成摄像头实时画面 (YOLOv3-tiny, HTTP串流, 320x240, 端口5000)
- [ ] 添加遥控控制（键盘/手柄）
- [ ] 实现自动避障
- [ ] 实现巡线功能
- [ ] 添加Web控制界面
- [ ] 升级到YOLOv8n（需安装PyTorch for Jetson或编译onnxruntime）

## 开发/调试指南

### SSH连接
```bash
ssh yuxin@10.1.41.174  # 密码: 123456
```

### 文件传输
```bash
scp local_file yuxin@10.1.41.174:~/Dojetbot/
```

### 运行Python脚本
```bash
python3 ~/Dojetbot/script_name.py
```

### I2C调试
```bash
i2cdetect -y -r 1   # 扫描I2C Bus 1
i2cget -y 1 0x40 0x00 w  # 读取PCA9685寄存器
```

### 注意事项
- 小车插着网线，测试时速度不宜超过30%，距离不宜超过1米
- 不要同时长时间运行电机避免过热
- Jetson Nano为ARM64架构，安装包时确认有arm64版本
