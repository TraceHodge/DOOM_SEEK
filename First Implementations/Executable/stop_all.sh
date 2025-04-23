echo "Stopping all camera feeds and servers..."
pkill -f ffmpeg
pkill -f mediamtx
pkill -f "uvicorn main:app"
pkill -f "memory_monitor.sh"
rm -rf __pycache__
rm -f logs/*.log
echo " All Logs Cleared"
echo "All services stopped!"