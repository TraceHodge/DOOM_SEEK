def main():
    import pygame
    import numpy as np

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected!")
        pygame.quit()
        exit()

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
        return round(np.interp(value, [-0.10, 1.00], [0, 65]))

    def map_reverse(value):
        return round(np.interp(value, [-0.10, 1.00], [0, 65]))

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt  # Trigger clean exit

            left_x = joystick.get_axis(0) # Controls Turning
            abs_gas = joystick.get_axis(5) # Controls going Forward
            abs_brake = joystick.get_axis(2) # Controls going backwards

            forward= map_forward(abs_gas)
            reverse= map_reverse(abs_brake)
            steering_speed=map_steering(left_x)

            if forward > 0:
                if left_x > 0.10: #Turning Right
                    motor1_speed = forward
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed
                    motor2_speed = max(0, round(forward * decrease_factor))
                    if motor2_speed >= motor1_speed:
                        motor2_speed = motor1_speed * 0.8
                elif left_x < -0.10: #Turning Left
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed
                    motor1_speed = max(0, round(forward * decrease_factor))
                    motor2_speed = forward
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                else:
                    motor1_speed = forward
                    motor2_speed = forward
                print(f"Forward Motor 1 speed= {motor1_speed:.2f} | Motor 2 speed= {motor2_speed:.2f} ")

            elif reverse > 0:
                if left_x > 0.10: #Reverse Right
                    decrease_factor = 1 - (steering_speed / 65)
                    motor1_speed = max(0, round(reverse * decrease_factor))
                    motor2_speed = reverse
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

            elif (steering_speed > 0) and (reverse == 0) and (forward == 0): #Turning in Place
                if left_x > 0:  # Turning right
                    print(f"Turning Right | Motor 1 Forward: {steering_speed}, Motor 2 Reverse: {steering_speed}")
                elif left_x < 0:  # Turning left
                    print(f"Turning Left | Motor 1 Reverse: {steering_speed}, Motor 2 Forward: {steering_speed}")

            else:  # Stop motors
                print("Motors Stopped")

            pygame.time.wait(50)  # Small delay to prevent excessive CPU usage

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        pygame.quit()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
