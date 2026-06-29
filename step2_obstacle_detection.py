"""Step 2: 障碍物检测 - 使用OpenCV实时分析摄像头画面
检测策略: 亮度分析 + 纹理分析 + 边缘检测三重判断
"""
import cv2
import numpy as np
import time
import os

# Jetson Nano GStreamer pipeline
GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

# 检测区域
ROI_TOP = 200
ROI_BOTTOM = 480
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 分区 (水平三等份)
ZONES = {
    "left":   (0, 213),
    "center": (213, 426),
    "right":  (426, 640),
}

# 检测阈值
INTENSITY_DROP_THRESHOLD = 20   # 亮度下降超过此值视为有障碍物
TEXTURE_THRESHOLD = 25          # 纹理(标准差)超过此值视为有障碍物
EDGE_DENSITY_THRESHOLD = 0.04   # 边缘密度阈值(已降低)


class ObstacleDetector:
    def __init__(self):
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")

        # 参考亮度 (启动后自动校准)
        self.ref_brightness = None

        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()

    def detect(self, frame):
        """检测前方障碍物，返回各区域状态和标注后的画面"""
        result = {
            "left": False,
            "center": False,
            "right": False,
            "has_obstacle": False,
        }
        display = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # 边缘检测
        edges = cv2.Canny(blur, 30, 90)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # ROI边缘
        roi_mask = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)
        cv2.rectangle(roi_mask, (0, ROI_TOP), (FRAME_WIDTH, ROI_BOTTOM), 255, -1)
        roi_edges = cv2.bitwise_and(edges, roi_mask)

        # 绘制ROI边界
        cv2.rectangle(display, (0, ROI_TOP), (FRAME_WIDTH, ROI_BOTTOM), (255, 255, 0), 1)

        # 如果还没有参考亮度，先校准(取左区亮度)
        if self.ref_brightness is None:
            left_roi = gray[ROI_TOP:ROI_BOTTOM, 0:213]
            self.ref_brightness = left_roi.mean()
            print("  参考亮度已校准: %.1f" % self.ref_brightness)

        # 逐区域分析
        zone_scores = {}
        for zone_name, (x_start, x_end) in ZONES.items():
            roi = gray[ROI_TOP:ROI_BOTTOM, x_start:x_end]
            roi_edges_zone = roi_edges[ROI_TOP:ROI_BOTTOM, x_start:x_end]

            # 指标1: 亮度下降
            mean_bright = roi.mean()
            brightness_drop = self.ref_brightness - mean_bright

            # 指标2: 纹理强度 (标准差)
            texture = roi.std()

            # 指标3: 边缘密度
            edge_density = np.count_nonzero(roi_edges_zone) / roi_edges_zone.size if roi_edges_zone.size > 0 else 0

            # 计算综合得分 (0-1)
            # 亮度下降 > 阈值 或 纹理 > 阈值 或 边缘密度 > 阈值 则判定为有障碍物
            score = 0
            reasons = []

            if brightness_drop > INTENSITY_DROP_THRESHOLD:
                score += 0.5
                reasons.append("dark")
            if texture > TEXTURE_THRESHOLD:
                score += 0.3
                reasons.append("texture")
            if edge_density > EDGE_DENSITY_THRESHOLD:
                score += 0.2
                reasons.append("edge")

            detected = score >= 0.5
            result[zone_name] = detected
            if detected:
                result["has_obstacle"] = True

            # 标注
            color = (0, 0, 255) if detected else (0, 255, 0)
            cv2.rectangle(display, (x_start, ROI_TOP), (x_end, ROI_BOTTOM), color, 2)

            # 显示亮度值和判定原因
            info = "%s:b=%.0f t=%.1f e=%.2f" % (zone_name[0].upper(), mean_bright, texture, edge_density)
            cv2.putText(display, info, (x_start+5, ROI_TOP+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            status_text = "BLOCK" if detected else "OK"
            cv2.putText(display, status_text, (x_start+5, ROI_TOP+30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            zone_scores[zone_name] = {
                "brightness": mean_bright,
                "texture": texture,
                "edge_density": edge_density,
                "detected": detected,
            }

        # 显示FPS和总体状态
        status = "OBSTACLE!" if result["has_obstacle"] else "CLEAR"
        status_color = (0, 0, 255) if result["has_obstacle"] else (0, 255, 0)
        cv2.putText(display, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        directions = []
        for z in ["left", "center", "right"]:
            if result[z]: directions.append(z[0].upper())
        cv2.putText(display, "Blocked: " + (",".join(directions) if directions else "-"),
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.putText(display, "FPS: %.1f" % self.fps, (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return result, display, zone_scores

    def run_test(self, duration=10):
        """运行实时检测测试，保存带标注的图片"""
        print("运行障碍物检测测试 (%.1f秒)..." % duration)
        start_time = time.time()
        self.ref_brightness = None  # 重新校准
        frame_count = 0
        saved = False

        while time.time() - start_time < duration:
            ret, frame = self.cap.read()
            if not ret:
                continue

            frame_count += 1
            result, display, scores = self.detect(frame)

            if frame_count % 10 == 0:
                elapsed = time.time() - self.last_time
                self.fps = 10.0 / elapsed if elapsed > 0 else 0
                self.last_time = time.time()

            if not saved and frame_count > 10:  # 等校准完成后再保存
                output_path = "/home/yuxin/Dojetbot/obstacle_test.jpg"
                cv2.imwrite(output_path, display)
                print("  标注画面已保存: %s" % output_path)
                print("  检测结果: 左=%s 中=%s 右=%s" % (
                    result["left"], result["center"], result["right"]))
                for z in ["left", "center", "right"]:
                    s = scores[z]
                    print("    %s: b=%.1f t=%.1f e=%.3f" % (z, s["brightness"], s["texture"], s["edge_density"]))
                saved = True

            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                print("  [%.1fs] %s | L=%s C=%s R=%s | FPS=%.1f" % (
                    elapsed,
                    "OBSTACLE!" if result["has_obstacle"] else "CLEAR",
                    result["left"], result["center"], result["right"],
                    self.fps))

        print("测试结束, 共处理 %d 帧" % frame_count)
        return saved

    def cleanup(self):
        self.cap.release()
        print("摄像头已释放")


if __name__ == "__main__":
    import sys

    detector = ObstacleDetector()
    try:
        duration = float(sys.argv[1]) if len(sys.argv) > 1 else 10
        detector.run_test(duration)
    finally:
        detector.cleanup()
