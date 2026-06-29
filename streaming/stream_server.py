"""
Dojetbot 摄像头实时流 + YOLO 物体识别服务器
用法:
  python3 stream_server.py              # 摄像头 + YOLO
  python3 stream_server.py --no-yolo    # 仅摄像头(无检测)
  python3 stream_server.py --download   # 仅下载模型
"""
import os
import sys
import time
import threading
import urllib.request
import numpy as np
import cv2
from flask import Flask, Response, render_template_string, request

# ==================== 配置 ====================
CAM_WIDTH = 640
CAM_HEIGHT = 480
CONFIDENCE = 0.5
NMS_THRESH = 0.4
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
JPEG_QUALITY = 80

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

YOLO_CFG = os.path.join(MODELS_DIR, "ssd_mobilenet_v2_coco.pbtxt")
YOLO_WEIGHTS = os.path.join(MODELS_DIR, "ssd_mobilenet_v2_coco.pb")
COCO_NAMES = os.path.join(MODELS_DIR, "coco.names")

YOLO_URLS = {
    YOLO_WEIGHTS: ("https://github.com/opencv/opencv_extra/raw/master/testdata/dnn/ssd_mobilenet_v2_coco.pb", None),
    YOLO_CFG: ("https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco.pbtxt", None),
    COCO_NAMES: ("https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/coco.names", None),
}

GST_PIPELINE = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width={w}, height={h}, framerate=30/1, format=NV12 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width={w}, height={h}, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
).format(w=CAM_WIDTH, h=CAM_HEIGHT)

