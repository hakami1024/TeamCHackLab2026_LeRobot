#!/usr/bin/env bash
# One 45 s autonomous trial on the follower, recorded to a rollout_ dataset, plus a
# contact sheet (one frame every 2 s, front on top, wrist below) for review.
# Usage: scripts/test_policy.sh <policy_path> <name> [extra lerobot-rollout flags]
# Live camera window: ROLLOUT="python scripts/rollout_with_video.py" scripts/test_policy.sh ...
cd "$(dirname "$0")/.." && source .venv/bin/activate
export HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
set -o pipefail
mkdir -p outputs/logs  # not in git, and tee fails without it
POLICY="$1"; NAME="$2"; shift 2
FRONT=/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0
WRIST=/dev/v4l/by-id/usb-Generic_USB_HD_Camera_200910120001-video-index0
REPO=hakami1024/rollout_${NAME}_$(date +%Y%m%d_%H%M%S)
${ROLLOUT:-python scripts/camera_lock.py lerobot-rollout} --strategy.type=episodic --policy.path="$POLICY" --policy.n_action_steps=30 \
  --robot.type=so101_follower --robot.id=hacklab_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 \
  --robot.cameras="{front: {type: opencv, index_or_path: $FRONT, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: $WRIST, width: 640, height: 480, fps: 30}}" \
  --dataset.repo_id="$REPO" --dataset.single_task="Pick up the candy wrapper and put it in the bin" \
  --dataset.num_episodes=1 --dataset.episode_time_s=45 --dataset.reset_time_s=0 \
  --dataset.push_to_hub=false "$@" 2>&1 | tee -i "outputs/logs/rollout_${NAME}.log" || exit 1  # tee, not >: connect can ask for ENTER
D=$(ls -dt ~/.cache/huggingface/lerobot/${REPO}* | head -1)
T=$(mktemp -d)
for c in front wrist; do
  ffmpeg -loglevel error -y -i "$D/videos/observation.images.$c/chunk-000/file-000.mp4" -vf "fps=0.5,scale=320:240" "$T/${c}_%02d.jpg"
  ffmpeg -loglevel error -y -i "$T/${c}_%02d.jpg" -vf tile=6x4 -frames:v 1 "$T/$c.jpg"
done
mkdir -p outputs/rollout_sheets
ffmpeg -loglevel error -y -i "$T/front.jpg" -i "$T/wrist.jpg" -filter_complex "vstack,scale=1280:-1" "outputs/rollout_sheets/${NAME}.jpg"
rm -rf "$T"
echo "outputs/rollout_sheets/${NAME}.jpg"
