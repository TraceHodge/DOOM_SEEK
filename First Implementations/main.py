def main():
    import pygame
    import numpy as np
    import requests
    import time

    SERVER_URL = "http://10.13.57.244:8000/control"  # Replace with your Raspberry Pi's IP

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
        if value > 0.10:  # Turning Right
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
                    raise KeyboardInterrupt

            left_x = joystick.get_axis(0)  # Steering
            abs_gas = joystick.get_axis(5)  # Forward
            abs_brake = joystick.get_axis(4)  # Reverse

            forward = map_forward(abs_gas)
            reverse = map_reverse(abs_brake)
            steering_speed = map_steering(left_x)

            action = "stop"
            motor1_speed = motor2_speed = 0

            if forward > 0:
                action = "forward"
                if left_x > 0.10:  # Turning Right
                    motor1_speed = forward
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed
                    motor2_speed = max(0, round(forward * decrease_factor))
                    if motor2_speed >= motor1_speed:
                        motor2_speed = motor1_speed * 0.8
                elif left_x < -0.10:  # Turning Left
                    decrease_factor = 1 - (steering_speed / 65)  # Normalize steering speed
                    motor1_speed = max(0, round(forward * decrease_factor))
                    motor2_speed = forward
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                else:
                    motor1_speed = forward
                    motor2_speed = forward

            elif reverse > 0:
                action = "reverse"
                if left_x > 0.10:  # Reverse Right
                    decrease_factor = 1 - (steering_speed / 65)
                    motor1_speed = max(0, round(reverse * decrease_factor))
                    motor2_speed = reverse
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                elif left_x < -0.10:  # Reverse Left
                    motor1_speed = reverse
                    decrease_factor = 1 - (steering_speed / 65)
                    motor2_speed = max(0, round(reverse * decrease_factor))
                    if motor2_speed >= motor1_speed:
                        motor2_speed = motor1_speed * 0.8
                else:
                    motor1_speed = reverse
                    motor2_speed = reverse


            elif (steering_speed > 0) and (reverse == 0) and (forward == 0):  # Turning in Place
                action = "turn"
                if left_x > 0:  # Turning right
                    action="Turning Right"
                    print(f"Turning Right | Motor 1 Forward: {steering_speed}, Motor 2 Reverse: {steering_speed}")
                    motor1_speed = steering_speed
                    motor2_speed = steering_speed

                elif left_x < 0:  # Turning left
                    action = "Turning Left"
                    print(f"Turning Left | Motor 1 Reverse: {steering_speed}, Motor 2 Forward: {steering_speed}")
                    motor1_speed=steering_speed
                    motor2_speed=steering_speed

                else:  # Stop motors
                    print("Motors Stopped")

            data = {
                "motor1_speed": motor1_speed,
                "motor2_speed": motor2_speed,
                "action": action
            }

            try:
                response = requests.post(SERVER_URL, json=data)
                if response.status_code != 200:
                    print(f"Failed to send data: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")

            time.sleep(0.05)  # Prevent spamming the server

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        pygame.quit()


if __name__ == "__main__":
    main()