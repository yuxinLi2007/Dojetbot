# Software Documentation

> ⚠️ **概念文档** — 以下内容基于 README.md 的技术选型表。项目目前无实际代码，所有软件实现待工程开发。

---

## 技术栈

| 模块 | 技术选型 |
|------|----------|
| 操作系统 | Ubuntu 20.04 (Jetson) / Raspberry Pi OS |
| 中间件 | ROS Noetic |
| AI框架 | PyTorch + Transformers |
| 检测模型 | Grounding DINO / YOLOv8（可切换） |
| 仿真环境 | Gazebo + OSM Beach World |
| 嵌入式控制 | Arduino / MicroROS |
| 路径规划 | OMPL / ROS Navigation Stack |
| 视觉处理 | OpenCV + cv_bridge |
| 远程监控 | WebRTC / ROS Web Bridge |
| 底盘驱动 | diff_drive_controller（ROS） |

---

## ROS 包结构

以下文件树来自 README.md 的仓库结构描述：

```
src/
├── perception/          # 垃圾检测模块
│   ├── detector.py
│   ├── grounding_dino_wrapper.py
│   └── preprocess.py
│
├── planning/            # 规划与决策
│   ├── coverage_planner.py
│   ├── local_planner.py
│   └── return_to_dock.py
│
├── control/             # 底层控制
│   ├── chassis_controller.py
│   ├── vibration_controller.py
│   └── gripper_controller.py
│
├── hardware/            # 硬件抽象层
│   ├── motor_driver.py
│   ├── imu_reader.py
│   └── battery_monitor.py
│
└── utils/               # 工具函数
    ├── logger.py
    ├── config_loader.py
    └── ros_utils.py
```

---

## Launch 文件

| 文件 | 描述 |
|------|------|
| `launch/sim_sand.launch` | Gazebo 仿真启动 |
| `launch/robot_bringup.launch` | 实体机器人启动 |
| `launch/cleaning_mission.launch` | 清扫任务启动 |
| `launch/mapping.launch` | SLAM 建图启动 |

> 以上文件仅列出于 README.md 仓库结构中。具体配置内容待工程开发时定义。

---

## 配置文件

| 文件 | 用途 |
|------|------|
| `config/robot_params.yaml` | 机器人通用参数 |
| `config/camera_params.yaml` | 摄像头参数与标定 |
| `config/planner_params.yaml` | 路径规划参数 |
| `config/control_params.yaml` | 控制参数 |

> 以上文件名来自 README.md。具体参数内容待工程实现时定义。

---

## AI 检测流程

READEME.md 中描述的算法处理流程：

```
输入帧
   │
   ▼
预处理（CLAHE去反光 + 沙尘滤波）
   │
   ▼
Grounding DINO / YOLOv8 推理
   │
   ▼
后处理（NMS + 置信度阈值0.5）
   │
   ▼
3D投影（深度估计 + 坐标转换）
   │
   ▼
抓取位姿发布 → 控制层
```

### 训练数据

| 数据集 | 用途 | 状态 |
|--------|------|------|
| TACO (野外垃圾) | 预训练 | 🚧 采集中 |
| 自采沙滩数据 | 微调 | 🚧 采集中 |
| 合成沙滩数据 (Blender) | 数据增强 | 🚧 进行中 |

> 训练流程、模型权重来源、具体训练参数为待定。

---

## 路径规划

| 策略 | 说明 |
|------|------|
| 全覆盖清扫 | 弓字形（Boustrophedon）+ 螺旋补扫边缘 |
| 动态重规划 | 电量 < 30% 自动切换回航路径 |
| 避障 | DWA（Dynamic Window Approach） |

> 以上内容来自 README.md。具体算法实现和参数需工程开发阶段确定。
