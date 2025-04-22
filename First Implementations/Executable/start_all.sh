#!/bin/bash

# Run MediaMTX
echo "Starting MediaMTX..."
./mediamtx > logs/mediamtx.log 2>&1 &

# Wait a bit to let MediaMTX boot up
sleep 2

echo "Starting Server port 8000" 
uvicorn main:app --host 0.0.0.0 --port 8000 > logs/motor_server.log 2>&1 &

# Stream Camera A
echo "Starting Camera A Stream..."
ffmpeg -f v4l2 -input_format mjpeg -framerate 30 -video_size 960x540 \
-i /dev/video0 \
-vcodec libx264 -preset ultrafast -tune zerolatency -crf 21 \
-b:v 1M -maxrate 1M -bufsize 2M \
-g 30 -keyint_min 30 \
-f rtsp rtsp://localhost:8554/webrtc/camA \
> logs/camA.log 2>&1 &


# Stream Camera B
echo "Starting Camera B Stream..."
ffmpeg -f v4l2 -input_format yuyv422 -framerate 30 -video_size 640x480 \
-i /dev/video2 \
-vcodec libx264 -preset ultrafast -tune zerolatency -crf 20 \
-b:v 900k -maxrate 900k -bufsize 1800k \
-g 30 -keyint_min 30 \
-f rtsp rtsp://localhost:8554/webrtc/camB \
> logs/camB.log 2>&1 &



sleep 2
echo "Starting Memory Control"
./memory_monitor.sh > logs/memory.log 2>&1 &

echo "All services started! Access UI at: http://<your-pi-ip>:8081"
echo "Type ./stop_all.sh to End All Streams"
