"""
Dojetbot YOLOv3-tiny 实时检测串流 (MVP)
用法: python3 app.py
"""
import time, cv2, numpy as np
from flask import Flask, Response

W, H, CONF, NMS = 320, 240, 0.5, 0.45
MODEL_DIR = "/home/yuxin/Dojetbot/detection"

# 加载 YOLOv3-tiny
net = cv2.dnn.readNetFromDarknet(
    f"{MODEL_DIR}/yolov3-tiny.cfg", f"{MODEL_DIR}/yolov3-tiny.weights")
layer_names = net.getUnconnectedOutLayersNames()
with open(f"{MODEL_DIR}/coco.names") as f:
    classes = [line.strip() for line in f]
print(f"[YOLO] YOLOv3-tiny loaded ({len(classes)} classes)")

# 摄像头
cap = cv2.VideoCapture(
    f"nvarguscamerasrc ! video/x-raw(memory:NVMM), width={W}, height={H}, "
    f"framerate=30/1, format=NV12 ! nvvidconv flip-method=0 ! "
    f"video/x-raw, width={W}, height={H}, format=BGRx ! "
    f"videoconvert ! video/x-raw, format=BGR ! appsink drop=1",
    cv2.CAP_GSTREAMER)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)

def detect(frame):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1/255, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(layer_names)
    boxes, scores, labels = [], [], []
    for out in outs:
        for det in out[0]:
            pts = det[5:]
            class_id = np.argmax(pts)
            conf = float(pts[class_id] * det[4])
            if conf < CONF:
                continue
            cx, cy, bw, bh = det[:4] * np.array([w, h, w, h])
            x = int(cx - bw / 2)
            y = int(cy - bh / 2)
            boxes.append([x, y, int(bw), int(bh)])
            scores.append(conf)
            labels.append(class_id)
    if boxes:
        idx = cv2.dnn.NMSBoxes(boxes, scores, CONF, NMS)
        if len(idx) > 0:
            idx = idx.flatten()
            for i in idx:
                x, y, bw, bh = boxes[i]
                text = f"{classes[labels[i]]} {scores[i]:.2f}"
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

app = Flask(__name__)

@app.route("/video_feed")
def video_feed():
    def gen():
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue
            detect(frame)
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/")
def index():
    return f'<img src="/video_feed" style="max-width:100%"><p>Dojetbot YOLOv3-tiny {W}x{H}</p>'

@app.route("/health")
def health():
    return {"status": "ok", "model": "yolov3-tiny"}

print(f"\n=== Dojetbot YOLO 串流服务 ===\n  http://10.1.41.174:5000\n================================")
app.run(host="0.0.0.0", port=5000, threaded=True)
