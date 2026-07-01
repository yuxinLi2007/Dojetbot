"""测试: 摄像头 + YOLOv3-tiny 模型加载"""
import sys

def test_camera():
    import cv2
    W, H = 320, 240
    cap = cv2.VideoCapture(
        f"nvarguscamerasrc ! video/x-raw(memory:NVMM), width={W}, height={H}, "
        f"framerate=30/1, format=NV12 ! nvvidconv flip-method=0 ! "
        f"video/x-raw, width={W}, height={H}, format=BGRx ! "
        f"videoconvert ! video/x-raw, format=BGR ! appsink drop=1",
        cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("FAIL: 摄像头打开失败")
        return False
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        print("FAIL: 摄像头读取失败")
        return False
    print("OK: 摄像头工作正常 (%dx%d)" % (frame.shape[1], frame.shape[0]))
    return True

def test_model():
    import cv2, numpy as np
    MODEL_DIR = "/home/yuxin/Dojetbot/detection"
    try:
        net = cv2.dnn.readNetFromDarknet(
            "%s/yolov3-tiny.cfg" % MODEL_DIR,
            "%s/yolov3-tiny.weights" % MODEL_DIR)
        names = net.getUnconnectedOutLayersNames()
        print("OK: YOLOv3-tiny 加载成功 (%d layers, %d outputs)" % (
            len(net.getLayerNames()), len(names)))
        return True
    except Exception as e:
        print("FAIL: 模型加载失败 - %s" % str(e))
        return False

if __name__ == "__main__":
    ok = True
    print("=== Dojetbot 环境测试 ===\n")
    ok &= test_camera()
    ok &= test_model()
    msg = "=== 全部通过 ===" if ok else "=== 有测试失败 ==="
    print("\n%s" % msg)
    sys.exit(0 if ok else 1)
