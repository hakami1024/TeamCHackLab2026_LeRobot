"""Print the follower's calibrated joint positions live (torque off, move it by hand). Ctrl+C to stop."""

import time

from lerobot.robots import make_robot_from_config
from lerobot.robots.so_follower import SO101FollowerConfig

PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00"

robot = make_robot_from_config(SO101FollowerConfig(port=PORT, id="hacklab_follower"))
robot.connect(calibrate=False)
robot.bus.disable_torque()
try:
    while True:
        obs = robot.get_observation()
        print("  ".join(f"{k.removesuffix('.pos')}={v:7.1f}" for k, v in obs.items()), end="\r", flush=True)
        time.sleep(0.05)
except KeyboardInterrupt:
    print()
finally:
    robot.disconnect()
