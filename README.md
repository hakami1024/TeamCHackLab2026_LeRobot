# HackLab LeRobot

Team C, HackLab 2026. An SO-101 arm that picks up empty candy wrappers and drops them into a bin, trained with [LeRobot](https://github.com/huggingface/lerobot) 0.7.0 (installed from PyPI, standalone).

## Docs

- [docs/setup.md](docs/setup.md): environment, ports, motor IDs, chaining, calibration, check scripts, teleoperation
- [docs/ml-plan.md](docs/ml-plan.md): the task, recording, ACT training, running the policy, what to do if it fails
- [docs/gpu.md](docs/gpu.md): NVIDIA driver, CUDA check, training settings for the 4 GB RTX 3050

## Quick start

```bash
uv sync                 # creates .venv with lerobot[feetech]
source .venv/bin/activate
```

| Arm      | Port | Calibration id |
|----------|------|----------------|
| Follower | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00` | `hacklab_follower` |
| Leader   | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00` | `hacklab_leader` |

Use these `/dev/serial/by-id` paths, since `/dev/ttyACM*` numbers can swap when cables are replugged. Calibrations live in `~/.cache/huggingface/lerobot/calibration/`.

Teleoperate (put the leader in roughly the follower's pose first):

```bash
.venv/bin/lerobot-teleoperate \
  --robot.type=so101_follower --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 --robot.id=hacklab_follower \
  --teleop.type=so101_leader --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00 --teleop.id=hacklab_leader
```

## Check scripts

- `scripts/watch_follower.py`: live follower joint readout, torque off.
- `scripts/powered_test_follower.py`: moves each follower joint a small step and back.
- `scripts/teleop_check.py [seconds]`: eases the follower to the leader pose, mirrors it, reports tracking error.

Record, train and run commands are in [docs/ml-plan.md](docs/ml-plan.md).
