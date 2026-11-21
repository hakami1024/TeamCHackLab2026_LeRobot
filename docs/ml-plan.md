# ML plan: candy wrappers into the bin

**Goal for the demo (Nov 22):** the follower arm finds an empty, crumpled candy wrapper on the table, picks it up and drops it into a bin.

**Approach:** record teleoperated demonstrations with the leader arm, train an [ACT](https://huggingface.co/docs/lerobot/act) policy on them overnight, and run it on the follower tomorrow. ACT is small, trains on one consumer GPU in a few hours, and works well on SO-101 for pick and place.

## Timeline

| When | What |
|------|------|
| Today, while waiting for candies | Rehearsal with paper balls: about 15 episodes, a short practice training, a test run on the arm |
| Today, once candies arrive | Record about 50 real episodes |
| Tonight | Train ACT (about 60k steps or whatever fits the night) |
| Tomorrow morning | Test, record 20 to 30 extra episodes where it fails, fine-tune, prepare the demo |

## Scene setup

Get this right before recording, because the policy only works in a scene that looks like the training data.

- **Two cameras:** `wrist` is mounted on the follower's gripper, `front` is a stationary camera looking at the table and bin. Fix the stationary camera, the bin and the lighting (tape them down) and don't move them again until the demo.
- **One wrapper per episode.** At the demo, just run the policy again for each wrapper.
- **Crumple the wrappers** into loose balls. Flat wrappers are very hard for the gripper. Before recording, check with teleop that you can pick one up reliably.
- **Vary the position** of the wrapper over the whole reachable area, and use 3 to 5 different wrappers.
- **Be consistent.** Move smoothly and in the same style every time. ACT copies your habits, including hesitations.
- **"Recognizing" wrappers:** ACT goes for whatever looks like the objects it saw in training. If it should ignore other things (like full candies), put a few distractors on the table in about a third of the episodes. Skip this if time is tight.

## 0. One-time prep

Log in to Hugging Face (datasets and models are uploaded there) and store your username:

```bash
.venv/bin/hf auth login
.venv/bin/hf auth whoami
export HF_USER=hakami1024
```

`hf auth whoami` prints `user=...`. Set `HF_USER` to that name (on this laptop it is `hakami1024`). The commands below use `$HF_USER`, so run the `export` again in every new terminal.

Find the camera indices. This saves one test picture per camera in `outputs/captured_images/` so you can see which is which:

```bash
.venv/bin/lerobot-find-cameras opencv
```

On our laptop the two USB webcams were `/dev/video0` and `/dev/video2` and the built-in camera `/dev/video4`, but numbers can change after a replug, so check again each session. The commands below assume `front` is index 0 and `wrist` is index 2. **Keep the names `front` and `wrist` the same in every command**, because the trained policy expects exactly those camera names.

## 1. Rehearsal with paper balls (while waiting for candies)

ACT learns one specific task from scratch, so random "general" data doesn't help it. Instead, do a dress rehearsal of the real task with a stand-in object: a crumpled ball of paper, foil or a plastic bag of about the same size. Same bin, same spot, same cameras.

1. Record 10 to 15 episodes. Use the record command from step 2 with `--dataset.repo_id=$HF_USER/rehearsal_paper_to_bin` and `--dataset.num_episodes=15`.
2. Train a short run with the train command from step 3, changing it to `--dataset.repo_id=$HF_USER/rehearsal_paper_to_bin --steps=5000 --policy.push_to_hub=false --output_dir=outputs/train/act_rehearsal --job_name=act_rehearsal`. Look at the time per step in the log to estimate how long the overnight run will take.
3. Run the result on the arm (step 4). It won't be good after 15 episodes. The point is to catch camera, port and command problems now instead of tonight.

If the paper balls look similar to crumpled wrappers, these episodes aren't wasted and can be added to the training data later.

## 2. Record the real episodes

```bash
.venv/bin/lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 \
  --robot.id=hacklab_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90100817-if00 \
  --teleop.id=hacklab_leader \
  --dataset.repo_id=$HF_USER/wrappers_to_bin \
  --dataset.single_task="Pick up the candy wrapper and put it in the bin" \
  --dataset.num_episodes=50 \
  --dataset.episode_time_s=25 \
  --dataset.reset_time_s=10 \
  --display_data=true
```

Keyboard controls while recording:

- **Right arrow:** end the current episode (or the reset pause) early.
- **Left arrow:** throw away the current episode and record it again.
- **Esc:** stop and save.

During the reset pause, put a new wrapper somewhere else on the table and move the arm back to its start pose.

To add more episodes to the same dataset later, run the same command again with `--resume=true`. The dataset is uploaded to the Hub at the end, so the other laptop can train on it.

## 3. Train ACT (overnight)

Run this on the laptop that is **not** recording.

```bash
.venv/bin/lerobot-train \
  --dataset.repo_id=$HF_USER/wrappers_to_bin \
  --policy.type=act \
  --policy.device=cuda \
  --policy.use_amp=true \
  --policy.repo_id=$HF_USER/act_wrappers_to_bin \
  --output_dir=outputs/train/act_wrappers \
  --job_name=act_wrappers \
  --batch_size=8 \
  --steps=60000 \
  --save_freq=10000
```

- On the 4 GB RTX 3050, `--batch_size=8` should fit. If you get "CUDA out of memory", use `--batch_size=4`. See [gpu.md](gpu.md).
- Use the time per step from the rehearsal run to pick `--steps`. If 60,000 steps would take more than about 8 hours, use 30,000 to 40,000 instead.
- A checkpoint is saved every 10,000 steps in `outputs/train/act_wrappers/checkpoints/`, so if something crashes you still have the last one. To continue a crashed run, add `--resume=true --config_path=outputs/train/act_wrappers/checkpoints/last/pretrained_model/train_config.json`.
- At the end the model is uploaded to `$HF_USER/act_wrappers_to_bin` on the Hub.

## 4. Run the policy on the arm

In LeRobot 0.7.0, running a trained policy uses `lerobot-rollout` (`lerobot-record` is only for collecting data now). Use the same camera names and settings as in recording, and set up the scene the same way.

Quick test, 30 seconds, no recording:

```bash
.venv/bin/lerobot-rollout \
  --strategy.type=base \
  --policy.path=outputs/train/act_wrappers/checkpoints/last/pretrained_model \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 \
  --robot.id=hacklab_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30}}" \
  --task="Pick up the candy wrapper and put it in the bin" \
  --duration=30
```

Proper evaluation, 10 recorded episodes with a reset pause between them (the arm returns to its start pose, you place a new wrapper):

```bash
.venv/bin/lerobot-rollout \
  --strategy.type=episodic \
  --policy.path=outputs/train/act_wrappers/checkpoints/last/pretrained_model \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00 \
  --robot.id=hacklab_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30}}" \
  --dataset.repo_id=$HF_USER/eval_wrappers_to_bin \
  --dataset.single_task="Pick up the candy wrapper and put it in the bin" \
  --dataset.num_episodes=10 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=15
```

On the laptop that trained, `--policy.path` points at the local checkpoint. On the other laptop, use the Hub name instead: `--policy.path=$HF_USER/act_wrappers_to_bin`.

Count how many of the 10 wrappers end up in the bin. That's the number to report at the demo.

## 5. If it fails tomorrow

- Note **where** it fails (which part of the table, which wrapper, which step: reaching, grasping or dropping).
- Record 20 to 30 more episodes focused on those positions, with `--resume=true` on the same dataset.
- Fine-tune from the overnight model instead of starting over: same train command, with `--policy.path=outputs/train/act_wrappers/checkpoints/last/pretrained_model` instead of `--policy.type=act`, a new `--output_dir` and fewer steps (10k to 20k).
- If it grabs at the right spot but misses, check that the cameras haven't moved and that the lighting matches the recording.
