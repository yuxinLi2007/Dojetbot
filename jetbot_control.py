"""
JetBot 小车控制代码
硬件: Jetson Nano + Waveshare JetBot Board (PCA9685 @ 0x40)
电机: 2路DC电机 (M1左, M2右)
"""
import time
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

class JetBot:
    def __init__(self, addr=0x40, busnum=1):
        # PCA9685 PWM控制器
        self.pwm = PCA9685(address=addr, busnum=busnum)
        self.pwm.set_pwm_freq(60)

        # Adafruit MotorHAT (用于标准控制)
        self.mh = Adafruit_MotorHAT(addr=addr, i2c_bus=busnum)

        # 左右电机 (Adafruit MotorHAT标准通道)
        self.left_motor = self.mh.getMotor(1)
        self.right_motor = self.mh.getMotor(2)

        # Waveshare JetBot板的引脚映射:
        # M1(左): INA=PCA9685 ch1, INB=PCA9685 ch0
        # M2(右): INA=PCA9685 ch2, INB=PCA9685 ch3
        # forward: INA=PWM, INB=0
        # backward: INA=0, INB=PWM
        self.M1_INA = 1
        self.M1_INB = 0
        self.M2_INA = 2
        self.M2_INB = 3

        self._speed = 0.5  # 默认速度 50%

    def _set_motor_pwm(self, channel, ina, inb, speed):
        """直接设置PCA9685通道控制电机"""
        speed = max(-1.0, min(1.0, speed))  # 限制在[-1, 1]
        val = int(4095 * abs(speed))

        if speed > 0:  # 正转: INA=PWM, INB=0
            self.pwm.set_pwm(ina, 0, val)
            self.pwm.set_pwm(inb, 0, 0)
            channel.run(Adafruit_MotorHAT.FORWARD)
        elif speed < 0:  # 反转: INA=0, INB=PWM
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, val)
            channel.run(Adafruit_MotorHAT.BACKWARD)
        else:  # 停止
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, 0)
            channel.run(Adafruit_MotorHAT.RELEASE)

    def set_speed(self, speed):
        """设置速度 (0.0 ~ 1.0)"""
        self._speed = max(0.0, min(1.0, speed))

    def set_motors(self, left, right):
        """分别控制左右电机: [-1.0, 1.0]"""
        self._set_motor_pwm(self.left_motor, self.M1_INA, self.M1_INB, left)
        self._set_motor_pwm(self.right_motor, self.M2_INA, self.M2_INB, right)

    def forward(self, speed=None, duration=None):
        s = self._speed if speed is None else speed
        print(">> 前进  speed=%.2f" % s)
        self.set_motors(s, s)
        if duration:
            time.sleep(duration)
            self.stop()

    def backward(self, speed=None, duration=None):
        s = self._speed if speed is None else speed
        print(">> 后退  speed=%.2f" % s)
        self.set_motors(-s, -s)
        if duration:
            time.sleep(duration)
            self.stop()

    def left(self, speed=None, duration=None):
        s = self._speed if speed is None else speed
        print(">> 左转  speed=%.2f" % s)
        self.set_motors(-s, s)
        if duration:
            time.sleep(duration)
            self.stop()

    def right(self, speed=None, duration=None):
        s = self._speed if speed is None else speed
        print(">> 右转  speed=%.2f" % s)
        self.set_motors(s, -s)
        if duration:
            time.sleep(duration)
            self.stop()

    def stop(self):
        print(">> 停止")
        self.set_motors(0, 0)

    def cleanup(self):
        self.stop()
        self.mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
        print("清理完成")


if __name__ == "__main__":
    import sys

    bot = JetBot()
    bot.set_speed(0.4)  # 先用40%速度测试

    print("=== JetBot 控制测试 ===")
    print("命令: forward, backward, left, right, stop, speed <0-1>, quit")

    try:
        if len(sys.argv) > 1:
            # 命令行模式
            cmd = sys.argv[1]
            dur = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
            spd = float(sys.argv[3]) if len(sys.argv) > 3 else None

            if cmd == "forward":
                bot.forward(speed=spd, duration=dur)
            elif cmd == "backward":
                bot.backward(speed=spd, duration=dur)
            elif cmd == "left":
                bot.left(speed=spd, duration=dur)
            elif cmd == "right":
                bot.right(speed=spd, duration=dur)
            elif cmd == "demo":
                # 演示: 前进-后退-左转-右转
                for action in ["forward", "backward", "left", "right"]:
                    getattr(bot, action)(duration=1.5)
                    time.sleep(0.5)
            print("完成!")
        else:
            # 交互模式
            while True:
                cmd = input("> ").strip().lower()
                if cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "forward":
                    bot.forward(duration=1.0)
                elif cmd == "backward":
                    bot.backward(duration=1.0)
                elif cmd == "left":
                    bot.left(duration=0.8)
                elif cmd == "right":
                    bot.right(duration=0.8)
                elif cmd == "stop":
                    bot.stop()
                elif cmd.startswith("speed"):
                    try:
                        bot.set_speed(float(cmd.split()[1]))
                        print("速度设为:", bot._speed)
                    except:
                        print("用法: speed <0-1>")
                elif cmd == "demo":
                    for action in ["forward", "backward", "left", "right"]:
                        getattr(bot, action)(duration=1.5)
                        time.sleep(0.5)
                else:
                    print("命令: forward, backward, left, right, stop, speed <N>, demo, quit")
    finally:
        bot.cleanup()
