# HackLab LeRobot

SO-101 leader/follower project built on [LeRobot](https://github.com/huggingface/lerobot) (installed from PyPI, standalone).

## Environment

```bash
uv sync                 # creates .venv with lerobot[feetech]
source .venv/bin/activate
```

## Hardware

Use the stable `/dev/serial/by-id` paths, since `/dev/ttyACM*` numbers can swap when cables are replugged.

| Arm      | Port |
|----------|------|
| Follower | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00` |
| Leader   | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00` |

Calibration ids: follower `hacklab_follower`, leader `hacklab_leader` (stored in `~/.cache/huggingface/lerobot/calibration/`).

## Teleoperate

```bash
.venv/bin/lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 --robot.id=hacklab_follower \
  --teleop.type=so101_leader --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00 --teleop.id=hacklab_leader
```

## Checks

- `scripts/watch_follower.py`: live follower joint readout, torque off.
- `scripts/powered_test_follower.py`: moves each follower joint a small step and back.
- `scripts/teleop_check.py [seconds]`: eases the follower to the leader pose, mirrors it, reports tracking error.
