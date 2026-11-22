"""Reset the front Logitech for previews (50 Hz, 30 fps). Not enough for recording: use camera_lock.py.

Mains lights pulse at 100 Hz and the camera defaults to 60 Hz anti-flicker. This sets 50 Hz and
a fixed 30 fps, and starts auto exposure from 10 ms, a full light pulse. Exposure stays automatic
on purpose: a manual one isn't kept when the next program reopens the camera (it came back
badly overexposed while still reading 10 ms).

The camera forgets this on unplug or reboot, so run it before each session. It prints the
banding it measured: around 0.2% is clean, 1.5-2% is the visible flicker.
Usage: .venv/bin/python scripts/fix_front_camera.py
"""

import os
import subprocess
import sys

import cv2
import numpy as np

DEVICE = "/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0"
CLEAN_BELOW = 0.6  # percent


def set_controls(**controls: int) -> None:
    for name, value in controls.items():
        subprocess.run(["v4l2-ctl", "-d", DEVICE, "-c", f"{name}={value}"], check=True)


def open_camera() -> cv2.VideoCapture:
    capture = cv2.VideoCapture(os.path.realpath(DEVICE), cv2.CAP_V4L2)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    capture.set(cv2.CAP_PROP_FPS, 30)
    if not capture.read()[0]:
        sys.exit("The front camera gave no frame.")
    return capture


def banding(capture: cv2.VideoCapture) -> tuple[float, float]:
    """Return (moving bands in percent, mean brightness)."""
    for _ in range(45):
        capture.read()
    frames = [cv2.cvtColor(capture.read()[1], cv2.COLOR_BGR2GRAY).astype(np.float32) for _ in range(45)]
    rows = np.array([frame.mean(axis=1) for frame in frames])
    means = rows.mean(axis=1, keepdims=True)
    relative = rows / means
    return float((relative - np.median(relative, axis=0)).std() * 100), float(means.mean())


def main() -> None:
    if subprocess.run(["fuser", os.path.realpath(DEVICE)], capture_output=True).returncode == 0:
        sys.exit("The front camera is in use. Close the preview, rollout or recording first.")

    # these only take effect while the camera is streaming
    capture = open_camera()
    set_controls(power_line_frequency=1, exposure_dynamic_framerate=0, brightness=128)
    set_controls(auto_exposure=1)
    set_controls(exposure_time_absolute=100)  # 10 ms
    set_controls(auto_exposure=3)
    capture.release()

    # measure the way the next program will see it, after a fresh open
    capture = open_camera()
    bands, brightness = banding(capture)
    capture.release()
    verdict = "clean for now, record with camera_lock.py" if bands < CLEAN_BELOW else "STILL FLICKERING (or something moved), run again"
    print(f"Front camera: 50 Hz, 30 fps, bands {bands:.2f}%, brightness {brightness:.0f}: {verdict}")


if __name__ == "__main__":
    main()
