"""
电机配置 — Waveshare JetBot Board
记录校准后的电机映射和方向约定
"""
from Adafruit_MotorHAT import Adafruit_MotorHAT

# ====== PCA9685 通道映射 ======
# M1(左轮): INA=ch1, INB=ch0
# M2(右轮): INA=ch2, INB=ch3
LEFT_INA = 1
LEFT_INB = 0
RIGHT_INA = 2
RIGHT_INB = 3

# ====== MotorHAT 电机 ID ======
LEFT_MOTOR_ID = 1
RIGHT_MOTOR_ID = 2

# ====== 方向约定 ======
# MotorHAT.FORWARD / MotorHAT.BACKWARD 对应物理方向
# （待校准确认，目前假设 FORWARD=前进，如不对可互换）
FORWARD = Adafruit_MotorHAT.FORWARD
BACKWARD = Adafruit_MotorHAT.BACKWARD

# ====== 默认速度 ======
DEFAULT_SPEED = 200   # 0-255
