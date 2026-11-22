# Voice demo: "Hey Claude, clean the table"

Say the phrase, the laptop beeps, and after 3 seconds the SO-101 follower runs our ACT policy for 45 seconds to put candy wrappers into the bowl. Every run saves a video from both cameras.

Speech recognition is offline (Vosk on the CPU). All commands run from the repo root.

## The model

**ACT v10 fine-tune, 11,000 steps** (`act_v10_ft/011000`), the model used for the demos on 2026-11-22. It was fine-tuned from our `act_v2_v9_trim` 5k checkpoint on the v10 recordings ([dataset](https://huggingface.co/datasets/hakami1024/wrappers_to_bin_v10_20261122_124023)) with idle starts trimmed.

What to expect, from that evening's recordings:

- 4 voice-started runs: three put everything that was on the table at the start into the bowl (one or two wrappers), one got 1 of 2 before the 45 seconds ran out.
- 4 manual trials just before: one clean success, the others failed or had a hand help.

So it works, but not every time, and it's sensitive to the scene and camera aim.

The weights (207 MB) are too big for git, which rejects files over 100 MB, so they are attached to this repo's GitHub release `model-act-v10-ft-11k`. Anyone with write access to the repo can download them, no Hugging Face account or Git LFS needed. `models/act_v10_ft_011000.sha256` pins the exact files.

## 1. System packages (Arch)

```bash
sudo pacman -S --needed git github-cli uv ffmpeg v4l-utils libpulse psmisc speech-dispatcher espeak-ng curl unzip
```

- `speech-dispatcher` and `espeak-ng` provide `spd-say`, which LeRobot calls to announce the recording.
- `ffmpeg` provides the live camera window (`ffplay`) and the demo videos.
- `v4l-utils` provides `v4l2-ctl` for the camera lock.
- `libpulse` provides `parec`, `pacat` and `pactl` for the mic and the beep. They work with PulseAudio and PipeWire (`pipewire-pulse`).

The user needs serial port access (log out and in afterwards):

```bash
sudo usermod -aG uucp "$USER"
```

For the NVIDIA driver see [gpu.md](gpu.md). The Python environment needs about 7 GB of disk, and the launcher refuses to run with less than 1 GB free.

## 2. Python environment

```bash
uv sync --locked
```

ACT loads torchvision's ResNet-18 file (47 MB) when it is created, so fetch it once while online:

```bash
.venv/bin/python -c "from torchvision.models import resnet18; resnet18(weights='IMAGENET1K_V1')"
```

`uv sync` removes packages that aren't in the lock file, such as a hand-installed LeLab.

## 3. Download the model

Sign in once with `gh auth login`, then:

```bash
gh release download model-act-v10-ft-11k --pattern 'act_v10_ft_011000.tar' --dir /tmp --clobber
```

```bash
tar -xf /tmp/act_v10_ft_011000.tar
```

```bash
sha256sum -c models/act_v10_ft_011000.sha256
```

All seven lines must say `OK`. The tar unpacks into `outputs/train/act_v10_ft/checkpoints/011000/pretrained_model`, where the launcher looks by default.

## 4. Install speech recognition

Vosk has its own environment, so `uv sync` can't remove it.

```bash
uv venv --python 3.12 ~/.cache/hacklab_voice/venv
```

```bash
uv pip install --python ~/.cache/hacklab_voice/venv/bin/python vosk==0.3.45
```

```bash
curl -fL -o /tmp/vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
```

```bash
mkdir -p ~/.cache/vosk && unzip -q /tmp/vosk-model.zip -d ~/.cache/vosk
```

## 5. Arm calibration

The model only works in the calibration it was trained with. On a new laptop, copy it in (`-n` never overwrites an existing file):

```bash
mkdir -p ~/.cache/huggingface/lerobot/calibration/robots/so_follower
```

```bash
cp -n assets/calibration/hacklab_follower.json ~/.cache/huggingface/lerobot/calibration/robots/so_follower/
```

This file belongs to our follower (board 5B90103156). **Don't recalibrate that arm for the demo.** If a run asks about calibration, press a blank **Enter** to use the file. Never type `c`.

On a different arm, or after a motor or horn was changed, calibrate as in [setup.md](setup.md) and expect to retrain.

## 6. Devices

| Device | Path |
|--------|------|
| Follower | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00` |
| Front camera (Logitech, also the default mic) | `/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0` |
| Wrist camera | `/dev/v4l/by-id/usb-Generic_USB_HD_Camera_200910120001-video-index0` |

The leader arm isn't needed. Check that all three exist:

```bash
ls -l /dev/serial/by-id/ /dev/v4l/by-id/
```

With other hardware, change the paths in every place they appear:

| Script | Paths |
|--------|-------|
| `scripts/test_policy.sh` | follower, front, wrist |
| `scripts/voice_trigger.py` (`DEVICES`) | follower, front, wrist |
| `scripts/camera_lock.py` (`FRONT`) | front |
| `scripts/fix_front_camera.py` (`DEVICE`) | front |
| `scripts/aim_front_camera.sh` (`CAM`) | front |

Use `by-id` paths, because `/dev/ttyACM*` and `/dev/video*` numbers change on replug.

## 7. Cameras and scene

Aim the front camera until the blended picture has nothing doubled, then press `q`:

```bash
scripts/aim_front_camera.sh
```

Set the table up like the target picture (`assets/camera/front_v9.jpg`): bowl at top right, wrapper on the left, arm at rest.

**Flicker.** The lights pulse at 100 Hz on 50 Hz mains, and auto exposure lets dark bands roll through the video. The launcher already fixes this: `camera_lock.py` holds the exposure at 10 ms (20 ms in dim light) and matches the training brightness. Look for `Front camera locked` at the start of each run. If it says `NOT locked`, press Ctrl-C once and check `v4l-utils` and the camera path.

For previews outside the launcher, after a replug or reboot:

```bash
.venv/bin/python scripts/fix_front_camera.py
```

That alone is not enough for rollouts. Run those through `python scripts/camera_lock.py lerobot-rollout ...`.

## 8. Run it

First a dry run. It listens, beeps and prints the command, and **the arm doesn't move**:

```bash
scripts/voice_trigger.sh
```

Say "Hey Claude, clean the table". When that works, clear hands from the table and go live. **The arm moves on the phrase:**

```bash
scripts/voice_trigger.sh --live
```

| Option | Effect |
|--------|--------|
| `--ptt` | push-to-talk: press Enter, then say "clean the table" within 6 seconds |
| `--mic <source>` | use another microphone |
| `--min-conf 0.8` | stricter, if it fires by itself (default 0.65) |
| `--policy <dir>` | another local ACT checkpoint directory |
| `--text` | type phrases to test without a mic, never moves the arm |

During a run:

- Ctrl-C during the 3 second countdown cancels.
- `n` ends the recording early, for example once the arm is home.
- Don't press `r`, it throws the take away. These keys work from any window, so don't type elsewhere during a run.
- Ctrl-C during a run returns the arm to rest, saves and exits. **Press it only once**, a second press skips the return to rest.
- After the 45 seconds it needs about a minute to save before it listens again.

Videos land in `outputs/demos/voice_<time>/` (`front.mp4`, `wrist.mp4`, `both.mp4`), logs in `outputs/logs/`.

## 9. Microphone in a noisy room

- A headset or other close mic helps most. The default on our laptop is the front webcam next to the servos, so otherwise speak toward that camera.
- List mics with `pactl list short sources` and pass the name with `--mic`. Skip names ending in `.monitor`, those are speaker loopbacks.
- If it hears nothing, check mute and level: `pactl get-source-mute @DEFAULT_SOURCE@` and `pactl get-source-volume @DEFAULT_SOURCE@`. The laptop's built-in mic was at 25%. Raise the default one with `pactl set-source-volume @DEFAULT_SOURCE@ 80%`.
- The dry run prints each word it heard with a confidence. If yours are just under the threshold, get closer or lower `--min-conf` a little. If chatter triggers it, raise it to 0.8.
- In a loud room use `--ptt`, which also drops the need for "Hey Claude".
- Run only one trigger at a time, otherwise both hear you.

## Troubleshooting

| Message or symptom | Fix |
|--------------------|-----|
| `no config.json in ...` | do step 3 |
| `Vosk is not installed` or `no Vosk model` | do step 4 |
| `Ignored, arm or camera is busy` | close the program it names (preview, recording, other rollout) |
| `Ignored, less than 1 GB of disk left` | free some space |
| `The mic stream ended` | check `pactl list short sources` and `--mic` |
| Waits without moving at start | look for the calibration question, answer with a blank Enter |
| Reaches next to the wrapper | re-aim the front camera and match the scene |
| `spd-say` error at the end of a run | install `speech-dispatcher` and `espeak-ng`, then test `spd-say hello` |
| No camera window | needs a local desktop. Without one: `ROLLOUT="python scripts/camera_lock.py lerobot-rollout" scripts/voice_trigger.sh --live` |
