#!/bin/bash

# Run MediaMTX
echo "Starting MediaMTX..."
./mediamtx > logs/mediamtx.log 2>&1 &

# Wait a bit to let MediaMTX boot up
sleep 2

echo "Starting Server port 8000" 
uvicorn main:app --host 0.0.0.0 --port 8000 > logs/motor_server.log 2>&1 &

python3 camera_control.py > logs/camA.log 2>&1 &



sleep 2
echo "Starting Memory Control"
./memory_monitor.sh > logs/memory.log 2>&1 &

echo "All services started! Access UI at: http://192.168.1.2:8000"
echo "Type ./stop_all.sh to End All Streams"
