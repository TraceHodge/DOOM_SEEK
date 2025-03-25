import evdev
import serial
import numpy as np
import sys
import time

try:
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)  # Ensure correct port
    print("Serial connection established with Sabertooth.")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit()

# Initialize Sabertooth serial connection
def send_packatized_command(address, command, value):
    """Send a packetized command to Sabertooth"""
    try:
        value = max(0, value)  # Ensure speed is always positive
        checksum = (address + command + value) & 0x7F  # Ensure 7-bit checksum
        packet = bytes([address, command, value, checksum])
        ser.write(packet)
    except Exception as e:
        print(f"Error sending command: {e}")

# Find the Xbox controller
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
controller = None
for device in devices:
    if "Xbox Wireless Controller" in device.name:  # Adjust for Controller names
        controller = evdev.InputDevice(device.path)
if not controller:
    print("No Xbox controller found!")
    sys.exit()

print("Controller Connected:", controller.name)

# Function to map ABS_X values for steering
def map_steering(value):
    """Maps ABS_X (0-65535) to turn intensity (0 to 65) with a dead zone."""
    if 20000 <= value <= 45000:
        return 0  # Dead zone: No turning, motors stop
    elif value < 20000:
        return round(np.interp(value, [0, 20000], [50, 0]))  # Left turn
    else:  # value > 45000
        return round(np.interp(value, [45000, 65535], [0, 50]))  # Right turn

# Function to map ABS_X values to speed scaling (0 to 65)
def map_speed(value):
    """Maps ABS_X to dynamically adjust speed based on distance from center."""
    return round(np.interp(abs(value - 35000), [0, 35000], [0, 50]))  # Speed increases further from center
prev_speed=0
prev_turn=0
alpha=0.2

try: 
    for event in controller.read_loop():
        if event.type == evdev.ecodes.EV_ABS:# Reads From event EV_ABS
            speed= round((event.value/1023)*50)
            if event.code == evdev.ecodes.ABS_GAS:# Uses ABS_GAS=Right Trigger to control speed going Foward
                prev_speed= round(alpha * speed + (1-alpha) * prev_speed) #Smooth speed transition
                speed=round((event.value/1023)*50)# Maps the Input Values to Speed As input increases Speed 
                send_packatized_command(128,0,speed) #Motor 1 moving foward
                send_packatized_command(128,4,speed) #Motor 2 MovingFoward
                print(f"Speed: {speed}")
                print(f"Right Trigger: {event.value}")
            elif event.code == evdev.ecodes.ABS_BRAKE:# Uses ABS_BRAKE=Left Trigger to control speed going Backward
                speed=round((event.value/1023)*50)# Maps the Input Values to Speed As input increases Speed Increases
                send_packatized_command(128,1,speed)#Motor 1 BackWards
                send_packatized_command(128,5,speed)#Motor 2 BackWards
                print(f"Speed: {speed}")
                print(f"Left Trigger: {event.value}")
                prev_speed= round(alpha * speed + (1-alpha) * prev_speed)# Smoothing the speed
            elif event.code == evdev.ecodes.ABS_X:# ABS_X Controls the turning
                turn_adjust=map_steering(event.value)
                if 20000 <= event.value <= 45000:  # Dead Zone: Stop motors
                    send_packatized_command(128, 0, 0)  # Stop Motor 1
                    send_packatized_command(128, 4, 0)  # Stop Motor 2
                    print(f"Dead Zone: Motors Stopped (ABS_X: {event.value})")
                elif event.value < 20000:  # Turning Left (Motor 1 Reverse, Motor 2 Forward)
                    send_packatized_command(128, 1, turn_adjust)  # Motor 1 Reverse
                    send_packatized_command(128, 4, turn_adjust)  # Motor 2 Forward
                    print(f"Turning Left: Motor 1 Reverse, Motor 2 Forward | Turn Speed: {turn_adjust}")
                elif event.value > 45000:  # Turning Right (Motor 1 Forward, Motor 2 Reverse)
                    send_packatized_command(128, 0, turn_adjust)  # Motor 1 Forward
                    send_packatized_command(128, 5, turn_adjust)  # Motor 2 Reverse
                    print(f"Turning Right: Motor 1 Forward, Motor 2 Reverse | Turn Speed: {turn_adjust}")
                
                                    
                
except KeyboardInterrupt:  # CTRL + C to stop the program
    print("\nInterrupt received! Stopping motors...")
    send_packatized_command(128, 0, 0)  # Stop Motor 1
    send_packatized_command(128, 4, 0)  # Stop Motor 2
    ser.close()
    sys.exit()