# ==================== 模型下载 ====================
def download_models():
    """下载模型文件, 每个URL可以是: str 或 (str, dict)"""
    os.makedirs(MODELS_DIR, exist_ok=True)
    for path, spec in YOLO_URLS.items():
        name = os.path.basename(path)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print("  [OK] %s 已存在 (%d KB)" % (name, os.path.getsize(path) // 1024))
            continue

        if isinstance(spec, tuple):
            url, headers = spec
        else:
            url, headers = spec, None

        print("  [下载] %s ..." % name, end=" ", flush=True)
        try:
            req = urllib.request.Request(url)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=120) as r:
                with open(path, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            size = os.path.getsize(path)
            print("完成 (%d KB)" % (size // 1024))
            if size < 1000:
                print("  [警告] %s 太小 (%d 字节)" % (name, size))
        except Exception as e:
            print("失败: %s" % e)
            if os.path.exists(path):
                os.remove(path)


# ==================== 检测器 ====================
class Detector:
    """使用 Haar Cascade 面部检测 (内置, 无需下载)"""

    def __init__(self):
        cascade_path = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            cascade_path = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_alt2.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            print("[检测器] 加载失败")
        else:
            print("[检测器] 加载完成 (面部检测)")

    def detect(self, frame):
        """返回 (detections, 耗时秒)  detections: [(label, conf, x, y, w, h), ...]"""
        if self.face_cascade.empty():
            return [], 0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        t0 = time.time()
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
        elapsed = time.time() - t0

        results = [("face", 1.0, x, y, w, h) for (x, y, w, h) in faces]
        return results, elapsed


# ==================== 三线程架构 ====================
class DojetbotStream:
    """采集 / 检测 / 服务 三线程解耦"""

    def __init__(self, enable_yolo=True):
        self.enable_yolo = enable_yolo
        self.detector = Detector() if enable_yolo else None

        # 线程控制
        self.running = False

        # 原始帧 (采集线程 → 检测线程 / 服务线程)
        self._raw_lock = threading.Lock()
        self._raw_frame = None
        self._raw_count = 0

        # 检测结果 (检测线程 → 服务线程)
        self._detect_lock = threading.Lock()
        self._detect_results = []       # [(label, conf, x, y, w, h), ...]
        self._detect_fps = 0.0
        self._detect_last_raw_count = 0

        # 采集帧率统计
        self._cap_fps = 0.0
        self._cap_count = 0
        self._cap_timer = time.time()

        # 输出帧 (已叠加检测框)
        self._out_lock = threading.Lock()
        self._out_frame = None

        self.cap = None

    def start(self):
        print("[摄像头] 打开 CSI 摄像头...")
        self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("摄像头打开失败")

        self.running = True
        t_cap = threading.Thread(target=self._capture_loop, daemon=True,
                                 name="capture")
        t_det = threading.Thread(target=self._detect_loop, daemon=True,
                                 name="detect")
        t_out = threading.Thread(target=self._output_loop, daemon=True,
                                 name="output")
        t_cap.start()
        t_det.start()
        t_out.start()
        print("[摄像头] 已启动 (采集/检测/服务 三线程)")

    # ---------- 采集线程 ----------
    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.005)
                continue

            with self._raw_lock:
                self._raw_frame = frame.copy()
                self._raw_count += 1

            self._cap_count += 1
            now = time.time()
            if now - self._cap_timer >= 2.0:
                self._cap_fps = self._cap_count / (now - self._cap_timer)
                self._cap_count = 0
                self._cap_timer = now

    # ---------- 检测线程 ----------
    def _detect_loop(self):
        while self.running:
            if not self.detector:
                time.sleep(0.5)
                continue

            # 拿到最新原始帧
            with self._raw_lock:
                if self._raw_frame is None:
                    time.sleep(0.05)
                    continue
                frame = self._raw_frame.copy()
                raw_count = self._raw_count

            # 检测
            t0 = time.time()
            results, _ = self.detector.detect(frame)

            with self._detect_lock:
                self._detect_results = results
                self._detect_last_raw_count = raw_count

            # 控制检测频率: 约 2fps (避免 CPU 满载)
            elapsed = time.time() - t0
            sleep = max(0.02, 0.4 - elapsed)
            time.sleep(sleep)

    # ---------- 输出线程 (拼装) ----------
    def _output_loop(self):
        detect_count = 0
        dt_timer = time.time()

        while self.running:
            with self._raw_lock:
                if self._raw_frame is None:
                    time.sleep(0.03)
                    continue
                raw = self._raw_frame.copy()
                raw_count = self._raw_count

            # 取最新检测结果
            with self._detect_lock:
                results = list(self._detect_results)

            # 覆盖检测框到画面
            for label, conf, x, y, w, h in results:
                color = (0, 255, 0)
                cv2.rectangle(raw, (x, y), (x + w, y + h), color, 2)
                text = "%s %.0f%%" % (label, conf * 100)
                cv2.putText(raw, text, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # HUD
            if self.enable_yolo:
                detect_count += 1
                dt = time.time() - dt_timer
                if dt >= 2.0:
                    self._detect_fps = detect_count / dt
                    detect_count = 0
                    dt_timer = time.time()

                cv2.putText(raw, "YOLO %.1f fps" % self._detect_fps,
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            cv2.putText(raw, "CAM %.1f fps" % self._cap_fps,
                        (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

            # 编码输出
            ret_jpg, buf = cv2.imencode(".jpg", raw,
                                        [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if ret_jpg:
                with self._out_lock:
                    self._out_frame = buf.tobytes()

            # 目标输出 25fps 左右
            time.sleep(0.03)

    def get_frame(self):
        with self._out_lock:
            return self._out_frame

    @property
    def fps(self):
        return self._cap_fps

    def stop(self):
        self.running = False
        time.sleep(1)
        if self.cap:
            self.cap.release()
        print("[摄像头] 已停止")


# ==================== Flask Web 服务 ====================
app = Flask(__name__)
camera = None  # 在 main 中初始化

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dojetbot 实时画面</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a2e;color:#fff;font-family:sans-serif;text-align:center;padding:20px}
h1{margin:10px 0;font-size:1.5em;color:#00d4ff}
.video-wrap{display:inline-block;position:relative;border:2px solid #00d4ff;border-radius:8px;overflow:hidden;background:#000}
.video-wrap img{display:block;max-width:100%;height:auto}
.info{margin:15px 0;color:#aaa;font-size:0.9em}
.info span{color:#00d4ff}
.controls{margin:15px 0}
.controls a{display:inline-block;margin:0 10px;padding:8px 20px;border-radius:5px;text-decoration:none;font-size:0.9em}
.btn-yolo{background:#00d4ff;color:#1a1a2e}
.btn-noyolo{background:#555;color:#fff}
.footer{margin-top:20px;color:#555;font-size:0.8em}
</style>
</head>
<body>
<h1>Dojetbot 实时画面</h1>
<div class="video-wrap"><img src="/video_feed" id="stream"></div>
<div class="info">
  状态: <span id="status">加载中...</span> |
  分辨率: {{w}}x{{h}}
</div>
<div class="controls">
  <a href="/?yolo=1" class="btn-yolo">YOLO ON</a>
  <a href="/?yolo=0" class="btn-noyolo">YOLO OFF</a>
</div>
<div class="footer">Dojetbot Stream Server</div>
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
    yolo = request.args.get("yolo")
    if yolo is not None:
        camera.enable_yolo = (yolo == "1")
        if not camera.enable_yolo:
            camera.detector = None
        elif camera.detector is None:
            camera.detector = Detector()
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
    return {"status": "ok", "yolo": camera.enable_yolo, "fps": camera.fps}


# ==================== 主入口 ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dojetbot Streaming Server")
    parser.add_argument("--download", action="store_true",
                        help="仅下载模型文件")
    parser.add_argument("--no-yolo", action="store_true",
                        help="禁用 YOLO 识别")
    parser.add_argument("--port", type=int, default=FLASK_PORT,
                        help="端口 (默认 %d)" % FLASK_PORT)
    args = parser.parse_args()

    if args.download:
        print("下载 YOLO 模型文件...")
        download_models()
        sys.exit(0)

    if not args.no_yolo:
        if not os.path.exists(YOLO_CFG) or not os.path.exists(YOLO_WEIGHTS):
            print("[YOLO] 模型文件缺失，自动下载中...")
            download_models()

    camera = DojetbotStream(enable_yolo=not args.no_yolo)
    try:
        camera.start()
        print("\n============================================")
        print("  Dojetbot 流媒体服务器已启动")
        print("  远程地址: http://10.1.41.174:%d" % args.port)
        print("  YOLO: %s" % ("开启" if not args.no_yolo else "关闭"))
        print("============================================\n")
        app.run(host=FLASK_HOST, port=args.port, threaded=True)
    finally:
        camera.stop()
