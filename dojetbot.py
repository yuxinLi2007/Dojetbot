"""
Dojetbot - Jetson Nano 智能小车避障程序
依赖: OpenCV, Adafruit-MotorHAT, Adafruit-PCA9685
"""
import cv2
import numpy as np
import time
import sys
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

# ==================== 配置 ====================
MOTOR_SPEED = 50       # 电机速度 0-255
TURN_DURATION = 0.6    # 转向时间(秒)
SPEED_DIFF = 20         # 差速转向差值

# 摄像头GStreamer pipeline (Jetson Nano专用)
GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

ROI_TOP = 200          # 检测区域起始行
FRAME_W, FRAME_H = 640, 480

# ==================== 电机控制 ====================
class Motors:
    def __init__(self):
        self.pwm = PCA9685(address=0x40, busnum=1)
        self.pwm.set_pwm_freq(60)
        self.mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
        self.m1 = self.mh.getMotor(1)   # 左电机
        self.m2 = self.mh.getMotor(2)   # 右电机
        # Waveshare板映射: 左(M1): INA=ch1, INB=ch0 | 右(M2): INA=ch2, INB=ch3
        self.ch = {1: (1, 0), 2: (2, 3)}

    def _power(self, motor_id, power):
        """控制单个电机 power: -255~255, 负值=物理正向, 正值=物理反向"""
        ina, inb = self.ch[motor_id]
        motor = self.m1 if motor_id == 1 else self.m2

        if power > 5:  # 正值 = 向后
            self.pwm.set_pwm(ina, 0, power * 16)
            self.pwm.set_pwm(inb, 0, 0)
            motor.run(Adafruit_MotorHAT.FORWARD)
        elif power < -5:  # 负值 = 向前
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, abs(power) * 16)
            motor.run(Adafruit_MotorHAT.BACKWARD)
        else:  # 停止
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, 0)
            motor.run(Adafruit_MotorHAT.RELEASE)

    def drive(self, left, right):
        self._power(1, left)
        self._power(2, right)

    def forward(self, s=None):
        s = -(s or MOTOR_SPEED)
        self.drive(s, s)

    def backward(self, s=None):
        s = s or MOTOR_SPEED
        self.drive(s, s)

    def spin_left(self, s=None):
        """原地左转: 左后右前"""
        sp = s or MOTOR_SPEED
        self.drive(sp, -sp)

    def spin_right(self, s=None):
        """原地右转: 左前右后"""
        sp = s or MOTOR_SPEED
        self.drive(-sp, sp)

    def stop(self):
        self.drive(0, 0)

    def cleanup(self):
        self.stop()
        self.m1.run(Adafruit_MotorHAT.RELEASE)
        self.m2.run(Adafruit_MotorHAT.RELEASE)

    def test(self):
        print("电机测试...")
        for name, l, r in [("左轮前进", -MOTOR_SPEED, 0), ("左轮后退", MOTOR_SPEED, 0),
                            ("右轮前进", 0, -MOTOR_SPEED), ("右轮后退", 0, MOTOR_SPEED)]:
            print("  %s" % name)
            self.drive(l, r)
            time.sleep(0.8)
            self.stop()
            time.sleep(0.3)
        print("电机测试完成")


# ==================== 障碍物检测 ====================
class Detector:
    def __init__(self):
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("摄像头打开失败")
        self.ref_brightness = None

    def detect(self, frame):
        """返回 (left_blocked, center_blocked, right_blocked, has_obstacle)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 90)

        # 自动校准参考亮度(取左区)
        if self.ref_brightness is None:
            self.ref_brightness = gray[ROI_TOP:, :213].mean()
            return False, False, False, False

        result = [False, False, False]
        zones = [(0, 213), (213, 426), (426, 640)]

        for i, (xs, xe) in enumerate(zones):
            roi = gray[ROI_TOP:, xs:xe]
            roi_edge = edges[ROI_TOP:, xs:xe]

            score = 0
            if self.ref_brightness - roi.mean() > 20:
                score += 0.5
            if roi.std() > 25:
                score += 0.3
            if np.count_nonzero(roi_edge) / roi_edge.size > 0.04:
                score += 0.2

            result[i] = score >= 0.5

        return result[0], result[1], result[2], any(result)

    def read(self):
        ret, frame = self.cap.read()
        return ret, frame

    def cleanup(self):
        self.cap.release()


# ==================== 避障控制 ====================
def run_avoidance(duration=60):
    print("=== Dojetbot 避障模式 ===")
    print("运行时长: %.1f秒  速度: %d" % (duration, MOTOR_SPEED))
    print("状态: FWD=前进, TURN=转向, STOP=停止")

    motors = Motors()
    camera = Detector()

    # 等待摄像头稳定
    for _ in range(5):
        camera.read()

    start = time.time()
    frame_count = 0
    state = "FWD"
    turn_start = 0
    turn_dir = "left"

    try:
        while time.time() - start < duration:
            ret, frame = camera.read()
            if not ret:
                continue

            frame_count += 1
            l, c, r, blocked = camera.detect(frame)

            # 每秒输出状态
            if frame_count % 30 == 0:
                elapsed = time.time() - start
                print("  [%.1fs] %s | 左=%s 中=%s 右=%s" % (
                    elapsed, state, l, c, r))

            if state == "FWD":
                if c or (l and r):
                    # 前方有障碍 → 停车转向
                    motors.stop()
                    state = "TURN"
                    turn_start = time.time()
                    turn_dir = "right" if l else "left"
                    print("  > 障碍物! 转向%s <" % turn_dir)
                elif l:
                    # 左侧障碍 → 微右转
                    motors.drive(-MOTOR_SPEED, -MOTOR_SPEED + SPEED_DIFF)
                elif r:
                    # 右侧障碍 → 微左转
                    motors.drive(-MOTOR_SPEED + SPEED_DIFF, -MOTOR_SPEED)
                else:
                    # 无障碍 → 前进
                    motors.forward()

            elif state == "TURN":
                if turn_dir == "left":
                    motors.spin_left()
                else:
                    motors.spin_right()

                if time.time() - turn_start > TURN_DURATION:
                    motors.stop()
                    camera.ref_brightness = None  # 重新校准
                    state = "FWD"
                    print("  > 转向完成 <")

            time.sleep(0.01)  # 防止CPU满载

    finally:
        motors.stop()
        camera.cleanup()

    print("共处理 %d 帧" % frame_count)
    print("测试结束")


# ==================== 主入口 ====================
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "avoid"

    if mode == "test_motor":
        m = Motors()
        try:
            m.test()
        finally:
            m.cleanup()

    elif mode == "test_detect":
        d = Detector()
        for _ in range(10): d.read()
        print("检测测试(5秒)...")
        start = time.time()
        while time.time() - start < 5:
            ret, frame = d.read()
            if ret:
                l, c, r, blocked = d.detect(frame)
                if blocked:
                    print("  障碍物: L=%s C=%s R=%s" % (l, c, r))
        d.cleanup()

    elif mode == "avoid":
        run_avoidance(120)

    else:
        print("用法: python3 dojetbot.py [test_motor|test_detect|avoid]")
