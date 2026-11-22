#!/usr/bin/env bash
# Demo videos from a run recorded by test_policy.sh: front, wrist and side by side, as H.264
# (the dataset's AV1 doesn't play everywhere). Reads saved files only, not the cameras.
# Usage: scripts/save_demo.sh <name given to test_policy.sh>   -> outputs/demos/<name>/
cd "$(dirname "$0")/.." || exit 1
NAME="$1"
[ -n "$NAME" ] || { echo "usage: $0 <run name>"; exit 2; }
D=$(ls -dt ~/.cache/huggingface/lerobot/hakami1024/rollout_"${NAME}"_* 2>/dev/null | head -1)
FRONT="$D/videos/observation.images.front/chunk-000/file-000.mp4"
WRIST="$D/videos/observation.images.wrist/chunk-000/file-000.mp4"
[ -s "$FRONT" ] && [ -s "$WRIST" ] || { echo "no saved video for $NAME"; exit 1; }
OUT="outputs/demos/$NAME"
mkdir -p "$OUT"
ffmpeg -nostdin -loglevel error -y -i "$FRONT" -i "$WRIST" \
  -filter_complex "[0:v]split[f][f2];[1:v]split[w][w2];[f2][w2]hstack=shortest=1[both]" \
  -map "[f]" -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -movflags +faststart "$OUT/front.mp4" \
  -map "[w]" -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -movflags +faststart "$OUT/wrist.mp4" \
  -map "[both]" -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -movflags +faststart "$OUT/both.mp4" \
  || exit 1
echo "Demo saved: $OUT/{front,wrist,both}.mp4"
