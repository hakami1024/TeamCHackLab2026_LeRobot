"""Move each follower joint a small step toward its center and back, one at a time, and report tracking error."""

import time

from lerobot.robots import make_robot_from_config
from lerobot.robots.so_follower import SO101FollowerConfig

PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00"
STEP = {"gripper": 15.0}  # gripper range is 0..100, the arm joints are -100..100
DEFAULT_STEP = 10.0


def move(robot, start, target, seconds=1.0, hz=50):
    n = int(seconds * hz)
    for i in range(1, n + 1):
        a = i / n
        robot.send_action({k: start[k] + a * (target[k] - start[k]) for k in start})
        time.sleep(1 / hz)
    time.sleep(0.4)
    return robot.get_observation()


robot = make_robot_from_config(SO101FollowerConfig(port=PORT, id="hacklab_follower"))
robot.connect(calibrate=False)
try:
    home = {k: v for k, v in robot.get_observation().items() if k.endswith(".pos")}
    for key in home:
        name = key.removesuffix(".pos")
        step = STEP.get(name, DEFAULT_STEP)
        center = 50.0 if name == "gripper" else 0.0
        target = dict(home)
        target[key] = home[key] + (step if home[key] < center else -step)
        reached = move(robot, home, target)[key]
        back = move(robot, target, home)[key]
        print(
            f"{name:14} start={home[key]:7.1f} goal={target[key]:7.1f} reached={reached:7.1f} "
            f"(err {reached - target[key]:+5.1f})  back={back:7.1f} (err {back - home[key]:+5.1f})"
        )
finally:
    robot.disconnect()
