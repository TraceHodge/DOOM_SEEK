import evdev
import serial
import numpy as np
import sys


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


# Function to map ABS_X values for steering
def map_steering(value):
    """Maps ABS_X (0-65535) to turn intensity (0 to 65) with a dead zone."""
    if 20000 <= value <= 45000:
        return 0  # Dead zone: No turning, motors stop
    elif value < 20000:
        return round(np.interp(value, [0, 20000], [50, 0]))  # Left turn
    else:  # value > 45000
        return round(np.interp(value, [45000, 65535], [0, 50]))  # Right turn

# Map ABS_GAS for forward movement
def map_gas(value):
    return round(np.interp(value, [0, 1023], [0, 65]))  # Maps trigger to 0-65

# Map ABS_BRAKE for reverse movement
def map_brake(value):
    return round(np.interp(value, [0, 1023], [0, 65]))  # Maps trigger to 0-65

try:
    gas_speed = 0
    brake_speed = 0
    steering_map = 0
    
    for event in controller.read_loop():
        if event.type == evdev.ecodes.EV_ABS:# Reads From event EV_ABS
            if event.code == evdev.ecodes.ABS_GAS: # Uses ABS_GAS=Right Trigger to control speed going Foward
                gas_speed = map_gas(event.value)
            
            elif event.code == evdev.ecodes.ABS_BRAKE: # Uses ABS_BRAKE=Left Trigger to control speed going Backward
                brake_speed = map_brake(event.value)
            
            elif event.code == evdev.ecodes.ABS_X: # Uses ABS_X=Left Joystick to control steering
                steering_map1= event.value

            steering_map = map_steering(steering_map1) # Maps the Input Values to Turn Speed

            if gas_speed > 0: # This will control movement going foward and turning at the same time
                if steering_map1 > 45000:
                    motor1_speed = min(65, gas_speed + steering_map) #Motor 1 will increase speed while going forward and turning right
                    motor2_speed = max(0, (gas_speed - steering_map)*0.90) #Motor 2 will decrease speed by 10% while going forward and turning right
                
                if steering_map1 < 20000:
                    motor1_speed = max(0, (gas_speed - steering_map) *0.90) #Motor 1 will decrease speed by 10% while going forward and turning left
                    motor2_speed = min(65, gas_speed + steering_map) #Motor 2 will increase speed while going forward and turning left
                
                else:  # Moving straight
                        motor1_speed = gas_speed
                        motor2_speed = gas_speed
                
                send_packatized_command(128, 0, motor1_speed)
                send_packatized_command(128, 4, motor2_speed)
                print(f"Moving Forward | Motor 1: {motor1_speed} | Motor 2: {motor2_speed}")
            
            elif brake_speed > 0: # This will control movement going backward and turning at the same time
                if steering_map1 > 45000: 
                    motor1_speed = max(65, (gas_speed - steering_map)*0.90) #Motor 1 will decrease speed by 10 % while going backward and turning right
                    motor2_speed = min(0, gas_speed + steering_map) # Motor 2 will increase speed while going backward and turning right
                
                if steering_map1 < 20000:
                    motor1_speed = min(0, gas_speed + steering_map) # Motor 1 will increase speed while going backward and turning left
                    motor2_speed = max(65, (gas_speed - steering_map)*0.90) # Motor 2 will decrease speed by 10% while going backward and turning left
                
                else:  # Moving straight
                        motor1_speed = gas_speed
                        motor2_speed = gas_speed
                
                send_packatized_command(128, 1, motor1_speed)
                send_packatized_command(128, 5, motor2_speed)
                print(f"Moving Reverse | Motor 1: {motor1_speed} | Motor 2: {motor2_speed}")
            
            elif gas_speed == 0 and brake_speed == 0 and abs(steering_map) > 0: # This will control turning while the robot is stationary
                if steering_map1 > 450000: #Turning Right
                    send_packatized_command(128, 0, steering_map)  # Motor 1 Forward
                    send_packatized_command(128, 5, steering_map)  # Motor 2 Reverse
                    print(f"Turning Right: Motor 1 Forward, Motor 2 Reverse | Turn Speed: {steering_map}")
                
                elif steering_map1 < 20000: # Turning Left
                    send_packatized_command(128, 1, steering_map) # Motor 1 Reverse
                    send_packatized_command(128, 4, steering_map) # Motor 2 Forward
                    print(f"Turning Left: Motor 1 Reverse, Motor 2 Forward | Turn Speed: {steering_map}")
                
                else:
                    send_packatized_command(128, 0, 0) # Stop Motor 1
                    send_packatized_command(128, 4, 0) # Stop Motor 2
                    print("Dead Zone: Motors Stopped")
            
            else: # This will stop the motors if no input is detected
                send_packatized_command(128, 0, 0) # Stop Motor 1
                send_packatized_command(128, 4, 0) # Stop Motor 2
                print(f"Motors Stopped")

except KeyboardInterrupt:  # CTRL + C to stop the program
    print("\nInterrupt received! Stopping motors...")
    send_packatized_command(128, 0, 0)  # Stop Motor 1
    send_packatized_command(128, 4, 0)  # Stop Motor 2
    ser.close()
    sys.exit()

            
            

            
