#This is a simple FastAPI server that communicates with a Sabertooth motor controller over serial.
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

#Def send_packatized_command function sends a command to the Sabertooth motor controller
#It uses 3 bytes to send the command, which includes the address, command, and value
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
    
#app post sends the motor control data to the Sabertooth motor controller
#Packet 0 and 4 are used to control the forward actions of the motors 
#Packet 1 and 5 are used to control the reverse actions of the motors
#128 is the address of the Sabertooth motor controller 
# [SaberTooth Info](Sabertooth2x32.pdf)
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

