from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import serial
import struct
import datetime

app = FastAPI()

# Serve UI
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
async def get_ui():
    return FileResponse("ui/index.html")

def checksum(data):
    return sum(data) & 0xFF

def parse_data(packet):
    if len(packet) < 11 or packet[0] != 0x55 or checksum(packet[:10]) != packet[10]:
        return None, None
    data_type = packet[1]
    values = struct.unpack('<hhhh', packet[2:10])
    return data_type, values

def direction(yaw):
    dirs = ["North", "NE", "East", "SE", "South", "SW", "West", "NW"]
    idx = int((yaw + 22.5) % 360 // 45)
    return dirs[idx]

def surface(pitch, roll):
    if abs(pitch) < 45 and abs(roll) < 45:
        return "Floor"
    elif abs(pitch) > 135 or abs(roll) > 135:
        return "Ceiling"
    else:
        return "Wall"

latest_imu_data = {
    "timestamp": None,
    "facing": "N/A",
    "surface": "N/A",
    "accel": None,
    "gyro": None
}

@app.get("/imu")
async def get_imu():
    return JSONResponse(content=latest_imu_data)

async def imu_loop():
    try:
        print("Attempting to open serial port /dev/ttyAMA2...")
        ser = serial.Serial("/dev/ttyAMA2", 115200, timeout=0.1)
        ser.flushInput()
        print("? IMU Serial connection established on /dev/ttyAMA2")
    except Exception as e:
        print(f"? Failed to open IMU serial port: {e}")
        return

    roll = pitch = yaw = 0.0
    accel = gyro = None

    try:
        while True:
            if ser.read(1) == b'\x55':
                packet = b'\x55' + ser.read(10)
                data_type, values = parse_data(packet)
                if data_type is None:
                    continue

                if data_type == 0x51:
                    ax = values[0] / 32768.0 * 16.0
                    ay = values[1] / 32768.0 * 16.0
                    az = values[2] / 32768.0 * 16.0
                    accel = (ax, ay, az)

                elif data_type == 0x52:
                    gx = values[0] / 32768.0 * 2000.0
                    gy = values[1] / 32768.0 * 2000.0
                    gz = values[2] / 32768.0 * 2000.0
                    gyro = (gx, gy, gz)

                elif data_type == 0x53:
                    roll = values[0] / 32768.0 * 180.0
                    pitch = values[1] / 32768.0 * 180.0
                    yaw = values[2] / 32768.0 * 180.0

                    facing = direction(yaw)
                    surf = surface(pitch, roll)
                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    latest_imu_data.update({
                        "timestamp": timestamp,
                        "facing": facing,
                        "surface": surf,
                        "accel": accel,
                        "gyro": gyro
                    })
                    print(f"[{timestamp}] Facing: {facing} | Surface: {surf}")

            await asyncio.sleep(0)  # No delay, just yield
    except Exception as e:
        print(f"? IMU error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(imu_loop())
