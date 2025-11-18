# This FastAPI server integrates motor control and IMU telemetry with a UI
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import serial, struct, sys, asyncio, datetime
import cv2
import os
import glob
import shutil
import subprocess
import re
from camera_control import camA_zoom_in,camB_zoom_in,camA_zoom_out,camB_zoom_out

app = FastAPI()
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

# Connect to Sabertooth motor controller. Information about the Sabertooth motor
# controller [Sabertooth 2x32](Sabertooth2x32.pdf)
try:
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
    print("Serial connection established with Sabertooth.")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit()

def send_packatized_command(address, command, value):
    try:
        checksum = (address + command + value) & 0x7F
        packet = bytes([address, command, value, checksum])
        ser.write(packet)
    except Exception as e:
        print(f"Error sending command: {e}")

class MotorControl(BaseModel):
    motor1_speed: int
    motor2_speed: int
    action: str



latest_control_input = {
    "timestamp": None,
    "action": None,
    "motor1_speed": 0,
    "motor2_speed": 0
}

#App.post("/control") receives motor control commands
#This endpoint expects a JSON payload with motor speeds and action
@app.post("/control")
async def control_motors(data: MotorControl):
    # Update the latest control input properly
    latest_control_input["timestamp"] = datetime.datetime.now().strftime('%H:%M:%S')
    latest_control_input["action"] = data.action
    latest_control_input["motor1_speed"] = data.motor1_speed
    latest_control_input["motor2_speed"] = data.motor2_speed

    if data.action == "forward":
        send_packatized_command(128, 1, data.motor1_speed)
        send_packatized_command(128, 5, data.motor2_speed)
    elif data.action == "reverse":
        send_packatized_command(128, 0, data.motor1_speed)
        send_packatized_command(128, 4, data.motor2_speed)
    elif data.action == "Turning Right":
        send_packatized_command(128, 1, data.motor1_speed)
        send_packatized_command(128, 4, data.motor2_speed)
    elif data.action == "Turning Left":
        send_packatized_command(128, 0, data.motor1_speed)
        send_packatized_command(128, 5, data.motor2_speed)
    elif data.action == "Take Picture": # Take picture uses openCV to capture a frame from the stream
        # Your streaming URL
        STREAM_URL = "rtsp://localhost:8554/webrtc/camB"  # Change cam depending on the camera you want to use
        # Create the inspection folder if it doesn't exist
        os.makedirs("inspection", exist_ok=True)
        # OpenCV capture from the stream
        cap = cv2.VideoCapture(STREAM_URL)
        if not cap.isOpened():
            print("Failed to open stream!")
        else:
            ret, frame = cap.read()
            if ret:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inspection/snapshot_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Snapshot saved: {filename}")
            else:
                print("Failed to grab frame!")
        cap.release()
        
    
    elif data.action == "Zoom In":
        camA_zoom_in()
    elif data.action == "Zoom Out":
        camA_zoom_out()
    
    else:
        send_packatized_command(128, 0, 0)
        send_packatized_command(128, 4, 0)
    return {"status": "Success", "message": "Data received"}

# Then update this endpoint accordingly:
@app.get("/input")
async def get_input():
    return JSONResponse(content={
        "timestamp": latest_control_input["timestamp"],
        "action": latest_control_input["action"],
        "motor1_speed": latest_control_input["motor1_speed"],
        "motor2_speed": latest_control_input["motor2_speed"]
    })
#------------------------------------------------------------------------------------------------------
#Above line is the endpoint for motor control
# app.get("/") serves the UI information 
@app.get("/")
async def get_ui():
    return FileResponse("ui/index.html")

#This data includes the timestamp and the input action
# app.get("/input") returns the latest control input data
@app.get("/input")
async def get_input():
     #Send exactly what the UI expects
    return JSONResponse(content={
        "timestamp": latest_control_input["timestamp"],
        "input": latest_control_input["input"]
    })
#------------------------------------------------------------------------------------------------------
#Below line is the Beginning for IMU telemetry
def checksum(data):
    return sum(data) & 0xFF

def parse_data(packet):
    if len(packet) < 11 or packet[0] != 0x55 or checksum(packet[:10]) != packet[10]:
        return None, None
    return packet[1], struct.unpack('<hhhh', packet[2:10])

