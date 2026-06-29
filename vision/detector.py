"""
目标检测器 — 传统计算机视觉 (边缘检测 + 轮廓分析)
无需 DNN 模型，在所有 OpenCV 版本上均可运行
"""
import time
import numpy as np
import cv2


class Detector:
    """CV-based 目标检测: 自适应阈值 → 形态学 → 轮廓过滤 → NMS"""

    def __init__(self, conf_thresh=0.3, min_area_ratio=0.002, max_area_ratio=0.8):
        self.conf_thresh = conf_thresh
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.fps = 0.0
        self.input_size = (0, 0)
        self._frame_count = 0
        self._fps_timer = time.time()
        print("[Detector] CV-based 检测器已初始化")

    def detect(self, frame):
        h, w = frame.shape[:2]
        min_area = self.min_area_ratio * w * h
        max_area = self.max_area_ratio * w * h

        # 灰度 + 降噪
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 自适应阈值分割 (适应不同光照)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2)

        # 形态学: 开运算去噪 + 闭运算连接断裂边缘
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=2)

        # 查找轮廓
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            perimeter = cv2.arcLength(cnt, True)
            if perimeter < 1:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)

            # 宽高比过滤
            aspect_ratio = bw / bh if bh > 0 else 0
            if aspect_ratio < 0.15 or aspect_ratio > 6:
                continue

            # 填充率 (solidity) 作为置信度
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            conf = min(solidity, 0.99)

            if conf < self.conf_thresh:
                continue

            detections.append(("object", conf, x, y, x + bw, y + bh))

        # NMS 合并重叠框
        detections = self._nms(detections, 0.4)

        # FPS 统计
        self._frame_count += 1
        now = time.time()
        if now - self._fps_timer >= 2.0:
            self.fps = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

        return detections, 0.0

    def _nms(self, detections, overlap_thresh):
        if len(detections) < 2:
            return detections
        boxes = np.array([[d[2], d[3], d[4] - d[2], d[5] - d[3]]
                          for d in detections], dtype=np.float32)
        confs = np.array([d[1] for d in detections], dtype=np.float32)
        idx = cv2.dnn.NMSBoxes(boxes.tolist(), confs.tolist(),
                               0.0, overlap_thresh)
        if len(idx) > 0:
            idx = idx.flatten()
            return [detections[i] for i in idx]
        return []

    def draw(self, frame, detections, extra_lines=None):
        """绘制检测框 + HUD"""
        for label, conf, x1, y1, x2, y2 in detections:
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{label} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                          0.5, 2)
            cv2.rectangle(frame, (x1, y1 - th - 6),
                          (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        cv2.putText(frame, f"Detect {self.fps:.1f} FPS",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 255, 255), 2)
        if extra_lines:
            for i, line in enumerate(extra_lines):
                cv2.putText(frame, line, (10, 70 + i * 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (0, 255, 255), 1)
        return frame

    def set_input_size(self, w, h):
        pass  # CV-based, 不使用推理分辨率

    def auto_tune(self):
        return False
