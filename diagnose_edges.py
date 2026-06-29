"""障碍物检测诊断 - 保存原始帧、边缘图、各通道分析"""
import cv2
import numpy as np

GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("Failed to open camera")
    exit(1)

# 读取5帧后取稳定的一帧
for _ in range(5):
    ret, frame = cap.read()

if not ret:
    print("Failed to read frame")
    exit(1)

cap.release()

# 保存原始帧
cv2.imwrite("/home/yuxin/Dojetbot/diag_raw.jpg", frame)

# 灰度图
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
cv2.imwrite("/home/yuxin/Dojetbot/diag_gray.jpg", gray)

# 尝试不同Canny阈值
for low, high, name in [(30, 90, "30_90"), (50, 150, "50_150"), (80, 200, "80_200")]:
    edges = cv2.Canny(gray, low, high)
    cv2.imwrite("/home/yuxin/Dojetbot/diag_edges_%s.jpg" % name, edges)
    edge_pct = np.count_nonzero(edges) / edges.size * 100
    print("Canny(%d,%d): edge pixels = %.2f%%" % (low, high, edge_pct))

# ROI区域分析 (y=200到480)
roi = gray[200:480, :]
print("\nROI (y=200:480) 均值: %.1f, 标准差: %.1f" % (roi.mean(), roi.std()))

# 分区分析
for zone_name, xs, xe in [("left", 0, 213), ("center", 213, 426), ("right", 426, 640)]:
    z = gray[200:480, xs:xe]
    print("%s zone: mean=%.1f, std=%.1f" % (zone_name, z.mean(), z.std()))

# 保存带有中间处理结果的大图
h, w = frame.shape[:2]
big = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
big[0:h, 0:w] = frame
gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
big[0:h, w:w*2] = cv2.resize(gray3, (w, h))
edges_best = cv2.Canny(gray, 30, 90)
edges3 = cv2.cvtColor(edges_best, cv2.COLOR_GRAY2BGR)
big[h:h*2, 0:w] = cv2.resize(edges3, (w, h))

# 在原始帧上画ROI
frame_roi = frame.copy()
cv2.rectangle(frame_roi, (0, 200), (640, 480), (0, 255, 255), 2)
cv2.line(frame_roi, (213, 200), (213, 480), (0, 255, 0), 1)
cv2.line(frame_roi, (426, 200), (426, 480), (0, 255, 0), 1)
big[h:h*2, w:w*2] = cv2.resize(frame_roi, (w, h))

cv2.imwrite("/home/yuxin/Dojetbot/diag_montage.jpg", big)
print("\n诊断图像已保存到 /home/yuxin/Dojetbot/diag_*.jpg")