def direction(yaw):
    dirs = ["North", "NE", "East", "SE", "South", "SW", "West", "NW"]
    return dirs[int((yaw + 22.5) % 360 // 45)]

def surface(pitch, roll):
    if abs(pitch) < 45 and abs(roll) < 45:
        return "Ceiling"
    elif abs(pitch) > 135 or abs(roll) > 135:
        return "Floor"
    return "Wall"

latest_imu_data = {
    "timestamp": None,
    "facing": "N/A",
    "surface": "N/A",
    "accel": None,
    "gyro": None
}
#app.get("/imu") returns the latest IMU data to the UI
#get fetch request for setting start position
@app.get("/imu")
async def get_imu():
    data = latest_imu_data.copy()
    data["input"] = latest_control_input.get("input")
    # Add debug info
    if not data.get("timestamp"):
        data["status"] = "No IMU data received yet"
    return JSONResponse(content=data)

# def imu_loop reads data from the IMU sensor and updates the latest IMU data

async def imu_loop():
    try:
        print("=" * 60)
        print("STARTING IMU LOOP")
        print("=" * 60)
        print("Attempting to open serial port /dev/ttyAMA2...")
        imu = serial.Serial("/dev/ttyAMA2", 115200, timeout=0.1)
        imu.flushInput()
        print("✅ IMU Serial connection established on /dev/ttyAMA2")
        print("Waiting for data packets...")
    except Exception as e:
        print("=" * 60)
        print(f"❌ Failed to open IMU serial port: {e}")
        print("=" * 60)
        return

    roll = pitch = yaw = 0.0
    accel = gyro = None

    try:
        while True:
            if imu.read(1) == b'\x55':
                packet = b'\x55' + imu.read(10)
                data_type, values = parse_data(packet)
                if not data_type:
                    continue
                #0x51 is the accelerometer data address
                if data_type == 0x51:
                    accel = tuple(v / 32768.0 * 16.0 for v in values[:3])

                #0x52 is the angular velocity data address
                elif data_type == 0x52:
                    gyro = tuple(v / 32768.0 * 2000.0 for v in values[:3])

                #0x53 is the Euler angles data address
                elif data_type == 0x53:
                    roll = values[0] / 32768.0 * 180.0
                    pitch = values[1] / 32768.0 * 180.0
                    yaw = values[2] / 32768.0 * 180.0

                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    facing = direction(yaw)
                    surf = surface(pitch, roll)

                    latest_imu_data.update({
                        "timestamp": timestamp,
                        "facing": facing,
                        "surface": surf,
                        "accel": accel,
                        "gyro": gyro
                    })
                    print(f"[{timestamp}] Facing: {facing} | Surface: {surf}")
            await asyncio.sleep(0)
    except Exception as e:
        print(f"IMU error: {e}")

# Recording management endpoints
@app.get("/recordings")
async def list_recordings():
    """List all available recordings"""
    try:
        recordings_dir = "./recordings"
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)
            return {"recordings": []}

        # Get all recording files
        recording_files = []
        for ext in ['*.mp4', '*.avi', '*.mkv', '*.webm', '*.ts']:
            recording_files.extend(glob.glob(os.path.join(recordings_dir, "**", ext), recursive=True))

        recordings = []
        for file_path in recording_files:
            file_stat = os.stat(file_path)
            recordings.append({
                "filename": os.path.basename(file_path),
                "path": file_path.replace("./recordings/", ""),
                "size": file_stat.st_size,
                "modified": datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "size_mb": round(file_stat.st_size / (1024 * 1024), 2)
            })

        # Sort by modification time (newest first)
        recordings.sort(key=lambda x: x['modified'], reverse=True)
        return {"recordings": recordings}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing recordings: {str(e)}")

@app.get("/recordings/download/{path:path}")
async def download_recording(path: str):
    """Download a specific recording file with optimized chunk size"""
    try:
        file_path = os.path.join("./recordings", path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording not found")

        # Get file size for Content-Length header
        file_size = os.path.getsize(file_path)

        def file_generator():
            with open(file_path, "rb") as file:
                # Increased chunk size from 8KB to 256KB for faster downloads
                while chunk := file.read(262144):  # 256KB chunks
                    yield chunk

        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}",
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes"
            }
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading recording: {str(e)}")

