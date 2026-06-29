"""简单电机测试 - 每个步骤用中文描述"""
import time
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)
mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)

def all_off():
    for ch in range(16):
        pwm.set_pwm(ch, 0, 0)

try:
    # 测试1: 标准MotorHAT Motor 1 FORWARD
    print("测试1: Motor 1 FORWARD (标准通道)")
    m1 = mh.getMotor(1)
    m1.setSpeed(200)
    m1.run(Adafruit_MotorHAT.FORWARD)
    time.sleep(1)
    m1.run(Adafruit_MotorHAT.RELEASE)
    all_off()
    time.sleep(1)

    # 测试2: 标准MotorHAT Motor 1 BACKWARD
    print("测试2: Motor 1 BACKWARD (标准通道)")
    m1.setSpeed(200)
    m1.run(Adafruit_MotorHAT.BACKWARD)
    time.sleep(1)
    m1.run(Adafruit_MotorHAT.RELEASE)
    all_off()
    time.sleep(1)

    # 测试3: 标准MotorHAT Motor 2 FORWARD
    print("测试3: Motor 2 FORWARD (标准通道)")
    m2 = mh.getMotor(2)
    m2.setSpeed(200)
    m2.run(Adafruit_MotorHAT.FORWARD)
    time.sleep(1)
    m2.run(Adafruit_MotorHAT.RELEASE)
    all_off()
    time.sleep(1)

    # 测试4: 标准MotorHAT Motor 2 BACKWARD
    print("测试4: Motor 2 BACKWARD (标准通道)")
    m2.setSpeed(200)
    m2.run(Adafruit_MotorHAT.BACKWARD)
    time.sleep(1)
    m2.run(Adafruit_MotorHAT.RELEASE)
    all_off()
    time.sleep(1)

    # 测试5: PCA9685通道0单独全功率
    print('测试5: "左电机正转" (PCA9685通道0=ON, 通道1=OFF)')
    pwm.set_pwm(0, 0, 4095)
    pwm.set_pwm(1, 0, 0)
    time.sleep(1)
    all_off()
    time.sleep(1)

    # 测试6: PCA9685通道1单独全功率
    print('测试6: "左电机反转" (PCA9685通道1=ON, 通道0=OFF)')
    pwm.set_pwm(0, 0, 0)
    pwm.set_pwm(1, 0, 4095)
    time.sleep(1)
    all_off()
    time.sleep(1)

    # 测试7: PCA9685通道2单独
    print('测试7: "右电机正转" (PCA9685通道2=ON, 通道3=OFF)')
    pwm.set_pwm(2, 0, 4095)
    pwm.set_pwm(3, 0, 0)
    time.sleep(1)
    all_off()
    time.sleep(1)

    # 测试8: PCA9685通道3单独
    print('测试8: "右电机反转" (PCA9685通道3=ON, 通道2=OFF)')
    pwm.set_pwm(2, 0, 0)
    pwm.set_pwm(3, 0, 4095)
    time.sleep(1)
    all_off()

finally:
    m1.run(Adafruit_MotorHAT.RELEASE)
    m2.run(Adafruit_MotorHAT.RELEASE)
    print("\n测试完成")
