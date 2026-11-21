# GPU and CUDA

Training runs on the laptop's NVIDIA GPU: an **RTX 3050 Laptop GPU with 4 GB of VRAM** (Arch Linux, stock `linux` kernel, systemd-boot, Secure Boot off).

## What's installed

- Driver: `nvidia-open` 620.73.04 plus `nvidia-utils` (which also blocks the open-source `nouveau` driver).
- PyTorch in `.venv` is 2.15 built for CUDA 13.2. It ships its own CUDA libraries, so **only the driver is needed**, not a system-wide CUDA toolkit.

## Installing the driver on a fresh machine

```bash
sudo pacman -Syu nvidia-open nvidia-utils
sudo reboot
```

The first reboot after the install looked stuck for a few minutes, so we switched to a TTY with Ctrl+Alt+F3. The boot had actually completed fine, and Ctrl+Alt+F7 brings back the graphical login. If a boot really hangs, log in on a TTY and send the output of:

```bash
sudo journalctl -b -1 -p warning --no-pager | tail -60
```

The fallback entry in the systemd-boot menu also works for recovery. (`redshift-gtk` crashes on every boot on this laptop. That's an old, unrelated issue.)

## Check that CUDA works

```bash
nvidia-smi
.venv/bin/python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

The second command should print `True NVIDIA GeForce RTX 3050 Laptop GPU`.

## Training settings for 4 GB

- Use `--policy.device=cuda --batch_size=4 --accelerator.mixed_precision=bf16`. Batch 8 runs out of memory even with bf16. Batch 4 peaks around 2.1 GB at about 0.22 s per step. In LeRobot 0.7.0 `--policy.use_amp=true` does not turn on mixed precision.
- `scripts/train_act_wrappers.sh` has these settings. See [ml-plan.md](ml-plan.md#3-train-act-overnight).
- A rerun viewer left open from recording can hold about 300 MB of VRAM. Close it before a long run.
- Close other GPU users (browsers with video, the camera viewer) while training.
- Don't record and train on the same laptop at the same time. Record on one laptop and train on the other.
- If a full run would take longer than the night, use fewer steps or a free Kaggle or Colab GPU. The dataset lives on the Hugging Face Hub, so the same `lerobot-train` command works there.