@app.head("/recordings/fast-download/{path:path}")
async def head_fast_download_recording(path: str):
    """HEAD request for file info to support parallel downloads"""
    try:
        file_path = os.path.join("./recordings", path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording not found")

        file_size = os.path.getsize(file_path)

        return JSONResponse(
            content=None,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Content-Type": "application/octet-stream",
                "Cache-Control": "public, max-age=3600"
            }
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting file info: {str(e)}")

@app.get("/recordings/fast-download/{path:path}")
async def fast_download_recording(path: str, request: Request):
    """Optimized download endpoint with range request support for faster downloads"""
    try:
        file_path = os.path.join("./recordings", path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording not found")

        file_size = os.path.getsize(file_path)

        # Check for range request
        range_header = request.headers.get('range')

        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1

            # Ensure valid range
            if start >= file_size or end >= file_size:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable")

            def range_generator():
                with open(file_path, "rb") as file:
                    file.seek(start)
                    remaining = end - start + 1
                    chunk_size = 524288  # 512KB chunks for range requests

                    while remaining > 0:
                        to_read = min(chunk_size, remaining)
                        chunk = file.read(to_read)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}",
                "Cache-Control": "public, max-age=3600"
            }

            return StreamingResponse(
                range_generator(),
                status_code=206,  # Partial Content
                media_type="application/octet-stream",
                headers=headers
            )
        else:
            # Regular full file download with optimizations
            def fast_file_generator():
                with open(file_path, "rb") as file:
                    # Use 512KB chunks for optimal performance
                    while chunk := file.read(524288):
                        yield chunk

            return StreamingResponse(
                fast_file_generator(),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}",
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=3600"
                }
            )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading recording: {str(e)}")

@app.delete("/recordings/{path:path}")
async def delete_recording(path: str):
    """Delete a specific recording file"""
    try:
        file_path = os.path.join("./recordings", path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording not found")

        os.remove(file_path)
        return {"message": f"Recording {path} deleted successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting recording: {str(e)}")

@app.get("/recordings/cleanup")
async def cleanup_old_recordings():
    """Delete recordings older than 7 days"""
    try:
        recordings_dir = "./recordings"
        if not os.path.exists(recordings_dir):
            return {"message": "No recordings directory found", "deleted": 0}

        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
        deleted_count = 0

        for root, dirs, files in os.walk(recordings_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) < cutoff_time.timestamp():
                    os.remove(file_path)
                    deleted_count += 1

        return {"message": f"Cleanup completed", "deleted": deleted_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

def get_wifi_signal_strength():
    """Get WiFi signal strength as a percentage (0-100)"""
    try:
        # Try using iw (more modern and reliable)
        result = subprocess.run(['iw', 'dev', 'wlan0', 'link'],
                              capture_output=True, text=True, timeout=2)

        if result.returncode == 0:
            # Look for signal strength in dBm
            match = re.search(r'signal:\s*(-?\d+)\s*dBm', result.stdout)
            if match:
                dbm = int(match.group(1))
                # Convert dBm to percentage (typical range: -90 to -30 dBm)
                # -30 dBm = 100%, -90 dBm = 0%
                percentage = min(100, max(0, 2 * (dbm + 100)))

                # Get SSID
                ssid_match = re.search(r'SSID:\s*(.+)', result.stdout)
                ssid = ssid_match.group(1).strip() if ssid_match else "Unknown"

                return {
                    "connected": True,
                    "signal_strength": percentage,
                    "signal_dbm": dbm,
                    "ssid": ssid
                }

        # Fallback to iwconfig
        result = subprocess.run(['iwconfig', 'wlan0'],
                              capture_output=True, text=True, timeout=2)

        if result.returncode == 0:
            # Look for Link Quality
            match = re.search(r'Link Quality=(\d+)/(\d+)', result.stdout)
            if match:
                quality = int(match.group(1))
                max_quality = int(match.group(2))
                percentage = int((quality / max_quality) * 100)

                # Get SSID
                ssid_match = re.search(r'ESSID:"(.+?)"', result.stdout)
                ssid = ssid_match.group(1) if ssid_match else "Unknown"

                return {
                    "connected": True,
                    "signal_strength": percentage,
                    "ssid": ssid
                }

        # Not connected or interface not found
        return {
            "connected": False,
            "signal_strength": 0,
            "ssid": None
        }

    except subprocess.TimeoutExpired:
        return {"connected": False, "signal_strength": 0, "ssid": None, "error": "Timeout"}
    except FileNotFoundError:
        # Commands not available (likely not on Linux)
        return {"connected": False, "signal_strength": 0, "ssid": None, "error": "WiFi tools not available"}
    except Exception as e:
        return {"connected": False, "signal_strength": 0, "ssid": None, "error": str(e)}

@app.get("/wifi")
async def get_wifi_status():
    """Get current WiFi connection status and signal strength"""
    return JSONResponse(content=get_wifi_signal_strength())

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(imu_loop())
