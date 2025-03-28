
def main():
    import pygame
    import numpy as np
    import serial
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
        
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected!")
        pygame.quit()
        sys.exit()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Connected to: {joystick.get_name()}")

    def map_steering(value):
        if value > 0.10: #Turning Right
            return round(np.interp(value, [0.10, 1.00], [0, 65]))
        elif value < -0.10:
            return round(np.interp(value, [-1.00, -0.10], [65, 0]))
        else:
            return 0

    def map_forward(value):
        return round(np.interp(value, [0.00, 1.00], [0, 65]))

    def map_reverse(value):
        return round(np.interp(value, [0.00, 1.00], [0, 65]))


    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt  # Trigger clean exit

            left_x = joystick.get_axis(0) # Controls Turning
            abs_gas = joystick.get_axis(5) # Controls going Forward
            abs_brake = joystick.get_axis(4) # Controls going backwards

            forward= map_forward(abs_gas) #Maps the forward speed
            reverse= map_reverse(abs_brake) #Maps the reverse speed
            steering_speed=map_steering(left_x) #Maps the steering speed

            if forward > 0:
                if left_x > 0.10: #Turning Right
                    motor1_speed = forward # Motor 1 Forward
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed 
                    motor2_speed = max(0, round(forward * decrease_factor)) # Motor 2 Decreased Speed since going forward and turning right
                    if motor2_speed >= motor1_speed:# Since motor 2 is going slower than motor 1, 
                        motor2_speed = motor1_speed * 0.8  #we need to decrease the speed of motor 2 to make sure it doesn't exceed motor 1
                elif left_x < -0.10: #Turning Left
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed
                    motor1_speed = max(0, round(forward * decrease_factor)) # Motor 1 Decreased Spped since going forward and turning left
                    motor2_speed = forward # Motor 2 Forward full speed
                    # Since motor 1 is going slower than motor 2, we need to decrease the speed of motor 1 to make sure it doesn't exceed motor 2
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                else: # Going straight
                    # No steering, both motors go forward at full speed
                    motor1_speed = forward
                    motor2_speed = forward
                print(f"Forward Motor 1 speed= {motor1_speed:.2f} | Motor 2 speed= {motor2_speed:.2f} ")
                send_packatized_command(128, 0, motor1_speed)
                send_packatized_command(128, 4, motor2_speed)

            elif reverse > 0:
                if left_x > 0.10: #Reverse Right
                    decrease_factor = 1 - (steering_speed / 65) # Normalize steering speed
                    motor1_speed = max(0, round(reverse * decrease_factor)) # Motor 1 Decreased Speed since going reverse and turning right
                    motor2_speed = reverse # Motor 2 Reverse full speed
                    # Since motor 1 is going slower than motor 2, we need to decrease the speed of motor 1 to make sure it doesn't exceed motor 2
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                elif left_x < -0.10: #Reverse Left
                    motor1_speed = reverse
                    decrease_factor = 1- (steering_speed /65)
                    motor2_speed = max(0, round(reverse * decrease_factor))
                    if motor2_speed >= motor1_speed:
                        motor2_speed = motor1_speed * 0.8
                else:
                    motor1_speed = reverse
                    motor2_speed = reverse
                print(f"Reverse Motor 1 speed= {motor1_speed:.2f} | Motor 2 speed= {motor2_speed:.2f} ")
                send_packatized_command(128, 1, motor1_speed)
                send_packatized_command(128, 5, motor2_speed)

            elif (steering_speed > 0) and (reverse == 0) and (forward == 0): #Turning in Place
                if left_x > 0.00:  # Turning right
                    print(f"Turning Right | Motor 1 Forward: {steering_speed}, Motor 2 Reverse: {steering_speed}")
                    send_packatized_command(128, 0, steering_speed)  # Motor 1 Forward
                    send_packatized_command(128, 5, steering_speed)  # Motor 2 Reverse
                elif left_x < 0.00:  # Turning left
                    print(f"Turning Left | Motor 1 Reverse: {steering_speed}, Motor 2 Forward: {steering_speed}")
                    send_packatized_command(128, 1, steering_speed)
                    send_packatized_command(128, 4, steering_speed)
                else:
                    print("No turning detected")
                    send_packatized_command(128, 0, 0)
                    send_packatized_command(128, 4, 0)

            else:  # Stop motors
                print("Motors Stopped")

            pygame.time.wait(50)  # Small delay to prevent excessive CPU usage

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        pygame.quit()
        sys.exit
        return False

# Press the green button in the gutter to run the script.

    
if __name__ == "__main__":
    main()