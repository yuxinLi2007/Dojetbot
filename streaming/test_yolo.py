"""
YOLO 识别测试: 拍一张照片 → YOLO检测 → 保存结果
"""
import os
import sys
import time
import cv2
import numpy as np

# 复用 stream_server.py 的模块
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from stream_server import YOLODetector, GST_PIPELINE, CAM_WIDTH, CAM_HEIGHT

print("=" * 50)
print("Dojetbot YOLO 识别测试")
print("=" * 50)

# 1. 打开摄像头
print("\n[1/4] 打开摄像头...")
cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("ERROR: 摄像头打开失败")
    sys.exit(1)

# 2. 等待摄像头稳定
print("[2/4] 等待摄像头稳定...")
for i in range(10):
    cap.read()
    time.sleep(0.1)

# 3. 拍照
print("[3/4] 拍照中...")
ret, frame = cap.read()
if not ret:
    print("ERROR: 拍照失败")
    cap.release()
    sys.exit(1)

raw_path = os.path.join(BASE, "test_raw.jpg")
cv2.imwrite(raw_path, frame)
print("  原始照片保存: %s (%d KB)" % (raw_path, os.path.getsize(raw_path) // 1024))

# 4. YOLO 检测
print("[4/4] YOLO 检测...")
detector = YOLODetector()
if detector.net is None:
    print("ERROR: YOLO 模型加载失败")
    cap.release()
    sys.exit(1)

t0 = time.time()
results, elapsed = detector.detect(frame)
cap.release()

print("\n  检测耗时: %.2f 秒" % elapsed)
print("  检测到 %d 个物体:\n" % len(results))

if results:
    for label, conf, x, y, w, h in results:
        print("    - %s (%.1f%%)  [x=%d y=%d w=%d h=%d]" % (label, conf * 100, x, y, w, h))
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "%s %.0f%%" % (label, conf * 100),
                    (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
else:
    print("    (无检测结果 — 摄像头前可能没有可识别的物体)")
    cv2.putText(frame, "No objects detected", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

# 保存结果
result_path = os.path.join(BASE, "test_result.jpg")
cv2.imwrite(result_path, frame)
print("\n  检测结果图: %s (%d KB)" % (result_path, os.path.getsize(result_path) // 1024))
print("=" * 50)
