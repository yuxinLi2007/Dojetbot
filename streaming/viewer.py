"""
Dojetbot 远程画面查看器 (Windows 客户端)
用法:
  python viewer.py <小车IP>
  python viewer.py 10.1.41.174
"""
import sys
import cv2
import urllib.request
import numpy as np

STREAM_URL = "http://%s:%d/video_feed"
PORT = 5000


def run_viewer(host):
    url = STREAM_URL % (host, PORT)
    print("连接中: %s" % url)

    stream = urllib.request.urlopen(url)
    data = b""
    frame_count = 0
    fps = 0
    fps_timer = cv2.getTickCount()

    print("按 'q' 退出, 's' 保存截图")
    print("按 'y' 切换 YOLO, 'r' 重启连接")

    while True:
        chunk = stream.read(4096)
        if not chunk:
            break

        data += chunk
        # 查找 JPEG 帧边界
        a = data.find(b"\xff\xd8")
        b = data.find(b"\xff\xd9")

        if a != -1 and b != -1 and b > a:
            jpg = data[a:b + 2]
            data = data[b + 2:]

            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8),
                                 cv2.IMREAD_COLOR)
            if frame is not None:
                frame_count += 1
                now = cv2.getTickCount()
                dt = (now - fps_timer) / cv2.getTickFrequency()
                if dt >= 1.0:
                    fps = frame_count / dt
                    frame_count = 0
                    fps_timer = now

                cv2.putText(frame, "FPS: %.1f" % fps, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Host: %s" % host, (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                cv2.imshow("Dojetbot - " + host, frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    return
                elif key == ord("s"):
                    cv2.imwrite("dojetbot_screenshot.jpg", frame)
                    print("截图保存: dojetbot_screenshot.jpg")

    stream.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python viewer.py <小车IP地址>")
        print("示例: python viewer.py 10.1.41.174")
        sys.exit(1)

    try:
        run_viewer(sys.argv[1])
    except KeyboardInterrupt:
        print("\n退出")
    except Exception as e:
        print("错误: %s" % e)
        sys.exit(1)
