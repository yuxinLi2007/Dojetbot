"""Build TensorRT engine from YOLOv8n ONNX model"""
import tensorrt as trt
import numpy as np
import time, os

ONNX_PATH = os.path.expanduser("~/Dojetbot/detection/yolov8n.onnx")
ENGINE_PATH = os.path.expanduser("~/Dojetbot/detection/yolov8n.engine")

logger = trt.Logger(trt.Logger.WARNING)
builder = trt.Builder(logger)
network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
parser = trt.OnnxParser(network, logger)

print(f"Parsing ONNX: {ONNX_PATH}")
with open(ONNX_PATH, "rb") as f:
    if not parser.parse(f.read()):
        for i in range(parser.num_errors):
            err = parser.get_error(i)
            print(f"  Error {i}: {err}")
        exit(1)

print(f"Network: {network.num_layers} layers, {network.num_inputs} inputs, {network.num_outputs} outputs")

# Input info
for i in range(network.num_inputs):
    inp = network.get_input(i)
    print(f"  Input: {inp.name}, shape={inp.shape}, dtype={inp.dtype}")

# Output info
for i in range(network.num_outputs):
    out = network.get_output(i)
    print(f"  Output: {out.name}, shape={out.shape}, dtype={out.dtype}")

# Build config
config = builder.create_builder_config()
config.max_workspace_size = 1 << 30  # 1GB

# Set FP16 mode if supported
if builder.platform_has_fast_fp16:
    config.set_flag(trt.BuilderFlag.FP16)
    print("FP16 mode enabled")

print("Building engine (this takes a few minutes)...")
t0 = time.time()
plan = builder.build_serialized_network(network, config)
if plan is None:
    print("Engine build FAILED")
    exit(1)

with open(ENGINE_PATH, "wb") as f:
    f.write(plan)

t = time.time() - t0
print(f"Engine built in {t:.0f}s: {os.path.getsize(ENGINE_PATH) // 1024**2} MB -> {ENGINE_PATH}")
