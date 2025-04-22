echo "Stopping all camera feeds and servers..."
pkill -f ffmpeg
pkill -f mediamtx
#pkill -f "uvicorn serverIMU:app"
#pkill -f "uvicorn serverControls:app"
pkill -f "uvicorn main:app"
pkill -f "memory_monitor.sh"
rm -rf __pycache__
echo "All streams stopped"
echo "Clearing Logs"
rm -f logs/*.log
echo " All Logs Cleared"
