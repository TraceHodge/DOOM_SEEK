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

    screen = pygame.display.set_mode((400, 100))
    pygame.display.set_caption("Robot Controller - Focus This Window")

    if pygame.joystick.get_count() == 0:
        print("No controller detected!")
    else:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"Connected to: {joystick.get_name()}")

    base_speed = 65
    max_speed = 80
    min_speed = 65
    led_state = "Led Off"
    keyboard_detected = False

    keyboard_state = {
        "up": False,
        "down": False,
        "left": False,
        "right": False
    }

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

                if event.type == pygame.KEYDOWN:
                    if not keyboard_detected:
                        print("Keyboard input detected. Keyboard control is active.")
                        keyboard_detected = True

                    if event.key in [pygame.K_w, pygame.K_UP]:
                        keyboard_state["up"] = True
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        keyboard_state["down"] = True
                    if event.key in [pygame.K_a, pygame.K_LEFT]:
                        keyboard_state["left"] = True
                    if event.key in [pygame.K_d, pygame.K_RIGHT]:
                        keyboard_state["right"] = True

                if event.type == pygame.KEYUP:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        keyboard_state["up"] = False
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        keyboard_state["down"] = False
                    if event.key in [pygame.K_a, pygame.K_LEFT]:
                        keyboard_state["left"] = False
                    if event.key in [pygame.K_d, pygame.K_RIGHT]:
                        keyboard_state["right"] = False

                if event.type == pygame.JOYBUTTONDOWN and pygame.joystick.get_count() > 0:
                    if joystick.get_button(11):
                        base_speed = min(base_speed + 5, max_speed)
                        print(f"Speed increased: {base_speed}")
                    if joystick.get_button(12):
                        base_speed = max(base_speed - 5, min_speed)
                        print(f"Speed decreased: {base_speed}")
                    if joystick.get_button(0):
                        led_state = "Led On" if led_state == "Led Off" else "Led Off"
                        print(f"LED State Changed: {led_state}")
                        data = {
                            "motor1_speed": 0,
                            "motor2_speed": 0,
                            "action": led_state
                        }
                        try:
                            response = requests.post(SERVER_URL, json=data)
                            if response.status_code != 200:
                                print(f"Failed to send LED command: {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print(f"Error sending LED command: {e}")
                    if joystick.get_button(1):
                        print("Picture button pressed!")
                        data = {
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

            # Default values
            action = "stop"
            motor1_speed = motor2_speed = 0

            # Smooth keyboard motion
            if keyboard_state["up"]:
                action = "forward"
                if keyboard_state["left"]:
                    motor1_speed = base_speed * 0.7
                    motor2_speed = base_speed
                elif keyboard_state["right"]:
                    motor1_speed = base_speed
                    motor2_speed = base_speed * 0.7
                else:
                    motor1_speed = motor2_speed = base_speed
            elif keyboard_state["down"]:
                action = "reverse"
                if keyboard_state["left"]:
                    motor1_speed = base_speed * 0.7
                    motor2_speed = base_speed
                elif keyboard_state["right"]:
                    motor1_speed = base_speed
                    motor2_speed = base_speed * 0.7
                else:
                    motor1_speed = motor2_speed = base_speed
            elif keyboard_state["left"]:
                action = "Turning Left"
                motor1_speed = motor2_speed = base_speed * 0.5
            elif keyboard_state["right"]:
                action = "Turning Right"
                motor1_speed = motor2_speed = base_speed * 0.5

            # Joystick fallback (if no keyboard input)
            elif pygame.joystick.get_count() > 0:
                joystick = pygame.joystick.Joystick(0)
                left_x = joystick.get_axis(0)
                abs_gas = joystick.get_axis(5)
                abs_brake = joystick.get_axis(4)

                forward = map_forward(abs_gas)
                reverse = map_reverse(abs_brake)
                steering_speed = map_steering(left_x)

                if forward > 0:
                    action = "forward"
                    if left_x > 0.10:
                        motor1_speed = forward
                        decrease_factor = 1 - (steering_speed / base_speed)
                        motor2_speed = max(0, round(forward * decrease_factor))
                        if motor2_speed >= motor1_speed:
                            motor2_speed = motor1_speed * 0.8
                    elif left_x < -0.10:
                        decrease_factor = 1 - (steering_speed / base_speed)
                        motor1_speed = max(0, round(forward * decrease_factor))
                        motor2_speed = forward
                        if motor1_speed >= motor2_speed:
                            motor1_speed = motor2_speed * 0.8
                    else:
                        motor1_speed = motor2_speed = forward
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
                        motor1_speed = motor2_speed = reverse
                elif (steering_speed > 0):
                    if left_x > 0:
                        action = "Turning Right"
                        motor1_speed = motor2_speed = steering_speed
                    elif left_x < 0:
                        action = "Turning Left"
                        motor1_speed = motor2_speed = steering_speed

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

            time.sleep(0.03)  # Lower delay = smoother control

    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        pygame.quit()

if __name__ == "__main__":
    main()

