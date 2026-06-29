"""
move.py — 基础运动控制（前进/后退）
依赖: Adafruit_MotorHAT
"""
import time
from Adafruit_MotorHAT import Adafruit_MotorHAT
from motor_config import LEFT_MOTOR_ID, RIGHT_MOTOR_ID, DEFAULT_SPEED


class Move:
    def __init__(self):
        self.mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
        self.left = self.mh.getMotor(LEFT_MOTOR_ID)
        self.right = self.mh.getMotor(RIGHT_MOTOR_ID)

    def forward(self, duration=2.0):
        print(">> 前进", flush=True)
        self.left.setSpeed(DEFAULT_SPEED)
        self.right.setSpeed(DEFAULT_SPEED)
        self.left.run(Adafruit_MotorHAT.FORWARD)
        self.right.run(Adafruit_MotorHAT.FORWARD)
        time.sleep(duration)
        self.stop()

    def backward(self, duration=2.0):
        print(">> 后退", flush=True)
        self.left.setSpeed(DEFAULT_SPEED)
        self.right.setSpeed(DEFAULT_SPEED)
        self.left.run(Adafruit_MotorHAT.BACKWARD)
        self.right.run(Adafruit_MotorHAT.BACKWARD)
        time.sleep(duration)
        self.stop()

    def stop(self):
        self.left.setSpeed(0)
        self.right.setSpeed(0)
        self.left.run(Adafruit_MotorHAT.RELEASE)
        self.right.run(Adafruit_MotorHAT.RELEASE)
        print(">> 停止", flush=True)

    def cleanup(self):
        self.stop()


if __name__ == "__main__":
    import sys

    bot = Move()
    try:
        cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
        dur = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

        if cmd == "forward":
            bot.forward(duration=dur)
        elif cmd == "backward":
            bot.backward(duration=dur)
        elif cmd == "test":
            print("=== 运动测试 ===")
            print("前进2秒", flush=True)
            bot.forward(duration=dur)
            time.sleep(1)
            print("后退2秒", flush=True)
            bot.backward(duration=dur)
        else:
            print("用法: python3 move.py [forward|backward|test] [时长秒]")
    finally:
        bot.cleanup()
