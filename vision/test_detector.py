"""
Dojetbot YOLOv8 检测器离线测试 (本地运行)
验证检测逻辑是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from detector import Detector


def test_detector():
    """用一张空白图测试检测器初始化和基本流程"""
    print("=" * 50)
    print("Dojetbot YOLOv8n 检测器测试")
    print("=" * 50)

    # 初始化检测器
    print("\n[1/3] 初始化 YOLOv8n 检测器...")
    det = Detector(conf_thresh=0.5)
    print(f"  模型: {det.model.model_name}")
    print(f"  设备: {det.device}")

    # 生成测试帧
    print("\n[2/3] 生成测试画面 (640x480)...")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (100, 100, 100)  # 灰色背景

    # 画几个彩色方块模拟物体
    cv2.rectangle(frame, (100, 100), (200, 200), (0, 0, 200), -1)  # 红色方块
    cv2.rectangle(frame, (300, 150), (450, 350), (200, 0, 0), -1)  # 蓝色方块

    # 执行检测
    print("\n[3/3] 运行检测...")
    detections, elapsed = det.detect(frame)
    print(f"  检测到 {len(detections)} 个目标")
    print(f"  推理耗时: {elapsed*1000:.1f} ms")
    for label, conf, x1, y1, x2, y2 in detections:
        print(f"    {label}: {conf:.2f}  [{x1},{y1} -> {x2},{y2}]")

    # 绘制结果
    result = det.draw(frame, detections)
    out_path = "test_detector_result.jpg"
    cv2.imwrite(out_path, result)
    print(f"\n  结果已保存: {out_path}")

    print("\n测试完成!")
    return detections


if __name__ == "__main__":
    test_detector()
