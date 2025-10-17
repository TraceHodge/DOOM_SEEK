import subprocess
import os

# Track zoom values for each camera
cam_zoom = {
    "camA": 0,
    "camB": 0
}

# Start Camera B
def start_camB():
    cmd = (
       "ffmpeg -f v4l2 -input_format h264 -framerate 30 -video_size 1920x1080 "
        "-i /dev/video2 "
        "-c:v copy -an "
        "-b:v 10M -maxrate 20M -bufsize 4M "
        "-f rtsp rtsp://localhost:8554/webrtc/camB "
        "> logs/camB.log 2>&1 &"
    )
    os.system(cmd)
    print("Camera B started")

# Start Camera A
def start_camA():
    cmd = (
        "ffmpeg -f v4l2 -input_format h264 -framerate 30 -video_size 1920x1080 "
        "-i /dev/video0 "
        "-c:v copy -an "
        "-b:v 10M -maxrate 20M -bufsize 4M "
        "-f rtsp rtsp://localhost:8554/webrtc/camA "
        "> logs/camA.log 2>&1 &"
    )
    os.system(cmd)
    print("Camera A started")

# Zoom In for Camera A
def camA_zoom_in():
    if cam_zoom["camA"] < 50:  # max = 50
        cam_zoom["camA"] += 5
        subprocess.run(["v4l2-ctl", "-d", "/dev/video0", "-c", f"zoom_absolute={cam_zoom['camA']}"])
        print(f"Camera A zoom set to {cam_zoom['camA']}")

# Zoom Out for Camera A
def camA_zoom_out():
    if cam_zoom["camA"] > 0:  # min = 0
        cam_zoom["camA"] -= 5
        subprocess.run(["v4l2-ctl", "-d", "/dev/video0", "-c", f"zoom_absolute={cam_zoom['camA']}"])
        print(f"Camera A zoom set to {cam_zoom['camA']}")

# Zoom In for Camera B
def camB_zoom_in():
    if cam_zoom["camB"] < 50:
        cam_zoom["camB"] += 5
        subprocess.run(["v4l2-ctl", "-d", "/dev/video2", "-c", f"zoom_absolute={cam_zoom['camB']}"])
        print(f"Camera B zoom set to {cam_zoom['camB']}")

# Zoom Out for Camera B
def camB_zoom_out():
    if cam_zoom["camB"] > 0:
        cam_zoom["camB"] -= 5
        subprocess.run(["v4l2-ctl", "-d", "/dev/video2", "-c", f"zoom_absolute={cam_zoom['camB']}"])
        print(f"Camera B zoom set to {cam_zoom['camB']}")

# Start both cameras when script runs
if __name__ == "__main__":
    start_camA()
    start_camB()
