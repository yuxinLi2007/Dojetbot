"""
Dojetbot TensorRT YOLOv8n 实时目标检测串流服务器
用法:
  python3 app_trt.py              # 正常启动
  python3 app_trt.py --no-yolo    # 仅摄像头(无检测)
"""
import os, sys, time, threading
import cv2, numpy as np
from flask import Flask, Response, render_template_string, request

from detector_trt import TRTDetector

# ==================== 配置 ====================
CAM_WIDTH = 640
CAM_HEIGHT = 480
CONFIDENCE = 0.5
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
JPEG_QUALITY = 80
ENGINE_PATH = os.path.expanduser("~/Dojetbot/detection/yolov8n.engine")

GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width={w}, height={h}, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width={w}, height={h}, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
).format(w=CAM_WIDTH, h=CAM_HEIGHT)


class Camera:
    """三线程: 采集 / 检测 / 输出 分离"""

    def __init__(self, enable_yolo=True):
        self.enable_yolo = enable_yolo
        self.detector = None
        if enable_yolo:
            self.detector = TRTDetector(ENGINE_PATH, conf_thresh=CONFIDENCE)

        self.running = False
        self.cap = None

        self._frame_lock = threading.Lock()
        self._frame = None

        self._det_lock = threading.Lock()
        self._detections = []
        self._detect_fps = 0.0

        self._out_lock = threading.Lock()
        self._out_frame = None

    def start(self):
        print("[摄像头] 打开 CSI 摄像头...")
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("摄像头打开失败")

        self.running = True
        for target in [self._capture_loop, self._detect_loop, self._output_loop]:
            t = threading.Thread(target=target, daemon=True)
            t.start()
        print("[摄像头] 已启动 (三线程)")
        return self

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.005)
                continue
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            with self._frame_lock:
                self._frame = frame.copy()

    def _detect_loop(self):
        while self.running:
            try:
                with self._frame_lock:
                    if self._frame is None:
                        time.sleep(0.05)
                        continue
                    frame = self._frame.copy()

                if not self.enable_yolo or not self.detector:
                    time.sleep(0.1)
                    continue

                detections, _ = self.detector.detect(frame)
                with self._det_lock:
                    self._detections = detections
                    self._detect_fps = self.detector.fps

                time.sleep(0.01)
            except Exception as e:
                print(f"[错误] detect_loop: {e}")
                time.sleep(0.5)

    def _output_loop(self):
        while self.running:
            try:
                with self._frame_lock:
                    if self._frame is None:
                        time.sleep(0.03)
                        continue
                    frame = self._frame.copy()

                with self._det_lock:
                    detections = list(self._detections)
                    detect_fps_val = self._detect_fps

                if self.enable_yolo and self.detector:
                    frame = self.detector.draw(frame, detections)
                else:
                    cv2.putText(frame, "DETECT OFF",
                                (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                                0.55, (0, 255, 255), 2)

                ret_jpg, buf = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                if ret_jpg:
                    with self._out_lock:
                        self._out_frame = buf.tobytes()

            except Exception as e:
                print(f"[错误] output_loop: {e}")
                time.sleep(0.1)

            time.sleep(0.03)

    def get_frame(self):
        with self._out_lock:
            return self._out_frame

    def stop(self):
        self.running = False
        time.sleep(0.5)
        if self.cap:
            self.cap.release()
        if self.detector:
            self.detector.release()
        print("[摄像头] 已停止")


# ==================== Flask Web ====================
app = Flask(__name__)
camera = None

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dojetbot YOLOv8n 实时检测</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a2e;color:#fff;font-family:sans-serif;text-align:center;padding:20px}
h1{margin:10px 0;font-size:1.5em;color:#00d4ff}
h1 span{font-size:0.6em;color:#888}
.video-wrap{display:inline-block;position:relative;border:2px solid #00d4ff;border-radius:8px;overflow:hidden;background:#000}
.video-wrap img{display:block;max-width:100%;height:auto}
.info{margin:15px 0;color:#aaa;font-size:0.9em}
.info span{color:#00d4ff}
.controls{margin:15px 0}
.controls a{display:inline-block;margin:0 10px;padding:8px 20px;border-radius:5px;text-decoration:none;font-size:0.9em}
.btn-on{background:#00d4ff;color:#1a1a2e}
.btn-off{background:#555;color:#fff}
.footer{margin-top:20px;color:#555;font-size:0.8em}
</style>
</head>
<body>
<h1>Dojetbot YOLOv8n <span>80类目标检测</span></h1>
<div class="video-wrap"><img src="/video_feed" id="stream"></div>
<div class="info">
  状态: <span id="status">加载中...</span> |
  分辨率: {{w}}x{{h}}
</div>
<div class="controls">
  <a href="/?yolo=1" class="btn-on">DETECT ON</a>
  <a href="/?yolo=0" class="btn-off">DETECT OFF</a>
</div>
<div class="footer">Dojetbot | TensorRT YOLOv8n | GPU加速</div>
<script>
function checkStream(){
  var s=document.getElementById('status');
  var i=document.getElementById('stream');
  if(i.complete&&i.naturalWidth>0){s.textContent='运行中';s.style.color='#0f0'}
  else{s.textContent='等待画面...';s.style.color='#ff0'}
}
setInterval(checkStream,2000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    global camera
    yolo_flag = request.args.get("yolo")
    if yolo_flag is not None:
        camera.enable_yolo = (yolo_flag == "1")
        if camera.enable_yolo and camera.detector is None:
            camera.detector = TRTDetector(ENGINE_PATH, conf_thresh=CONFIDENCE)
        elif not camera.enable_yolo:
            camera.detector = None
    return render_template_string(HTML_PAGE, w=CAM_WIDTH, h=CAM_HEIGHT)


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                   frame + b"\r\n")
            time.sleep(0.01)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/health")
def health():
    yolo_on = camera.enable_yolo and camera.detector is not None
    return {
        "status": "ok",
        "detect": yolo_on,
        "model": "yolov8n-tensorrt",
        "fps": camera.detector.fps if yolo_on else 0.0,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dojetbot YOLOv8n Stream")
    parser.add_argument("--no-yolo", action="store_true", help="禁用检测")
    parser.add_argument("--port", type=int, default=FLASK_PORT,
                        help=f"端口 (默认 {FLASK_PORT})")
    args = parser.parse_args()

    camera = Camera(enable_yolo=not args.no_yolo)
    try:
        camera.start()
        print()
        print("=" * 50)
        print("  Dojetbot 流媒体服务器已启动")
        print(f"  地址: http://10.1.41.174:{args.port}")
        print(f"  检测: {'YOLOv8n (TensorRT GPU)' if not args.no_yolo else '关闭'}")
        print("=" * 50)
        print()
        app.run(host=FLASK_HOST, port=args.port, threaded=True)
    finally:
        camera.stop()
