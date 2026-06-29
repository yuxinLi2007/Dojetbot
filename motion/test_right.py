"""
右轮测试 — 尝试不同通道组合找到右轮控制器
"""
import time
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)
mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)

def all_off():
    for ch in range(16):
        pwm.set_pwm(ch, 0, 0)
    for i in range(1, 5):
        mh.getMotor(i).run(Adafruit_MotorHAT.RELEASE)

all_off()
time.sleep(0.5)

# 测试所有4个MotorHAT电机
for mid in range(1, 5):
    print("--- MotorHAT Motor %d FORWARD ---" % mid, flush=True)
    m = mh.getMotor(mid)
    m.setSpeed(200)
    m.run(Adafruit_MotorHAT.FORWARD)
    time.sleep(2)
    all_off()
    time.sleep(1)

    print("--- MotorHAT Motor %d BACKWARD ---" % mid, flush=True)
    m.setSpeed(200)
    m.run(Adafruit_MotorHAT.BACKWARD)
    time.sleep(2)
    all_off()
    time.sleep(1)

print("完成", flush=True)
