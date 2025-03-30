from fastapi import FastAPI
from pydantic import BaseModel
import serial
import sys

try:
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)  # Ensure correct port
    print("Serial connection established with Sabertooth.")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit()


def send_packatized_command(address, command, value):
    """Send a packetized command to Sabertooth"""
    try:
        checksum = (address + command + value) & 0x7F  # Ensure 7-bit checksum
        packet = bytes([address, command, value, checksum])
        ser.write(packet)
        # print(f"Sent: {packet}")  # Debugging output
    except Exception as e:
        print(f"Error sending command: {e}")

app = FastAPI()

class MotorControl(BaseModel):
    motor1_speed: int
    motor2_speed: int
    action: str

@app.post("/control")
async def control_motors(data: MotorControl):
    print(f"Received Data: {data}")
    print(f"Motor 1 Speed: {data.motor1_speed}, Motor 2 Speed: {data.motor2_speed}")

    motor1_speed = data.motor1_speed
    motor2_speed = data.motor2_speed
    action = data.action

    if action == "forward":
        send_packatized_command(128, 0, motor1_speed)
        send_packatized_command(128, 4, motor2_speed)
    
    elif action == "reverse":
        send_packatized_command(128, 1, motor1_speed)
        send_packatized_command(128, 5, motor2_speed)
        
    elif action =="Turning Right":
        send_packatized_command(128, 0, motor1_speed)
        send_packatized_command(128, 5, motor2_speed)
        
    elif action == "Turning Left":
        send_packatized_command(128, 1, motor1_speed)
        send_packatized_command(128, 4, motor2_speed)
    else:
        send_packatized_command(128, 0, 0)
        send_packatized_command(128, 4, 0)
    return {"status": "Success", "message": "Data received"}

