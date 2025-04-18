import smbus
import struct
import time

# Configure I2C connection for Raspberry Pi 5
I2C_ADDRESS = 0x50  # Default I2C address of WT61 IMU
bus = smbus.SMBus(1)  # Use I2C bus 1

def read_data():
    """Read and parse data from WT61 IMU over I2C"""
    try:
        data = bus.read_i2c_block_data(I2C_ADDRESS, 0, 11)  # Read 11-byte frame
        if len(data) == 11 and data[0] == 0x55:  # Validate data packet
            return data
    except Exception as e:
        print(f"I2C Read Error: {e}")
    return None

# Program: Using Built-in Euler Angles
def parse_euler(data):
    """Parse Euler angles from built-in processing"""
    roll = struct.unpack('<h', bytes(data[2:4]))[0] / 32768.0 * 180  # Convert to degrees
    pitch = struct.unpack('<h', bytes(data[4:6]))[0] / 32768.0 * 180
    yaw = struct.unpack('<h', bytes(data[6:8]))[0] / 32768.0 * 180
    return roll, pitch, yaw

print("Using Built-in Euler Angles:")
while True:
    data = read_data()  # Read data from IMU
    if data and data[1] == 0x53:  # Check if data contains built-in Euler angles
        roll, pitch, yaw = parse_euler(data)  # Extract roll, pitch, yaw
        print(f'Built-in Roll: {roll:.2f}, Pitch: {pitch:.2f}, Yaw: {yaw:.2f}')  # Print results
    time.sleep(0.01)  # Wait for next sample
