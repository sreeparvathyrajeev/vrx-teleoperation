
"""Basic keyboard teleoperation for the VRX WAM-V.

W / Up      forward
S / Down    backward
A / Left    turn left
D / Right   turn right
Ctrl+C      stop and quit

Hold a key to keep driving. Release it and the boat stops.
"""
import os
import select
import sys
import termios
import time
import tty

import rclpy
from std_msgs.msg import Float64

LEFT_TOPIC = "/wamv/thrusters/left/thrust"
RIGHT_TOPIC = "/wamv/thrusters/right/thrust"

DRIVE_THRUST = 500.0  # newtons
TURN_THRUST = 300.0   # newtons

LOOP_PERIOD = 0.05          # publish 20 times per second
FIRST_PRESS_TIMEOUT = 0.8   # a single tap drives for this long
REPEAT_TIMEOUT = 0.15       # while holding, stop this fast after release
REPEAT_GAP = 0.25           # presses closer together than this = key held

# command -> (left thrust, right thrust)
COMMANDS = {
    "forward": (DRIVE_THRUST, DRIVE_THRUST),
    "backward": (-DRIVE_THRUST, -DRIVE_THRUST),
    "left": (-TURN_THRUST, TURN_THRUST),
    "right": (TURN_THRUST, -TURN_THRUST),
}

KEYS = {"w": "forward", "s": "backward", "a": "left", "d": "right"}
ARROWS = {"A": "forward", "B": "backward", "C": "right", "D": "left"}


def parse_keys(data):
    """Turn raw terminal input into a list of command names."""
    commands = []
    i = 0
    while i < len(data):
        if data[i] == "\x1b" and i + 2 < len(data) and data[i + 1] in "[O":
            cmd = ARROWS.get(data[i + 2])  # arrow keys: ESC [ A/B/C/D
            i += 3
        else:
            cmd = KEYS.get(data[i].lower())
            i += 1
        if cmd:
            commands.append(cmd)
    return commands


def main():
    

    rclpy.init()
    node = rclpy.create_node("keyboard_teleop")
    left_pub = node.create_publisher(Float64, LEFT_TOPIC, 10)
    right_pub = node.create_publisher(Float64, RIGHT_TOPIC, 10)

    def send(left, right):
        left_pub.publish(Float64(data=left))
        right_pub.publish(Float64(data=right))

#to restore the original terminal settings when the program exits, even if it crashes or is interrupted. 
# This is important because changing terminal settings can leave the terminal in an unusable state if not properly restored.
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    print("WASD or arrow keys to drive. Hold to keep moving. Ctrl+C to quit.")
    time.sleep(0.5)  # let the publishers connect before the first command

    active = None
    last_key_time = 0.0
    timeout = FIRST_PRESS_TIMEOUT

    try:
        tty.setcbreak(fd)  # read keys instantly, no Enter needed
        while True:
            now = time.monotonic()

            # Read any keys waiting in the input buffer, without blocking.
            while select.select([fd], [], [], 0)[0]:
                data = os.read(fd, 64).decode(errors="ignore")
                for cmd in parse_keys(data):
                    if cmd == active and now - last_key_time < REPEAT_GAP:
                        timeout = REPEAT_TIMEOUT      # key is being held
                    else:
                        timeout = FIRST_PRESS_TIMEOUT  # first press / tap
                    active = cmd
                    last_key_time = now

            # No new press within the timeout means the key was released.
            if active and now - last_key_time > timeout:
                active = None

            left, right = COMMANDS[active] if active else (0.0, 0.0)
            send(left, right)
            time.sleep(LOOP_PERIOD)

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\nStopping thrusters...")
        for _ in range(5):  # the thruster plugin holds its last command,
            send(0.0, 0.0)  # so send explicit zeros, a few times
            time.sleep(0.05)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()