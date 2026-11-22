#!/usr/bin/env bash
# Aim the front camera: LIVE | TARGET (v9 demos) | both blended. Line the blend up until
# nothing is doubled (table edge, wood seams, gripper at rest). Press q to close.
# Only one program can hold the camera, so close other previews and rollouts first.
cd "$(dirname "$0")/.."
CAM=${1:-/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0}
REF=assets/camera/front_v9.jpg
T="fontsize=30:fontcolor=red:x=12:y=12"
exec ffplay -loglevel error -window_title "Aim front camera" -x 1800 -y 450 \
  -f v4l2 -video_size 640x480 -framerate 30 "$CAM" \
  -vf "format=yuv420p,split[a][b];movie=$REF,format=yuv420p,split[r1][r2];\
[a]pad=1920:480[p];[p][r1]overlay=640:0:eof_action=repeat[side];\
[r2]format=yuva420p,colorchannelmixer=aa=0.5[t];[b][t]overlay=0:0:eof_action=repeat[mix];\
[side][mix]overlay=1280:0,drawtext=text=LIVE:$T,drawtext=text=TARGET:fontsize=30:fontcolor=red:x=652:y=12,drawtext=text=BLEND:fontsize=30:fontcolor=red:x=1292:y=12"
