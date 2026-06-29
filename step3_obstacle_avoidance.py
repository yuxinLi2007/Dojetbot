"""Step 3: 避障控制 - 结合摄像头检测和运动控制"""
import cv2
import numpy as np
import time
import sys
from Adafruit_PCA9685 import PCA9685
from Adafruit_MotorHAT import Adafruit_MotorHAT

# ========== 摄像头 ==========
GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

ROI_TOP = 200
ROI_BOTTOM = 480
FRAME_W = 640
FRAME_H = 480

ZONES = {
    "left":   (0, 213),
    "center": (213, 426),
    "right":  (426, 640),
}

# ========== 电机 ==========
class MotorController:
    """Waveshare JetBot Board 电机控制"""
    def __init__(self):
        self.pwm = PCA9685(address=0x40, busnum=1)
        self.pwm.set_pwm_freq(60)
        self.mh = Adafruit_MotorHAT(addr=0x40, i2c_bus=1)
        self.m1 = self.mh.getMotor(1)
        self.m2 = self.mh.getMotor(2)
        # Waveshare板通道映射: M1(左) ina=1,inb=0 | M2(右) ina=2,inb=3
        self.M1_INA, self.M1_INB = 1, 0
        self.M2_INA, self.M2_INB = 2, 3
        self.speed = 40  # 0-255

    def _drive_motor(self, motor, ina, inb, power):
        """控制单个电机 power: -255~255"""
        if power > 5:
            self.pwm.set_pwm(ina, 0, power * 16)
            self.pwm.set_pwm(inb, 0, 0)
            motor.run(Adafruit_MotorHAT.FORWARD)
        elif power < -5:
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, abs(power) * 16)
            motor.run(Adafruit_MotorHAT.BACKWARD)
        else:
            self.pwm.set_pwm(ina, 0, 0)
            self.pwm.set_pwm(inb, 0, 0)
            motor.run(Adafruit_MotorHAT.RELEASE)

    def set_motors(self, left, right):
        self._drive_motor(self.m1, self.M1_INA, self.M1_INB, left)
        self._drive_motor(self.m2, self.M2_INA, self.M2_INB, right)

    def forward(self, duration=None):
        self.set_motors(-self.speed, -self.speed)
        if duration: time.sleep(duration); self.stop()

    def backward(self, duration=None):
        self.set_motors(self.speed, self.speed)
        if duration: time.sleep(duration); self.stop()

    def left(self, duration=None):
        self.set_motors(self.speed, -self.speed)
        if duration: time.sleep(duration); self.stop()

    def right(self, duration=None):
        self.set_motors(-self.speed, self.speed)
        if duration: time.sleep(duration); self.stop()

    def stop(self):
        self.set_motors(0, 0)

    def cleanup(self):
        self.stop()
        self.m1.run(Adafruit_MotorHAT.RELEASE)
        self.m2.run(Adafruit_MotorHAT.RELEASE)

    def test_motors(self):
        """快速电机测试"""
        print("电机测试 (各运行0.8秒)...")
        tests = [
            ("左轮正转", -self.speed, 0),
            ("左轮反转", self.speed, 0),
            ("右轮正转", 0, -self.speed),
            ("右轮反转", 0, self.speed),
        ]
        for name, l, r in tests:
            print("  %s" % name)
            self.set_motors(l, r)
            time.sleep(0.8)
            self.stop()
            time.sleep(0.5)
        print("电机测试完成")


