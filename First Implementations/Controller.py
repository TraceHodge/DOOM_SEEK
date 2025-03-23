import evdev
import serial
import numpy as np
import sys


try:
    ser = serial.Serial('/dev/serial0', 9600, timeout=1)  # Ensure correct port
    print("Serial connection established with Sabertooth.")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit()

# Initialize Sabertooth serial connection
def send_packatized_command(address, command, value):
    """Send a packetized command to Sabertooth"""
    try:
        checksum = (address + command + value) & 0x7F  # Ensure 7-bit checksum
        packet = bytes([address, command, value, checksum])
        ser.write(packet)
        #print(f"Sent: {packet}")  # Debugging output
    except Exception as e:
        print(f"Error sending command: {e}")

# Find the Xbox controller
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
controller = None
for device in devices:
    if "Xbox Wireless Controller" in device.name:  # Adjust for Controller names
        controller = evdev.InputDevice(device.path)
if not controller:
    print("No PlayStation controller found!")
    sys.exit()

print("Controller Connected:", controller.name)


try: 
    for event in controller.read_loop():
        if event.type == evdev.ecodes.EV_ABS: #Reads From  event EV_ABS
            if event.code == evdev.ecodes.ABS_GAS:# Uses ABS_GAS=Right Trigger to control speed going Foward
                speed=round((event.value/1023)*127)# Maps the Input Values to Speed As input increases Speed 
                send_packatized_command(128,0,speed) #Motor 1 moving foward
                send_packatized_command(128,4,speed) #Motor 2 MovingFoward
                print(f"Speed: {speed}")
                print(f"Right Trigger: {event.value}")
            elif event.code == evdev.ecodes.ABS_BRAKE:# Uses ABS_BRAKE=Left Trigger to control speed going Backward
                speed=round((event.value/1023)*127)# Maps the Input Values to Speed As input increases Speed Increases
                send_packatized_command(128,1,speed)#Motor 1 BackWards
                send_packatized_command(128,5,speed)#Motor 2 BackWards
                print(f"Speed: {speed}")
                print(f"Left Trigger: {event.value}")

except KeyboardInterrupt:#CTRL + C is the Keyboard Interrupt
    print("\nInterrupt received! Stopping motors...")
    ser.write(bytes([128, 0, 0]))  # Stop Motor 1
    ser.write(bytes([128, 4, 0]))  # Stop Motor 2
    ser.close()
    sys.exit()