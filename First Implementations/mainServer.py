# This FastAPI server integrates motor control and IMU telemetry with a UI
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import serial, struct, sys, asyncio, datetime

app = FastAPI()
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

# Connect to Sabertooth motor controller
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

latest_control_input = {"timestamp": None, "input": "None"}
#App.post("/control") receives motor control commands
#This endpoint expects a JSON payload with motor speeds and action
@app.post("/control")
async def control_motors(data: MotorControl):
    #Update the latest control input properly
    latest_control_input["timestamp"] = datetime.datetime.now().strftime('%H:%M:%S')
    latest_control_input["input"] = data.action

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
    else:
        send_packatized_command(128, 0, 0)
        send_packatized_command(128, 4, 0)

    return {"status": "Success", "message": "Data received"}
#------------------------------------------------------------------------------------------------------
#Above line is the endpoint for motor control
@app.get("/")
async def get_ui():
    return FileResponse("ui/index.html")

#app.get inut returns the latest control input data
#This data includes the timestamp and the input action
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
        return "Floor"
    elif abs(pitch) > 135 or abs(roll) > 135:
        return "Ceiling"
    return "Wall"

latest_imu_data = {
    "timestamp": None,
    "facing": "N/A",
    "surface": "N/A",
    "accel": None,
    "gyro": None
}
#app.get("/imu") returns the latest IMU data
@app.get("/imu")
async def get_imu():
    data = latest_imu_data.copy()
    data["input"] = latest_control_input.get("input")
    return JSONResponse(content=data)

# def imu_loop reads data from the IMU sensor and updates the latest IMU data
#app.get("/imu") returns the latest IMU data
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
                # ![Acceleration](../docs/Acceleration0x51.png)
                if data_type == 0x51:
                    accel = tuple(v / 32768.0 * 16.0 for v in values[:3])

                #0x52 is the accelerometer data address
                # ![AngularVelocity](../docs/AngularVelocity0x52.png)
                elif data_type == 0x52:
                    gyro = tuple(v / 32768.0 * 2000.0 for v in values[:3])

                #0x53 is the Euler angles data address
                # # ![Angle](../docs/Angle0x53.png)
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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(imu_loop())
