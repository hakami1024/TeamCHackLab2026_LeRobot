"""Teleoperate for a fixed time: ease the follower to the leader's pose, then mirror it and report tracking error."""

import sys
import time

from lerobot.robots import make_robot_from_config
from lerobot.robots.so_follower import SO101FollowerConfig
from lerobot.teleoperators import make_teleoperator_from_config
from lerobot.teleoperators.so_leader import SO101LeaderConfig

FOLLOWER_PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00"
LEADER_PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00"
DURATION_S = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
HZ = 30

robot = make_robot_from_config(SO101FollowerConfig(port=FOLLOWER_PORT, id="hacklab_follower"))
leader = make_teleoperator_from_config(SO101LeaderConfig(port=LEADER_PORT, id="hacklab_leader"))
robot.connect(calibrate=False)
leader.connect(calibrate=False)
try:
    start = {k: v for k, v in robot.get_observation().items() if k.endswith(".pos")}
    goal = leader.get_action()
    n = 2 * HZ
    for i in range(1, n + 1):
        robot.send_action({k: start[k] + i / n * (goal[k] - start[k]) for k in start})
        time.sleep(1 / HZ)

    max_err = dict.fromkeys(start, 0.0)
    travel = dict.fromkeys(start, (float("inf"), float("-inf")))
    t_end = time.time() + DURATION_S
    last_print = 0.0
    while time.time() < t_end:
        action = leader.get_action()
        robot.send_action(action)
        obs = robot.get_observation()
        for k in start:
            lo, hi = travel[k]
            travel[k] = (min(lo, action[k]), max(hi, action[k]))
            max_err[k] = max(max_err[k], abs(obs[k] - action[k]))
        if time.time() - last_print > 5:
            last_print = time.time()
            print(f"{t_end - time.time():4.0f}s left  " + "  ".join(f"{k[:-4]}={action[k]:6.1f}" for k in start), flush=True)
        time.sleep(1 / HZ)

    print("\njoint           leader range        max |follower - leader|")
    for k in start:
        lo, hi = travel[k]
        print(f"{k[:-4]:14} {lo:7.1f} .. {hi:7.1f}     {max_err[k]:6.1f}")
finally:
    robot.disconnect()
    leader.disconnect()