# ========== 障碍物检测 ==========
class ObstacleDetector:
    def __init__(self):
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")
        self.ref_brightness = None

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 90)

        result = {"left": False, "center": False, "right": False, "has_obstacle": False}

        if self.ref_brightness is None:
            self.ref_brightness = gray[ROI_TOP:ROI_BOTTOM, 0:213].mean()
            return result

        for zname, (xs, xe) in ZONES.items():
            roi = gray[ROI_TOP:ROI_BOTTOM, xs:xe]
            roi_edge = edges[ROI_TOP:ROI_BOTTOM, xs:xe]

            bdrop = self.ref_brightness - roi.mean()
            texture = roi.std()
            edge_density = np.count_nonzero(roi_edge) / roi_edge.size if roi_edge.size > 0 else 0

            score = 0
            if bdrop > 20: score += 0.5
            if texture > 25: score += 0.3
            if edge_density > 0.04: score += 0.2

            result[zname] = score >= 0.5
            if result[zname]:
                result["has_obstacle"] = True

        return result

    def read(self):
        ret, frame = self.cap.read()
        return ret, frame

    def cleanup(self):
        self.cap.release()


# ========== 避障逻辑 ==========
class ObstacleAvoider:
    def __init__(self):
        print("初始化避障系统...")
        self.motor = MotorController()
        self.camera = ObstacleDetector()
        self.state = "forward"
        self.frame_count = 0

    def run(self, duration=30):
        print("避障模式运行中 (%.1f秒)..." % duration)
        print("状态: forward=前进, avoid=避障, turn=转向")
        start = time.time()
        turn_start = 0
        turn_dir = "left"

        while time.time() - start < duration:
            ret, frame = self.camera.read()
            if not ret:
                continue

            self.frame_count += 1
            result = self.camera.detect(frame)

            # 显示
            if self.frame_count % 30 == 0:
                elapsed = time.time() - start
                print("  [%.1fs] %s | L=%s C=%s R=%s" % (
                    elapsed, self.state.upper(),
                    result["left"], result["center"], result["right"]))

            if self.state == "forward":
                if result["center"] or (result["left"] and result["right"]):
                    # 前方有障碍 → 立即停止并转向
                    self.motor.stop()
                    self.state = "turn"
                    turn_start = time.time()
                    turn_dir = "right" if result["left"] else "left"
                    print("  障碍物! 转向%s" % turn_dir)
                elif result["left"]:
                    # 左侧有障碍 → 微右转
                    self.motor.set_motors(-self.motor.speed, -self.motor.speed + 20)
                elif result["right"]:
                    # 右侧有障碍 → 微左转
                    self.motor.set_motors(-self.motor.speed + 20, -self.motor.speed)
                else:
                    # 无障碍 → 前进
                    self.motor.set_motors(-self.motor.speed, -self.motor.speed)

            elif self.state == "turn":
                # 原地转向
                if turn_dir == "left":
                    self.motor.set_motors(self.motor.speed, -self.motor.speed)
                else:
                    self.motor.set_motors(-self.motor.speed, self.motor.speed)

                # 转向0.6秒后切回前进
                if time.time() - turn_start > 0.6:
                    self.motor.stop()
                    self.state = "forward"
                    # 重新校准参考亮度(场景已变)
                    self.camera.ref_brightness = None
                    print("  转向完成, 继续前进")

        self.motor.stop()
        print("避障测试结束")

    def cleanup(self):
        self.motor.cleanup()
        self.camera.cleanup()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "avoid"

    if mode == "test_motor":
        mc = MotorController()
        try:
            mc.test_motors()
        finally:
            mc.cleanup()

    elif mode == "test_detect":
        det = ObstacleDetector()
        # 快速校准
        for _ in range(5): det.read()
        print("障碍物检测运行5秒...")
        start = time.time()
        while time.time() - start < 5:
            ret, frame = det.read()
            if ret:
                r = det.detect(frame)
                if r["has_obstacle"]:
                    print("  障碍物! L=%s C=%s R=%s" % (r["left"], r["center"], r["right"]))
        det.cleanup()

    elif mode == "avoid":
        avoider = ObstacleAvoider()
        try:
            avoider.run(60)
        finally:
            avoider.cleanup()

    else:
        print("用法: python3 step3_obstacle_avoidance.py [test_motor|test_detect|avoid]")
