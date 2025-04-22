#!/bin/bash

# Threshold in MB
THRESHOLD=600

while true; do
  USED=$(free -m | awk '/Mem:/ {print $3}')
  echo "Memory used: ${USED}MB"

  # Clean __pycache__ directories
  echo "Cleaning __pycache__..."
  find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null

  # Truncate IMU log to last 50 lines
  echo "Trimming imu.log to last 50 lines..."
  tail -n 50 logs/imu.log > logs/imu_trimmed.log && mv logs/imu_trimmed.log logs/imu.log

  # Remove images older than 10 minutes from inspection folder
  echo "Deleting inspection images older than 10 minutes..."
  find inspection -name "*.jpg" -mmin +10 -type f -delete 2>/dev/null

  # Alert on high memory, but do not restart the IMU server
  if [ "$USED" -gt "$THRESHOLD" ]; then
    echo "??  High memory usage detected: ${USED}MB. Consider manual intervention."
  fi

  sleep 60
done
