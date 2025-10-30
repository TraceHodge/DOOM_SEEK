# This FastAPI server integrates motor control and IMU telemetry with a UI
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import serial, struct, sys, asyncio, datetime
import board
import neopixel
import neopixel
import cv2
import os
import glob
import shutil
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

# Num_Pixels is the number of pixels in the LED strip
# The LED strip is connected to GPIO pin 24
# pixels is the object that controls the LED strip
NUM_PIXELS = 42    # Change this to match your LED count
PIXEL_PIN = board.D24   # Data line (GPIO 24)
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.7, auto_write=True)

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
        send_packatized_command(128, 0, data.motor1_speed)
        send_packatized_command(128, 4, data.motor2_speed)
    elif data.action == "reverse":
        send_packatized_command(128, 1, data.motor1_speed)
        send_packatized_command(128, 5, data.motor2_speed)
    elif data.action == "Turning Right":
        send_packatized_command(128, 0, data.motor1_speed)
        send_packatized_command(128, 5, data.motor2_speed)
    elif data.action == "Turning Left":
        send_packatized_command(128, 1, data.motor1_speed)
        send_packatized_command(128, 4, data.motor2_speed)
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
        
    elif data.action == "Led On":
        pixels.fill((255, 255, 255))  # White LED
    elif data.action == "Zoom In":
        camA_zoom_in()
    elif data.action == "Zoom Out":
        camA_zoom_out()
    elif data.action == "Led Off":
        pixels.fill((0, 0, 0))  # Turn off LED
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

# Wall labeling system - calibrated at startup
wall_calibration = {
    "reference_yaw": None,  # Yaw angle when starting at Wall A
    "reference_surface": None,  # Which surface type is Wall A
    "is_calibrated": False
}

def get_wall_label(yaw, current_surface):
    """
    Label walls as A, B, C, D based on starting position.
    Wall A = starting wall
    Wall B = 90° clockwise from A
    Wall C = opposite of A
    Wall D = 90° counter-clockwise from A
    """
    if not wall_calibration["is_calibrated"]:
        return "Calibrating..."

    # Only label actual walls, not floor/ceiling
    if current_surface not in ["Left Wall", "Right Wall", "Front Wall", "Back Wall"]:
        return current_surface

    # Calculate relative angle from starting position
    ref_yaw = wall_calibration["reference_yaw"]
    angle_diff = (yaw - ref_yaw) % 360

    # Determine which wall based on rotation
    # 0° = Wall A, 90° = Wall B, 180° = Wall C, 270° = Wall D
    if angle_diff < 45 or angle_diff >= 315:
        return "Wall A"
    elif 45 <= angle_diff < 135:
        return "Wall B"
    elif 135 <= angle_diff < 225:
        return "Wall C"
    else:
        return "Wall D"

def surface(pitch, roll, accel=None):
    """
    Enhanced surface detection using gravity vector from accelerometer.
    The accelerometer measures gravity direction - this tells us which surface we're on.

    Gravity components:
    - Z-axis negative (az < -0.7): Gravity pulling down → Floor
    - Z-axis positive (az > 0.7): Gravity pulling up → Ceiling
    - X-axis negative (ax < -0.7): Gravity pulling left → Left Wall
    - X-axis positive (ax > 0.7): Gravity pulling right → Right Wall
    - Y-axis negative (ay < -0.7): Gravity pulling forward → Front Wall
    - Y-axis positive (ay > 0.7): Gravity pulling backward → Back Wall
    """
    if accel:
        ax, ay, az = accel

        # Use accelerometer to detect gravity direction (most accurate)
        # Threshold of 0.7g means axis is within ~45° of vertical
        if abs(az) > 0.7:
            return "Floor" if az < 0 else "Ceiling"
        elif abs(ax) > 0.7:
            return "Left Wall" if ax < 0 else "Right Wall"
        elif abs(ay) > 0.7:
            return "Front Wall" if ay < 0 else "Back Wall"
        else:
            # Transitioning between surfaces or at an angle
            return "Transitioning"

    # Fallback to pitch/roll if no accelerometer data
    if abs(pitch) < 45 and abs(roll) < 45:
        return "Floor"
    elif abs(pitch) > 135 or abs(roll) > 135:
        return "Ceiling"
    return "Wall"

latest_imu_data = {
    "timestamp": None,
    "location": "N/A",  # Changed from "facing" - now shows Wall A/B/C/D or Floor/Ceiling
    "surface": "N/A",
    "accel": None,
    "gyro": None,
    "yaw": None  # Track raw yaw for debugging
}
#app.get("/imu") returns the latest IMU data to the UI
@app.get("/imu")
async def get_imu():
    data = latest_imu_data.copy()
    data["input"] = latest_control_input.get("input")
    return JSONResponse(content=data)

# def imu_loop reads data from the IMU sensor and updates the latest IMU data
async def imu_loop():
    try:
        print("Attempting to open serial port /dev/ttyAMA2...")
        imu = serial.Serial("/dev/ttyAMA2", 115200, timeout=0.1)
        imu.flushInput()
        print("IMU Serial connection established on /dev/ttyAMA2")
    except Exception as e:
        print(f"Failed to open IMU serial port: {e}")
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
                # ![](./docs/Acceleration0x51.png)
                if data_type == 0x51:
                    accel = tuple(v / 32768.0 * 16.0 for v in values[:3])

                #0x52 is the accelerometer data address
                # ![](./docs/AngularVelocity0x52.png)
                elif data_type == 0x52:
                    gyro = tuple(v / 32768.0 * 2000.0 for v in values[:3])

                #0x53 is the Euler angles data address
                # ![](./docs/Angle0x53.png)
                elif data_type == 0x53:
                    roll = values[0] / 32768.0 * 180.0
                    pitch = values[1] / 32768.0 * 180.0
                    yaw = values[2] / 32768.0 * 180.0

                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    surf = surface(pitch, roll, accel)  # Get surface type
                    location = get_wall_label(yaw, surf)  # Convert to Wall A/B/C/D

                    # Auto-calibrate on first wall detection
                    if not wall_calibration["is_calibrated"] and "Wall" in surf:
                        wall_calibration["reference_yaw"] = yaw
                        wall_calibration["reference_surface"] = surf
                        wall_calibration["is_calibrated"] = True
                        print(f"✓ Calibrated! Starting wall set as Wall A at yaw={yaw:.1f}°")

                    latest_imu_data.update({
                        "timestamp": timestamp,
                        "location": location,
                        "surface": surf,
                        "accel": accel,
                        "gyro": gyro,
                        "yaw": yaw
                    })
                    print(f"[{timestamp}] Location: {location} | Surface: {surf}")
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
    """Download a specific recording file"""
    try:
        file_path = os.path.join("./recordings", path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording not found")

        def file_generator():
            with open(file_path, "rb") as file:
                while chunk := file.read(8192):
                    yield chunk

        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(imu_loop())
