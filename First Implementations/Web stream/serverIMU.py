import asyncio
import struct
import serial
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

app.mount("/ui", StaticFiles(directory="ui"), name="ui")
# Add this to serve logs directory
app.mount("/logs", StaticFiles(directory="logs"), name="logs")

@app.get("/")
async def get_ui():
    return HTMLResponse(open("ui/index.html").read())


# IMU Functions
def checksum(data):
    return sum(data) & 0xFF

def parse_data(packet):
    if len(packet) < 11 or packet[0] != 0x55 or checksum(packet[:10]) != packet[10]:
        return None
    data_type = packet[1]
    values = struct.unpack('<hhhh', packet[2:10])
    if data_type == 0x53:
        roll = values[0] / 32768.0 * 180.0
        pitch = values[1] / 32768.0 * 180.0
        yaw = values[2] / 32768.0 * 180.0
        return roll, pitch, yaw
    return None

def determine_direction(yaw):
    dirs = ["North", "NE", "East", "SE", "South", "SW", "West", "NW"]
    idx = int((yaw + 22.5) % 360 // 45)
    return dirs[idx]

def determine_surface(pitch, roll):
    if abs(pitch) < 45 and abs(roll) < 45:
        return "Floor"
    elif abs(pitch) > 135 or abs(roll) > 135:
        return "Ceiling"
    else:
        return "Wall"

async def imu_loop():
    try:
        ser = serial.Serial("/dev/ttyAMA2", 115200, timeout=0.1)
        ser.flushInput()
        print("IMU serial started on /dev/ttyAMA2")

        while True:
            if ser.read(1) == b'\x55':
                packet = b'\x55' + ser.read(10)
                result = parse_data(packet)
                if result:
                    roll, pitch, yaw = result
                    direction = determine_direction(yaw)
                    surface = determine_surface(pitch, roll)

                    msg = f"Facing: {direction} | Surface: {surface}"

                    os.makedirs("logs", exist_ok=True)
                    with open("logs/imu.log", "a") as f:
                        f.write(msg + "\n")

                    # Optionally keep log file small
                    with open("logs/imu.log", "r") as f:
                        lines = f.readlines()[-50:]  # Last 50 lines only
                    with open("logs/imu.log", "w") as f:
                        f.writelines(lines)

            await asyncio.sleep(0.5)

    except serial.SerialException as e:
        print("Serial error:", e)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(imu_loop())
