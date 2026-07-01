"""Build TensorRT engine from YOLOv8n ONNX model
用法: python3 _trt_build.py

首次运行会自动下载 yolov8n.onnx (13MB)，然后构建 TensorRT 引擎。
"""
import os, sys, time, urllib.request, hashlib

# ==================== 下载配置 ====================
ONNX_EXPECTED_SIZE = 12851049  # 12.3 MB
ONNX_SHA256 = None  # 可选校验

ONNX_URLS = [
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx",
    "https://github.com/yuxinLi2007/Dojetbot/releases/download/v0.2.0/yolov8n.onnx",
]

ONNX_PATH = os.path.expanduser("~/Dojetbot/detection/yolov8n.onnx")
ENGINE_PATH = os.path.expanduser("~/Dojetbot/detection/yolov8n.engine")


def download_file(url, dest, expected_size=None):
    """下载文件并验证大小"""
    print(f"  下载: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest + ".tmp", "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        sys.stdout.write(f"\r    {pct}% ({downloaded // 1024**2}MB/{total // 1024**2}MB)")
                        sys.stdout.flush()
            print()
    except Exception as e:
        os.remove(dest + ".tmp")
        raise e

    size = os.path.getsize(dest + ".tmp")
    if expected_size and size != expected_size:
        os.remove(dest + ".tmp")
        raise ValueError(f"文件大小不匹配: 期望 {expected_size}, 实际 {size}")

    os.rename(dest + ".tmp", dest)
    print(f"  完成: {size // 1024**2} MB")


def ensure_onnx():
    """确保 yolov8n.onnx 存在，否则下载"""
    if os.path.exists(ONNX_PATH):
        size = os.path.getsize(ONNX_PATH)
        if ONNX_EXPECTED_SIZE and size == ONNX_EXPECTED_SIZE:
            print(f"[OK] yolov8n.onnx 已存在 ({size // 1024**2} MB)")
            return True
        print(f"[!] yolov8n.onnx 大小不匹配 ({size}), 重新下载...")
        os.remove(ONNX_PATH)
    else:
        print("[下载] yolov8n.onnx (13MB)...")

    for url in ONNX_URLS:
        try:
            download_file(url, ONNX_PATH, ONNX_EXPECTED_SIZE)
            print(f"[OK] yolov8n.onnx 下载成功!")
            return True
        except Exception as e:
            print(f"  FAIL: {e}")
            print(f"  尝试下一个源...\n")

    print("[错误] 所有下载源均失败!")
    print("请手动下载 yolov8n.onnx 放到 ~/Dojetbot/detection/ 目录:")
    print("  wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx")
    return False


# ==================== TensorRT 引擎构建 ====================
def build_engine():
    print("\n" + "=" * 50)
    print("  TensorRT YOLOv8n 引擎构建")
    print("=" * 50)

    import tensorrt as trt
    import numpy as np

    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)

    print(f"\n[1/4] 解析 ONNX: {ONNX_PATH}")
    with open(ONNX_PATH, "rb") as f:
        if not parser.parse(f.read()):
            for i in range(parser.num_errors):
                err = parser.get_error(i)
                print(f"  Error {i}: {err}")
            sys.exit(1)

    print(f"  网络: {network.num_layers} 层, {network.num_inputs} 输入, {network.num_outputs} 输出")
    for i in range(network.num_inputs):
        inp = network.get_input(i)
        print(f"  输入: {inp.name}, shape={inp.shape}")
    for i in range(network.num_outputs):
        out = network.get_output(i)
        print(f"  输出: {out.name}, shape={out.shape}")

    print(f"\n[2/4] 配置构建参数...")
    config = builder.create_builder_config()
    config.max_workspace_size = 1 << 30  # 1GB
    if builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
        print("  FP16 模式启用")

    print(f"\n[3/4] 构建引擎 (约5-10分钟)...")
    t0 = time.time()
    plan = builder.build_serialized_network(network, config)
    if plan is None:
        print("  引擎构建失败!")
        sys.exit(1)

    with open(ENGINE_PATH, "wb") as f:
        f.write(plan)

    t = time.time() - t0
    size_mb = os.path.getsize(ENGINE_PATH) // 1024**2
    print(f"\n[4/4] 完成! 耗时 {t:.0f}s, 引擎大小 {size_mb} MB")
    print(f"  输出: {ENGINE_PATH}")


if __name__ == "__main__":
    if ensure_onnx():
        build_engine()
    else:
        sys.exit(1)
