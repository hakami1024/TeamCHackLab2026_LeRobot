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
