# This script is used to control a robot using a joystick.
# It sends the motor speeds and actions to a server via HTTP POST requests.
# [Pygame controls Info](https://www.pygame.org/docs/ref/joystick.html)
# Our controls are for a Playstation 4 controller

def main():
    import pygame
    import numpy as np
    import requests
    import time

    SERVER_URL = "http://192.168.1.2:8000/control"

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected!")
        pygame.quit()
        exit()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Connected to: {joystick.get_name()}")

    base_speed = 65  # Starting speed
    max_speed = 80
    min_speed = 65
    led_state = "Led Off"

    def map_steering(value):
        if value > 0.10:
            return round(np.interp(value, [0.10, 1.00], [0, base_speed]))
        elif value < -0.10:
            return round(np.interp(value, [-1.00, -0.10], [base_speed, 0]))
        else:
            return 0

    def map_forward(value):
        return round(np.interp(value, [0.00, 1.00], [0, base_speed]))

    def map_reverse(value):
        return round(np.interp(value, [0.00, 1.00], [0, base_speed]))

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                # ----------------------------------- Start Of Button Events -----------------------------------
                if event.type == pygame.JOYBUTTONDOWN:
                    if joystick.get_button(11):  # D-pad UP
                        base_speed = min(base_speed + 5, max_speed)
                        print(f"Speed increased: {base_speed}")

                    if joystick.get_button(12):  # D-pad DOWN
                        base_speed = max(base_speed - 5, min_speed)
                        print(f"Speed decreased: {base_speed}")
                    
                    if joystick.get_button(0):  # X button (toggle LED)
                        if led_state == "Led Off":
                            led_state = "Led On"
                        else:
                            led_state = "Led Off"
                        print(f"LED State Changed: {led_state}")
                        data = { # data to send to the server for LED control
                            "motor1_speed": 0,
                            "motor2_speed": 0,
                            "action": led_state
                        }

                    if joystick.get_button(1):  # Circle button (Take Picture)
                        print("Picture button pressed!")
                        data = { # data to send to the server for taking a picture
                            "motor1_speed": 0,
                            "motor2_speed": 0,
                            "action": "Take Picture"
                        }
                    try:
                        response = requests.post(SERVER_URL, json=data)
                        if response.status_code != 200:
                            print(f"Failed to send Picture command: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                            print(f"Error sending Picture command: {e}")
                # ----------------------------------- End Of Button Events -----------------------------------

            left_x = joystick.get_axis(0)
            abs_gas = joystick.get_axis(5)
            abs_brake = joystick.get_axis(4)

            forward = map_forward(abs_gas)
            reverse = map_reverse(abs_brake)
            steering_speed = map_steering(left_x)

            action = "stop"
            motor1_speed = motor2_speed = 0

            if forward > 0:
                action = "forward"
                if left_x > 0.10:  # Turning right
                    motor1_speed = forward
                    decrease_factor = 1 - (steering_speed / base_speed) # Decrease factor for right turn
                    motor2_speed = max(0, round(forward * decrease_factor)) # Motor 2 speed is decreased
                    if motor2_speed >= motor1_speed: # Ensure motor 2 is slower
                        motor2_speed = motor1_speed * 0.8
                elif left_x < -0.10:  # Turning left
                    decrease_factor = 1 - (steering_speed / base_speed)
                    motor1_speed = max(0, round(forward * decrease_factor))
                    motor2_speed = forward 
                    if motor1_speed >= motor2_speed: # Ensure motor 1 is slower
                        motor1_speed = motor2_speed * 0.8
                else:
                    motor1_speed = forward
                    motor2_speed = forward

            elif reverse > 0:
                action = "reverse"
                if left_x > 0.10:
                    decrease_factor = 1 - (steering_speed / base_speed)
                    motor1_speed = max(0, round(reverse * decrease_factor))
                    motor2_speed = reverse
                    if motor1_speed >= motor2_speed:
                        motor1_speed = motor2_speed * 0.8
                elif left_x < -0.10:
                    motor1_speed = reverse
                    decrease_factor = 1 - (steering_speed / base_speed)
                    motor2_speed = max(0, round(reverse * decrease_factor))
                    if motor2_speed >= motor1_speed:
                        motor2_speed = motor1_speed * 0.8
                else:
                    motor1_speed = reverse
                    motor2_speed = reverse

            elif (steering_speed > 0) and (reverse == 0) and (forward == 0):
                if left_x > 0:
                    action = "Turning Right"
                    motor1_speed = steering_speed
                    motor2_speed = steering_speed
                elif left_x < 0:
                    action = "Turning Left"
                    motor1_speed = steering_speed
                    motor2_speed = steering_speed
                else:
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

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        pygame.quit()


if __name__ == "__main__":
    main()
