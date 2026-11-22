"""Hold the front Logitech's exposure at a multiple of 10 ms for as long as LeRobot has it open.

Lights on 50 Hz mains pulse at 100 Hz. With auto exposure the camera sometimes drops below
10 ms, for instance when the arm moves into view, and dark bands then roll through the video
(found in most of v10 up to episode 50). A fixed exposure only sticks if it's sent while the
camera streams, so this hooks OpenCVCamera.connect; on disconnect auto exposure is put back,
otherwise the next program to open the camera gets a badly overexposed image.

Use instead of the plain commands, with the same flags:
  python scripts/camera_lock.py lerobot-record ...
  python scripts/camera_lock.py lerobot-rollout ...
"""

import atexit
import importlib
import os
import subprocess
import sys
import time

import cv2

from lerobot.cameras.opencv import OpenCVCamera

FRONT = "/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0"
TARGET = 122.0  # mean grey level of the training image, assets/camera/front_v9.jpg
EXPOSURES = (100, 200)  # 10 ms, or 20 ms in dim light (units of 0.1 ms)
MIN_GAIN, MAX_GAIN = 16, 64  # the camera ignores less, and more gets noisy
SETTLE_S = 0.4

_connect = OpenCVCamera.connect
_disconnect = OpenCVCamera.disconnect


def _set(**controls: int) -> None:
    for name, value in controls.items():
        subprocess.run(["v4l2-ctl", "-d", FRONT, "-c", f"{name}={value}"], check=True)


def _is_front(camera: OpenCVCamera) -> bool:
    return os.path.realpath(str(camera.index_or_path)) == os.path.realpath(FRONT)


def _brightness(camera: OpenCVCamera) -> float:
    time.sleep(SETTLE_S)
    return float(cv2.cvtColor(camera.read_latest(), cv2.COLOR_RGB2GRAY).mean())


def _tune(camera: OpenCVCamera, control: str, low: int, high: int) -> str:
    while high - low > 1:
        middle = (low + high) // 2
        _set(**{control: middle})
        if _brightness(camera) < TARGET:
            low = middle
        else:
            high = middle
    _set(**{control: high})
    return f"{control} {high}"


def lock(camera: OpenCVCamera) -> None:
    _set(power_line_frequency=1, exposure_dynamic_framerate=0, brightness=128, auto_exposure=1)
    atexit.register(unlock)
    for exposure in EXPOSURES:
        _set(exposure_time_absolute=exposure, gain=MAX_GAIN)
        if _brightness(camera) >= TARGET:
            break
    _set(gain=MIN_GAIN)
    if _brightness(camera) > TARGET:
        setting = _tune(camera, "brightness", 90, 128)
    else:
        setting = _tune(camera, "gain", MIN_GAIN, MAX_GAIN)
    got = _brightness(camera)
    print(f"Front camera locked: {exposure // 10} ms, {setting}, image {got:.0f} (training {TARGET:.0f})", flush=True)


def unlock() -> None:
    subprocess.run(["v4l2-ctl", "-d", FRONT, "-c", "auto_exposure=3"], capture_output=True)


def _connect_locked(self: OpenCVCamera, *args, **kwargs) -> None:
    _connect(self, *args, **kwargs)
    if _is_front(self):
        try:
            lock(self)
        except Exception as error:  # a worse picture is better than no session
            unlock()
            print(f"Front camera NOT locked, it may flicker: {error!r}", flush=True)


def _disconnect_unlocked(self: OpenCVCamera, *args, **kwargs) -> None:
    if _is_front(self):
        unlock()
    _disconnect(self, *args, **kwargs)


def install() -> None:
    OpenCVCamera.connect = _connect_locked
    OpenCVCamera.disconnect = _disconnect_unlocked


if __name__ == "__main__":
    commands = ("lerobot-record", "lerobot-rollout")
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    command = sys.argv.pop(1)
    install()
    importlib.import_module(f"lerobot.scripts.{command.replace('-', '_')}").main()
