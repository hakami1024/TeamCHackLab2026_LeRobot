#!/usr/bin/env python
"""lerobot-rollout (or another entry point, see record_v10.sh) plus one live video window with all the robot's cameras side by side.

The window is fed from the frames the robot's camera threads already capture, so no camera is
opened twice. A separate thread does the work: a slow, stalled or closed window only drops
video and never waits on the control loop.

Usage: same flags as lerobot-rollout (opencv-python here has no GUI, hence ffplay).
"""

import atexit
import os
import subprocess
import threading
import time
from collections.abc import Callable

import camera_lock
import numpy as np

from lerobot.cameras.opencv import OpenCVCamera
from lerobot.scripts.lerobot_rollout import main

FPS = 20
WIDTH, HEIGHT = 640, 480  # per camera, as in scripts/test_policy.sh

_cameras: list[OpenCVCamera] = []
_connect = camera_lock._connect_locked  # the front camera's exposure lock, then register


def _connect_and_register(self: OpenCVCamera, *args, **kwargs) -> None:
    _connect(self, *args, **kwargs)
    _cameras.append(self)


def _panel(camera: OpenCVCamera) -> np.ndarray:
    try:
        frame = camera.read_latest()
    except Exception:  # not started, stale or already disconnected: show black, never interfere
        return np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    return frame if frame.shape == (HEIGHT, WIDTH, 3) else np.zeros((HEIGHT, WIDTH, 3), np.uint8)


def _show(stop: threading.Event) -> None:
    while len(_cameras) < 2:  # front, then wrist
        if stop.wait(0.1):
            return
    cameras = _cameras[:2]
    player = subprocess.Popen(
        [
            "ffplay", "-loglevel", "error", "-window_title", "Robot cameras: front | wrist",
            "-fflags", "nobuffer", "-flags", "low_delay", "-noframedrop",
            "-probesize", "32", "-analyzeduration", "0",
            "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{WIDTH * 2}x{HEIGHT}",
            "-framerate", "60", "-i", "pipe:0",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0.0")},
        start_new_session=True,  # Ctrl+C is for the rollout, not the window
    )
    atexit.register(player.kill)  # also unblocks a write that a stalled window is holding up
    assert player.stdin is not None
    try:
        while not stop.is_set():
            started = time.perf_counter()
            player.stdin.write(np.hstack([_panel(camera) for camera in cameras]).tobytes())
            player.stdin.flush()
            stop.wait(max(0.0, 1 / FPS - (time.perf_counter() - started)))
    except (BrokenPipeError, ValueError, OSError):
        pass  # window closed: the rollout carries on without video


def run(entry: Callable[[], object] = main) -> None:
    camera_lock.install()
    OpenCVCamera.connect = _connect_and_register
    stop = threading.Event()
    viewer = threading.Thread(target=_show, args=(stop,), daemon=True)
    viewer.start()
    # atexit runs last-in first-out: the player is killed first, then this joins the thread
    atexit.register(lambda: (stop.set(), viewer.join(timeout=2)))
    entry()


if __name__ == "__main__":
    run()
