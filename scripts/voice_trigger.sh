#!/usr/bin/env bash
# Voice trigger for the arm, see scripts/voice_trigger.py. Dry-run unless --live.
# Vosk gets its own venv because `uv sync` would remove it from the project one.
cd "$(dirname "$0")/.." || exit 1
# Live camera window by default. It sets the same front-camera exposure lock as camera_lock.py.
export ROLLOUT="${ROLLOUT:-python scripts/rollout_with_video.py}"
PY="$HOME/.cache/hacklab_voice/venv/bin/python"
[ -x "$PY" ] || PY=.venv/bin/python  # enough for --text
exec "$PY" scripts/voice_trigger.py "$@"
