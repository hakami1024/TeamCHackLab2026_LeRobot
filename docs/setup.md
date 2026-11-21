# Arm setup (SO-101 leader + follower)

This is how we set up both arms from fresh motors on 2026-11-21. If the arms are already set up and calibrated, skip to [Teleoperate](#7-teleoperate).

All commands run from the repo root.

## 1. Python environment

The project has its own environment and does not depend on any other LeRobot checkout. It installs `lerobot[feetech]` 0.7.0 from PyPI.

```bash
uv sync
source .venv/bin/activate
```

If you don't activate the venv, call the tools as `.venv/bin/lerobot-...` like in the commands below.

Your user needs access to the serial ports. On Arch that means being in the `uucp` group (`dialout` on Ubuntu).

## 2. Find the ports

Each arm has its own controller board with a USB cable. The `/dev/ttyACM0` and `/dev/ttyACM1` numbers can swap when you replug, so we always use the stable `/dev/serial/by-id` paths:

| Arm      | Board serial | Port |
|----------|--------------|------|
| Follower | 5B90103156   | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00` |
| Leader   | 5B90100817   | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00` |

To figure this out on a new machine or with different boards, run `ls -l /dev/serial/by-id/`, unplug one arm, and run it again. The entry that disappeared belongs to the arm you unplugged. `lerobot-find-port` does the same thing interactively.

A quick sanity check: the follower board runs on the 12 V supply (about 11.9 V measured), the leader board on 5 V (about 4.9 V).

## 3. Motor IDs

Fresh motors all have the same ID, so each one needs its own ID before they can share a bus. This is done once per arm, **one motor at a time**.

1. Power the board and plug in its USB cable.
2. Disconnect every servo cable from the board except the one going to the motor the script asks for.
3. Run the setup for that arm. It asks for the motors in this order: **gripper first**, then wrist_roll, wrist_flex, elbow_flex, shoulder_lift, shoulder_pan. For each one, connect only that motor to the board and press Enter.

Leader:

```bash
.venv/bin/lerobot-setup-motors --teleop.type=so101_leader \
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00
```

Follower:

```bash
.venv/bin/lerobot-setup-motors --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00
```

You can do the two arms in parallel, one person per arm.

## 4. Chain the motors back together

After the ID setup, only the last motor (shoulder_pan) is still connected. Wire the whole chain back up in order:

board → shoulder_pan → shoulder_lift → elbow_flex → wrist_flex → wrist_roll → gripper

If a later step says a motor is missing, it is almost always a loose cable in the chain or a board without power. If **no** motor answers on the follower, check the 12 V supply first.

## 5. Calibrate

Calibration maps raw motor positions to a common range so the leader and follower agree. Joints end up roughly at −100 to +100, and the gripper at 0 (closed) to 100 (open).

```bash
.venv/bin/lerobot-calibrate --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 \
  --robot.id=hacklab_follower
```

```bash
.venv/bin/lerobot-calibrate --teleop.type=so101_leader \
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00 \
  --teleop.id=hacklab_leader
```

For each arm:

1. Move every joint to the middle of its range and press Enter.
2. Slowly sweep each joint through its full range, including opening and closing the gripper, then press Enter.

The calibration is saved under `~/.cache/huggingface/lerobot/calibration/` with the ids `hacklab_follower` and `hacklab_leader`. Always pass those same ids to later commands, otherwise LeRobot asks you to calibrate again.

## 6. Check scripts

These are in `scripts/` and use the ports and ids above.

| Script | What it does |
|--------|--------------|
| `scripts/watch_follower.py` | Prints the follower's joint positions live with torque off. Move the arm by hand and check that the numbers change smoothly. Ctrl+C stops it. |
| `scripts/powered_test_follower.py` | Moves each follower joint a small step toward its center and back, one at a time, and reports the error. Clear the area around the arm first. Errors under about 1 unit are normal, elbow_flex a bit more under gravity. |
| `scripts/teleop_check.py [seconds]` | Eases the follower to the leader's pose over 2 seconds, then mirrors the leader for the given time (default 30 s) and prints the tracking error per joint. |

```bash
.venv/bin/python scripts/watch_follower.py
.venv/bin/python scripts/powered_test_follower.py
.venv/bin/python scripts/teleop_check.py 60
```

## 7. Teleoperate

Before starting, put the leader in roughly the same pose as the follower. The plain teleop command makes the follower jump straight to the leader's pose. (`scripts/teleop_check.py` eases into it instead, which is gentler.)

```bash
.venv/bin/lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 --robot.id=hacklab_follower \
  --teleop.type=so101_leader --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00 --teleop.id=hacklab_leader
```

Move slowly at first. Ctrl+C stops it. Some lag on fast moves is normal (we saw up to about 15 units on the arm joints and 18 on the gripper during quick sweeps).
