# Hardware Documentation

> Platform: Jetson Nano (4GB, B01) · JetBot chassis · ROS Noetic

---

## 1. Bill of Materials

### Core Components

| Item | Model / Spec | Qty | Notes |
|------|-------------|-----|-------|
| Main board | Jetson Nano 4GB B01 | 1 | JetPack 4.6.1 |
| MicroSD | SanDisk Extreme 128GB A2 | 1 | Boot + storage |
| USB camera | Logitech C270 (or IMX219 CSI) | 1 | 1280×720, 30fps |
| Motor driver | Adafruit DC/Stepper HAT (DRV8833) | 1 | I2C address 0x60 |
| DC motor | N20 Micro Metal Gearmotor (30:1) | 2 | 12V, 200RPM |
| Encoder | Magnetic encoder (N20 built-in) | 2 | 12 PPR, quadrature |
| IMU | MPU6050 (or ICM-20948) | 1 | I2C address 0x68 |
| Servo | MG996R (metal gear) | 1 | Gripper actuation |
| Battery | 4S LiPo 14.8V 5000mAh | 1 | XT60 connector |
| BEC | 5V/3A step-down regulator | 1 | Jetson power |
| Vibration motor | 1027 coreless 12V | 1 | Dry sand mode |

### Optional

| Item | Purpose |
|------|---------|
| VL53L1X TOF sensor | Obstacle detection backup |
| NEO-6M GPS | Outdoor position logging |
| RC522 RFID | Docking station identification |
| 0.96" OLED (SSD1306) | I2C debug display |

### Mechanical

| Part | Material | Spec |
|------|----------|------|
| Chassis base | 6061 aluminum | 3mm thick, laser-cut |
| Track belt | Rubber + Kevlar cord | 250mm width, custom |
| Track wheels | PETG (3D print) | 50mm diameter |
| Litter bin | PLA (3D print) | 2.5L, detachable |
| Sealing enclosure | 316 stainless steel | IP54 gasketed |

---

## 2. Jetson Nano J41 Pinout

Physical pin assignments used in this project:

```
J41  (40-pin GPIO header, viewed from top, USB ports facing away)
┌──────────────────────────────┐
│  01 3.3V    02  5V           │
│  03 I2C_SDA 04  5V           │
│  05 I2C_SCL 06  GND          │
│  07 GPIO227 08  UART_TXD     │  ← Motor driver TX
│  09 GND     10  UART_RXD     │  ← Motor driver RX
│  11 GPIO226 12  GPIO229      │  ← Vibration MOSFET gate
│  13 GPIO224 14  GND          │
│  15 GPIO225 16  GPIO228      │  ← Servo PWM
│  17 3.3V    18  GPIO230      │
│  19 SPI_MOSI 20 GND          │
│  21 SPI_MISO 22 GPIO231      │
│  23 SPI_CLK  24 SPI_CS0      │
│  25 GND     26 SPI_CS1       │
│  27 I2C_SDA  28 I2C_SCL      │
│  29 GPIO233  30 GND          │
│  31 GPIO234  32 GPIO232      │
│  33 GPIO235  34 GND          │
│  35 GPIO236  36 GPIO237      │
│  37 GPIO238  38 GPIO239      │
│  39 GND     40 GPIO240       │
└──────────────────────────────┘
```

### Pin Allocation

| Pin | Function | Connected To | Driver |
|-----|----------|-------------|--------|
| 8 | UART TX | Motor driver RX | `/dev/ttyTHS1` |
| 10 | UART RX | Motor driver TX | `/dev/ttyTHS1` |
| 12 | GPIO229 | Vibration MOSFET gate | `Jetson.GPIO` |
| 16 | GPIO228 | Servo signal | `Jetson.GPIO` PWM |
| 3 | I2C SDA | IMU SDA + OLED SDA | `/dev/i2c-1` |
| 5 | I2C SCL | IMU SCL + OLED SCL | `/dev/i2c-1` |

> **Warning:** Jetson Nano GPIO is 3.3V logic. Use level shifters for 5V peripherals.

---

## 3. Wiring Diagram

### Power Distribution

