"""
电机校准测试
逐轮测试，确认每个电机的通道映射和物理方向
"""
import time
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)

MOTOR_HAT = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)


def all_off():
    """关闭所有PWM通道并释放电机"""
    for ch in range(16):
        pwm.set_pwm(ch, 0, 0)
    for i in range(1, 5):
        MOTOR_HAT.getMotor(i).run(Adafruit_MotorHAT.RELEASE)


def pwm_direct(ina_ch, inb_ch, power):
    """直接控制H桥：power>0 → INA=PWM, INB=0；power<0 → INA=0, INB=PWM"""
    if power > 0:
        pwm.set_pwm(ina_ch, 0, power)
        pwm.set_pwm(inb_ch, 0, 0)
    elif power < 0:
        pwm.set_pwm(ina_ch, 0, 0)
        pwm.set_pwm(inb_ch, 0, -power)
    else:
        pwm.set_pwm(ina_ch, 0, 0)
        pwm.set_pwm(inb_ch, 0, 0)


# ========== 测试计划 ==========
tests = [
    # (名称, ina_ch, inb_ch, power, 说明)
    ("左轮 — 方向A (ch1=PWM, ch0=0)", 1, 0, 4095,
     "观察：是哪个轮子在转？向前还是向后？"),
    ("左轮 — 方向B (ch1=0, ch0=PWM)", 1, 0, -4095,
     "观察：转向与方向A相同还是相反？"),
    ("右轮 — 方向A (ch2=PWM, ch3=0)", 2, 3, 4095,
     "观察：是哪个轮子在转？向前还是向后？"),
    ("右轮 — 方向B (ch2=0, ch3=PWM)", 2, 3, -4095,
     "观察：转向与方向A相同还是相反？"),
]

print("=" * 60)
print("  电机校准测试")
print("=" * 60)
print()
print("测试将依次进行，每个测试持续2秒，间隔2秒")
print("请观察并记录每个测试中哪个轮子转、方向如何")
print()
print("5秒后开始...")
time.sleep(5)

all_off()
time.sleep(1)

try:
    for name, ina, inb, power, desc in tests:
        print()
        print("-" * 60)
        print("【%s】" % name)
        print("  %s" % desc)
        print("-" * 60)

        pwm_direct(ina, inb, power)
        time.sleep(2)

        all_off()
        time.sleep(2)

    print()
    print("=" * 60)
    print("  测试完成！请在下面记录观察结果")
    print("=" * 60)
    print()
    print("请CEO告诉我每个测试的观察结果：")
    print("  1. 哪个轮子转？（左轮/右轮）")
    print("  2. 转动的方向？（向前/向后）")
    print("  3. 方向A和方向B是相同还是相反？")

finally:
    all_off()
    print()
    print("电机已释放")
