import os, sys
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

print("=== PCA9685 Test (0x40) ===")
pwm = PCA9685(address=0x40, busnum=1)
pwm.set_pwm_freq(60)
print("PCA9685 initialized OK")

print("\n=== I2C Check via PCA9685 ===")
# Use PCA9685's built-in I2C to probe addresses
for addr in [0x40, 0x60, 0x70, 0x1b]:
    try:
        pwm._device._bus.read_byte(addr)
        print("  Device at 0x%02x: accessible" % addr)
    except:
        print("  Device at 0x%02x: not accessible" % addr)

print("\n=== MotorHAT Test ===")
try:
    mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
    print("MotorHAT at 0x40: OK")
    m1 = mh.getMotor(1)
    m2 = mh.getMotor(2)
    print("Motor 1:", type(m1))
    print("Motor 2:", type(m2))
    print("PWM addr:", hex(mh._pwm._device.address))
except Exception as e:
    print("MotorHAT at 0x40:", e)
    try:
        mh2 = Adafruit_MotorHAT(i2c_bus=1)
        print("MotorHAT at 0x60: OK")
    except Exception as e2:
        print("MotorHAT at 0x60:", e2)

print("\n=== Checking JetBot module ===")
try:
    import jetbot
    print("jetbot module found")
    print("jetbot path:", jetbot.__file__)
except Exception as e:
    print("jetbot:", e)

print("\n=== Done ===")
