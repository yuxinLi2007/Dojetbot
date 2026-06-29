"""
电机诊断脚本 - 逐个测试PCA9685通道
"""
import time
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)

def all_off():
    for ch in range(16):
        pwm.set_pwm(ch, 0, 0)

all_off()
print("1. 标准MotorHAT控制 (无Waveshare覆盖)")
mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
m1 = mh.getMotor(1)
m2 = mh.getMotor(2)

print("   Motor 1 FORWARD speed=200")
m1.setSpeed(200)
m1.run(Adafruit_MotorHAT.FORWARD)
time.sleep(1)
m1.run(Adafruit_MotorHAT.RELEASE)
time.sleep(0.5)

print("   Motor 1 BACKWARD speed=200")
m1.setSpeed(200)
m1.run(Adafruit_MotorHAT.BACKWARD)
time.sleep(1)
m1.run(Adafruit_MotorHAT.RELEASE)
time.sleep(0.5)

print("   Motor 2 FORWARD speed=200")
m2.setSpeed(200)
m2.run(Adafruit_MotorHAT.FORWARD)
time.sleep(1)
m2.run(Adafruit_MotorHAT.RELEASE)
time.sleep(0.5)

print("   Motor 2 BACKWARD speed=200")
m2.setSpeed(200)
m2.run(Adafruit_MotorHAT.BACKWARD)
time.sleep(1)
m2.run(Adafruit_MotorHAT.RELEASE)

all_off()
print("\n2. 直接PCA9685通道控制")
print("   测试 ch0=4095")
pwm.set_pwm(0, 0, 4095)
time.sleep(1)
all_off()
time.sleep(0.5)

print("   测试 ch1=4095")
pwm.set_pwm(1, 0, 4095)
time.sleep(1)
all_off()
time.sleep(0.5)

print("   测试 ch2=4095")
pwm.set_pwm(2, 0, 4095)
time.sleep(1)
all_off()
time.sleep(0.5)

print("   测试 ch3=4095")
pwm.set_pwm(3, 0, 4095)
time.sleep(1)
all_off()

print("\n3. H桥组合测试 ch0/ch1")
print("   ch0=4095, ch1=0")
pwm.set_pwm(0, 0, 4095)
pwm.set_pwm(1, 0, 0)
time.sleep(1)
all_off()
time.sleep(0.5)

print("   ch0=0, ch1=4095")
pwm.set_pwm(0, 0, 0)
pwm.set_pwm(1, 0, 4095)
time.sleep(1)
all_off()

print("\n4. H桥组合测试 ch2/ch3")
print("   ch2=4095, ch3=0")
pwm.set_pwm(2, 0, 4095)
pwm.set_pwm(3, 0, 0)
time.sleep(1)
all_off()
time.sleep(0.5)

print("   ch2=0, ch3=4095")
pwm.set_pwm(2, 0, 0)
pwm.set_pwm(3, 0, 4095)
time.sleep(1)
all_off()

print("\n=== 测试完成 ===")
