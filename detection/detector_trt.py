"""TensorRT YOLOv8n 目标检测器 (GPU加速，支持80类COCO识别)
无需 pycuda — 使用 ctypes 直接调用 CUDA Driver API
"""
import os
import time
import ctypes
import numpy as np
import cv2
import tensorrt as trt

COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

# CUDA Runtime API (via ctypes) — works on Tegra, no pycuda needed
_cudart = ctypes.CDLL("libcudart.so")
_cudart.cudaFree(0)  # initialize

_cudart.cudaMalloc.restype = int
_cudart.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]
_cudart.cudaFree.restype = int
_cudart.cudaFree.argtypes = [ctypes.c_uint64]
_cudart.cudaMemcpy.restype = int
_cudart.cudaMemcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]

cudaMemcpyHostToDevice = 1
cudaMemcpyDeviceToHost = 2


def _malloc(size):
    ptr = ctypes.c_uint64()
    err = _cudart.cudaMalloc(ctypes.byref(ptr), size)
    if err != 0:
        raise RuntimeError(f"cudaMalloc failed: {err}")
    return ptr.value


def _free(ptr):
    _cudart.cudaFree(ptr)


def _htod(dst, src):
    _cudart.cudaMemcpy(dst, src.ctypes.data, src.nbytes, cudaMemcpyHostToDevice)


def _dtoh(dst, src):
    _cudart.cudaMemcpy(dst.ctypes.data, src, dst.nbytes, cudaMemcpyDeviceToHost)


class TRTDetector:
    """TensorRT YOLOv8n 检测器"""

    def __init__(self, engine_path, conf_thresh=0.5, iou_thresh=0.45):
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.fps = 0.0
        self._frame_count = 0
        self._fps_timer = time.time()

        print(f"[TRTDetector] 加载引擎: {engine_path}")
        with open(engine_path, "rb") as f:
            engine_data = f.read()

        runtime = trt.Runtime(TRT_LOGGER)
        self.engine = runtime.deserialize_cuda_engine(engine_data)
        self.context = self.engine.create_execution_context()

        self.input_shape = (1, 3, 640, 640)
        self.output_shape = (1, 84, 8400)

        self.input_size = 1 * 3 * 640 * 640 * 4
        self.output_size = 1 * 84 * 8400 * 4
        self.d_input = _malloc(self.input_size)
        self.d_output = _malloc(self.output_size)

        self.h_input = np.empty(1 * 3 * 640 * 640, dtype=np.float32)
        self.h_output = np.empty(1 * 84 * 8400, dtype=np.float32)

        print(f"[TRTDetector] YOLOv8n 就绪 | 输入 640x640 | 输出 84x8400")

    def detect(self, frame):
        h, w = frame.shape[:2]
        self._preprocess(frame, self.h_input)

        _htod(self.d_input, self.h_input)
        self.context.execute_v2([int(self.d_input), int(self.d_output)])
        _dtoh(self.h_output, self.d_output)

        detections = self._postprocess(self.h_output, w, h)

        self._frame_count += 1
        now = time.time()
        if now - self._fps_timer >= 2.0:
            self.fps = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

        return detections, 0.0

    def _preprocess(self, frame, dst):
        h, w = frame.shape[:2]
        scale = min(640 / w, 640 / h)
        nw, nh = int(w * scale), int(h * scale)
        dw, dh = (640 - nw) // 2, (640 - nh) // 2

        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
        canvas[dh:dh+nh, dw:dw+nw] = resized

        blob = canvas.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        dst[:] = blob.reshape(-1)

    def _postprocess(self, output, orig_w, orig_h):
        pred = output.reshape(84, 8400)
        box_data = pred[:4, :]
        cls_data = pred[4:, :]

        scores = np.max(cls_data, axis=0)
        class_ids = np.argmax(cls_data, axis=0)

        mask = scores > self.conf_thresh
        scores = scores[mask]
        class_ids = class_ids[mask]
        box_data = box_data[:, mask]

        if len(scores) == 0:
            return []

        scale = min(640 / orig_w, 640 / orig_h)
        pad_x = (640 - orig_w * scale) / 2
        pad_y = (640 - orig_h * scale) / 2

        cx = (box_data[0] - pad_x) / scale
        cy = (box_data[1] - pad_y) / scale
        bw = box_data[2] / scale
        bh = box_data[3] / scale

        x1 = np.clip(cx - bw / 2, 0, orig_w)
        y1 = np.clip(cy - bh / 2, 0, orig_h)
        x2 = np.clip(cx + bw / 2, 0, orig_w)
        y2 = np.clip(cy + bh / 2, 0, orig_h)

        keep = self._nms(x1, y1, x2, y2, scores)

        detections = []
        for idx in keep:
            label = COCO_NAMES[class_ids[idx]] if class_ids[idx] < 80 else "unknown"
            detections.append((
                label,
                float(scores[idx]),
                int(x1[idx]), int(y1[idx]),
                int(x2[idx]), int(y2[idx])
            ))
        return detections

    def _nms(self, x1, y1, x2, y2, scores):
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            if len(order) == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-10)
            order = order[1:][iou <= self.iou_thresh]
        return keep

    def draw(self, frame, detections):
        for label, conf, x1, y1, x2, y2 in detections:
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{label} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        cv2.putText(frame, f"YOLOv8n {self.fps:.1f} FPS",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 255, 255), 2)
        return frame

    def release(self):
        _free(self.d_input)
        _free(self.d_output)
