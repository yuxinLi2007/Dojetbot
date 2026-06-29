"""
左轮单独测试 — 检验左轮能否正常转动
"""
import time
from Adafruit_MotorHAT import Adafruit_MotorHAT
from Adafruit_PCA9685 import PCA9685

pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)
mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
m1 = mh.getMotor(1)

def all_off():
    for ch in range(16):
        pwm.set_pwm(ch, 0, 0)
    for i in range(1, 5):
        mh.getMotor(i).run(Adafruit_MotorHAT.RELEASE)

all_off()
time.sleep(0.5)

print("左轮正转 2 秒", flush=True)
m1.setSpeed(200)
m1.run(Adafruit_MotorHAT.FORWARD)
time.sleep(2)

print("停止", flush=True)
all_off()
time.sleep(1)

print("左轮反转 2 秒", flush=True)
m1.setSpeed(200)
m1.run(Adafruit_MotorHAT.BACKWARD)
time.sleep(2)

print("停止", flush=True)
all_off()

print("完成", flush=True)
