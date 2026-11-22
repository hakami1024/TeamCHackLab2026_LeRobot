# HackLab LeRobot

Team C, HackLab 2026. An SO-101 arm that picks up empty candy wrappers and drops them into a bin, trained with [LeRobot](https://github.com/huggingface/lerobot) 0.7.0 (installed from PyPI, standalone).

## Run the voice demo: "Hey Claude, clean the table"

The demo model is the ACT v10 fine-tune at 11k steps. Its weights (207 MB) are too big for git, so they are a file on this repo's draft release `model-act-v10-ft-11k`, visible to collaborators with write access.

On a new laptop, first install the [system packages](docs/voice-demo.md#1-system-packages-arch) and sign in with `gh auth login`. Then, from the repo root:

1. Install the Python environment: `uv sync --locked`
2. Download and check the model:

   ```bash
   gh release download model-act-v10-ft-11k --pattern 'act_v10_ft_011000.tar' --dir /tmp --clobber
   ```

   ```bash
   tar -xf /tmp/act_v10_ft_011000.tar
   ```

   ```bash
   sha256sum -c models/act_v10_ft_011000.sha256
   ```

3. Install [speech recognition](docs/voice-demo.md#4-install-speech-recognition), copy in the [arm calibration](docs/voice-demo.md#5-arm-calibration) and check the [device paths](docs/voice-demo.md#6-devices).
4. Dry run, the arm doesn't move: `scripts/voice_trigger.sh`
5. Live, **the arm moves on the phrase**: `scripts/voice_trigger.sh --live` (add `--ptt` for push-to-talk in a noisy room)

If asked about calibration, press a blank Enter, never `c`. To stop, press Ctrl-C once. Saying "don't" is not a safe stop. Camera aim, flicker, mic tips and troubleshooting are in [docs/voice-demo.md](docs/voice-demo.md).

## Docs

- **[docs/voice-demo.md](docs/voice-demo.md): run the demo ("Hey Claude, clean the table"): model download, install, cameras, mic, troubleshooting**
- [docs/setup.md](docs/setup.md): environment, ports, motor IDs, chaining, calibration, check scripts, teleoperation
- [docs/ml-plan.md](docs/ml-plan.md): the task, recording, ACT training, running the policy, what to do if it fails
- [docs/gpu.md](docs/gpu.md): NVIDIA driver, CUDA check, training settings for the 4 GB RTX 3050

## Quick start

```bash
uv sync                 # creates .venv with LeRobot and the extras we use
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
