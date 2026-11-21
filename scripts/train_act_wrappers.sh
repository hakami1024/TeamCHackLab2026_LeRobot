#!/usr/bin/env bash
# ACT on the SO-101 wrappers dataset, sized for the RTX 3050 Laptop (4 GB).
# batch 8 OOMs; batch 4 + bf16 peaks ~2.1 GB and runs ~0.22 s/step.
# Usage: scripts/train_act_wrappers.sh [extra lerobot-train flags]
#   DATASET=hakami1024/other_set scripts/train_act_wrappers.sh --steps=5000
cd "$(dirname "$0")/.." && source .venv/bin/activate
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HUB_OFFLINE=1
exec lerobot-train \
  --dataset.repo_id="${DATASET:-hakami1024/wrappers_merged_v2346_clean}" \
  --policy.type=act --policy.device=cuda \
  --accelerator.mixed_precision=bf16 \
  --batch_size=4 --num_workers=4 \
  --steps=100000 --save_freq=10000 --log_freq=200 \
  --output_dir=outputs/train/act_wrappers --job_name=act_wrappers \
  --policy.push_to_hub=false "$@"
