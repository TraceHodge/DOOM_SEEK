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
ffmpeg -f v4l2 -input_format mjpeg -framerate 30 -video_size 1920x1080 \
-i /dev/video0 \
-vcodec libx264 -preset ultrafast -tune zerolatency -crf 18 \
-b:v 1M -maxrate 2M -bufsize 4M \
-g 30 -keyint_min 30 \
-f rtsp rtsp://localhost:8554/webrtc/camA \
> logs/camA.log 2>&1 &


# Stream Camera B
echo "Starting Camera B Stream..."
ffmpeg -f v4l2 -input_format mjpeg -framerate 30 -video_size 1920x1080 \
-i /dev/video2 \
-vcodec libx264 -preset ultrafast -tune zerolatency -crf 18 \
-b:v 1M -maxrate 2M -bufsize 4M \
-g 30 -keyint_min 30 \
-f rtsp rtsp://localhost:8554/webrtc/camB \
> logs/camB.log 2>&1 &



sleep 2
echo "Starting Memory Control"
./memory_monitor.sh > logs/memory.log 2>&1 &

echo "All services started! Access UI at: http://192.168.1.2:8000"
echo "Type ./stop_all.sh to End All Streams"