```
                ┌─────────────────────┐
                │  4S LiPo 14.8V      │
                │  5000mAh XT60       │
                └─────┬───────────────┘
                      │
          ┌───────────┼───────────────┐
          │           │               │
    5V BEC       12V rail         12V rail
    (5V/3A)      (motor)          (vibration)
          │           │               │
          ▼           ▼               ▼
   [Jetson Nano]  [DRV8833]     [Vibration MOS]
                   │    │             │
               Left ┘    └ Right     GND
               motor       motor
```

### Motor Driver Wiring

```
[Jetson Nano]              [Adafruit DRV8833 HAT]
  UART TX ───────────────── RX (console)
  UART RX ───────────────── TX (console)
  5V BEC  ───────────────── 5V
  GND     ───────────────── GND
```

UART baud: 115200, 8N1.

Motor outputs:

```
Motor driver                Motors
  M1A ───────────────────── Left motor (+)
  M1B ───────────────────── Left motor (-)
  M2A ───────────────────── Right motor (+)
  M2B ───────────────────── Right motor (-)
```

### IMU I2C

```
Jetson I2C (J41:3,5)    MPU6050
  SDA ───────────────── SDA (pin 20)
  SCL ───────────────── SCL (pin 21)
  3.3V ──────────────── VCC (pin 8)
  GND  ──────────────── GND (pin 13)
```

Pull-up resistors: 4.7kΩ on both SDA and SCL lines.

---

## 4. Mechanical Specifications

### Chassis

| Dimension | Value |
|-----------|-------|
| Wheelbase | 750 mm |
| Track width | 250 mm |
| Ground clearance | 60 mm |
| Total weight (w/ battery) | ~4.5 kg |
| Max payload | ~2 kg |

### Track

| Parameter | Value |
|-----------|-------|
| Material | Rubber + Kevlar cord |
| Belt width | 50 mm |
| Pitch | 25 mm |
| Tension | Adjustable via idler position |
| Cleat height | 8 mm (V-shaped, self-cleaning) |

### Collection Mechanism

| Component | Material | Mount |
|-----------|----------|-------|
| Gripper arm | 6061 aluminum + PLA | 2-DOF servo on front plate |
| Litter bin | PLA (3D print) | Quick-release on top deck |
| Intake funnel (optional) | TPU (flex print) | Below camera FOV |

---

## 5. Sensor Specifications

### Camera

| Parameter | Value |
|-----------|-------|
| Sensor | IMX219 (CSI) or Logitech C270 (USB) |
| Resolution | 1280×720 (downsampled to 320×240 for inference) |
| FOV | 120° (wide angle) |
| Mounting | Forward-facing, 30° downward tilt |
| Calibration | `scripts/calibrate_camera.py` (OpenCV chessboard) |

### IMU (MPU6050)

| Parameter | Value |
|-----------|-------|
| Accelerometer | ±2g, ±4g, ±8g, ±16g |
| Gyroscope | ±250, ±500, ±1000, ±2000 °/s |
| Output rate | 100 Hz (configured) |
| Address | 0x68 (AD0 = LOW) |

### Encoder (built-in N20)

| Parameter | Value |
|-----------|-------|
| PPR | 12 (48 CPR with quadrature) |
| Gear ratio | 30:1 |
| Effective resolution | 1440 counts/rev (at output shaft) |

---

## 6. Environmental Protection

### Ingress Protection

| Measure | Implementation | Status |
|---------|---------------|--------|
| Enclosure seal | Silicone gasket + 316SS hardware | Tested |
| Labyrinth vent | 3D-printed labyrinth + GORE membrane | Designed |
| Connector spec | All connectors IP67 (XT60, JST SH) | Implemented |
| Battery compartment | Sealed box + silica gel desiccant | Tested |

### Thermal Management

| Component | Cooling | Activation Temp |
|-----------|---------|-----------------|
| Jetson SoC | Active fan + heatsink | >60°C fan on, >80°C throttle |
| Motor driver | Passive heatsink | N/A |
| BEC regulator | Conduction to chassis | >70°C derate |

---

## 7. Revision History

| Rev | Date | Changes |
|-----|------|---------|
| v1.0 | 2026-03 | Initial prototype, DRV8833 + N20 motors |
| v1.1 | 2026-05 | Added vibration module, switched to CSI camera |
