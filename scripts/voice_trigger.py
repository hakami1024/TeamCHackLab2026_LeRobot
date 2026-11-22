"""Say "Hey Claude, clean the table" to start one recorded policy run on the follower.

Offline: parec -> Vosk (CPU) -> scripts/test_policy.sh (pins --robot.id=hacklab_follower)
-> scripts/save_demo.sh (outputs/demos/<run>/front.mp4, wrist.mp4, both.mp4).
Dry-run unless --live. Start it through scripts/voice_trigger.sh.

  scripts/voice_trigger.sh                         # mic, beeps and prints the command
  scripts/voice_trigger.sh --ptt                   # noisy room: press ENTER, then speak
  scripts/voice_trigger.sh --live                  # MOVES THE ARM on the phrase
  scripts/voice_trigger.sh --policy <dir>          # or VOICE_POLICY=<dir>, ACT checkpoints only
  scripts/voice_trigger.sh --mic <source>          # a close mic, names: pactl list short sources
  scripts/voice_trigger.sh --min-conf 0.8          # stricter, if it triggers by itself
  scripts/voice_trigger.sh --text                  # type phrases, no mic
  ROLLOUT="python scripts/camera_lock.py lerobot-rollout" scripts/voice_trigger.sh --live   # no camera window

A trigger beeps and waits 3 s; Ctrl-C in that window cancels it.
The mic is off from the beep to the end of the run, so phrases said then are dropped.
Ctrl-C during a run lets the rollout return to rest and save the video, then exits.
Press it only once: a second one force-quits lerobot-rollout.
"""

import argparse
import array
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import termios
import time
import wave
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = "outputs/train/act_v10_ft/checkpoints/011000/pretrained_model"
MODEL = Path.home() / ".cache/vosk/vosk-model-small-en-us-0.15"
# Must be free before a run (same paths as test_policy.sh)
DEVICES = (
    "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90103156-if00",
    "/dev/v4l/by-id/usb-046d_081d_9D9D0F90-video-index0",
    "/dev/v4l/by-id/usb-Generic_USB_HD_Camera_200910120001-video-index0",
)
# These take a few seconds to open the devices, so also look for them by name
RUNNERS = {
    "lerobot-rollout", "lerobot-record", "lerobot-teleoperate", "lerobot-calibrate",
    "test_policy.sh", "rollout_with_video.py",
}  # fmt: skip
MIN_FREE = 1e9  # bytes, a run writes ~50 MB of video

RATE = 16000
GREETS = ("hey", "hi", "okay")
NAMES = ("claude", "cloud", "clod")  # what the small model hears for "Claude"
VERB, OBJECT = "clean", "table"
FILLER = {"the", "up", "please", "[unk]"}
NEGATIONS = {"don't", "not", "never"}
# With only the target in the grammar, similar speech gets forced onto it. These absorb it.
DECOYS = [
    "don't", "not", "never", "hey", "hey google", "cleaning", "clean it", "clean the floor",
    "clean code", "the table", "tablet", "able", "label", "stable", "loud", "crowd",
]  # fmt: skip
NAME_CONF = 0.4  # lower than for the command, the spellings of "Claude" share the confidence
JOIN_S = 3.0  # allowed pause between "hey claude" and "clean the table"
SPAN_S = 3.0  # longest "clean ... table"
SETTLE_S = 0.8  # chatter hides the end of an utterance, so cut it this long after the phrase
PTT_S = 6.0
COUNTDOWN_S = 3

Word = dict  # Vosk's {"word", "conf", "start", "end"}, times in seconds since the mic opened


def grammar() -> str:
    command = [f"{VERB} the {OBJECT}", f"{VERB} up the {OBJECT}", f"please {VERB} the {OBJECT}"]
    wake = [f"{greet} {name}" for greet in GREETS for name in NAMES]
    return json.dumps(wake + [f"{w} {command[0]}" for w in wake] + command + DECOYS + ["[unk]"])


class Phrase:
    """Finds wake + command in the last seconds of words, whatever noise surrounds them."""

    def __init__(self, min_conf: float, ptt: bool = False) -> None:
        self.min_conf = min_conf
        self.ptt = ptt  # the key press replaces "hey claude"
        self.words: list[Word] = []

    def heard(self, new: list[Word]) -> bool:
        self.words += new
        for verb, word in enumerate(self.words):
            if word["word"] != VERB:
                continue
            end = verb + 1
            while end < len(self.words) and self.words[end]["word"] in FILLER:
                end += 1
            if end == len(self.words) or self.words[end]["word"] != OBJECT:
                continue
            if self.words[end]["end"] - word["start"] > SPAN_S:
                continue
            first = verb
            while first and self.words[first - 1]["word"] in FILLER:
                first -= 1
            name = None
            if not self.ptt:
                if first < 2 or self.words[first - 2]["word"] not in GREETS:
                    continue
                name = self.words[first - 1]
                if name["word"] not in NAMES or word["start"] - name["end"] > JOIN_S:
                    continue
                first -= 2
            since = self.words[first]["start"] - 1.5
            if any(w["word"] in NEGATIONS and w["start"] >= since for w in self.words[:verb]):
                continue
            scored = [(word, self.min_conf), (self.words[end], self.min_conf)]
            if name:
                scored.append((name, NAME_CONF))
            if unsure := [f"{w['word']} {w['conf']:.2f}" for w, need in scored if w["conf"] < need]:
                if end >= len(self.words) - len(new):  # report it once
                    print(f"  not sure enough ({', '.join(unsure)}), say it again closer to the mic", flush=True)
                continue
            self.words.clear()
            return True
        if self.words:
            self.words = [w for w in self.words if w["end"] >= self.words[-1]["end"] - 15]
        return False


def busy() -> str | None:
    """What holds the arm or cameras. Only reads /proc, never opens a device."""
    devices = {os.path.realpath(d) for d in DEVICES}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            argv = (proc / "cmdline").read_bytes().decode(errors="replace").split("\0")
            if RUNNERS & {Path(a).name for a in argv[:2]}:
                return f"{' '.join(argv[:2])} (pid {proc.name})"
            for fd in (proc / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target in devices:
                    return f"{Path(argv[0]).name} (pid {proc.name}) holds {target}"
        except OSError:
            continue
    return None


def blocker() -> str | None:
    if holder := busy():
        return f"arm or camera is busy: {holder}"
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        return "less than 1 GB of disk left for the video"
    return None


def beep(*tones: int) -> None:
    pcm = array.array("h")
    for hz in tones:
        pcm.extend(int(12000 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(int(0.15 * RATE)))
    cmd = ["pacat", "--raw", "--format=s16le", f"--rate={RATE}", "--channels=1"]
    try:
        subprocess.run(cmd, input=pcm.tobytes(), timeout=2, capture_output=True)
    except (OSError, subprocess.TimeoutExpired):
        print("\a", end="", flush=True)


def typed() -> Iterator[list[Word]]:
    for line in sys.stdin:
        now = time.monotonic()
        words = re.sub(r"[^a-z' ]", " ", line.lower()).split()
        yield [{"word": w, "conf": 1.0, "start": now, "end": now} for w in words]


def audio(args: argparse.Namespace) -> Iterator[bytes]:
    if args.wav:
        with wave.open(args.wav) as w:
            if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 1, 2):
                sys.exit("--wav needs 16 kHz mono s16: ffmpeg -i in -ar 16000 -ac 1 -c:a pcm_s16le out.wav")
            while chunk := w.readframes(2000):
                yield chunk
        return

    cmd = ["parec", "--raw", "--format=s16le", f"--rate={RATE}", "--channels=1", "--latency-msec=100"]
    if args.mic:
        cmd.append(f"--device={args.mic}")
    mic = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert mic.stdout is not None
    try:
        first, limit, read = True, PTT_S * RATE * 2, 0
        while chunk := mic.stdout.read(4000):
            if first and args.ptt:
                print(f'Speak now ({PTT_S:.0f} s): "clean the table"', flush=True)
            first = False
            yield chunk
            read += len(chunk)
            if args.ptt and read >= limit:
                return
        sys.exit("The mic stream ended. Check `pactl list short sources` and --mic.")
    finally:
        mic.terminate()
        mic.wait()


def spoken(args: argparse.Namespace, model) -> Iterator[list[Word]]:
    from vosk import KaldiRecognizer

    def recognizer():
        rec = KaldiRecognizer(model, RATE, grammar())
        rec.SetWords(True)
        return rec

    def result(raw: str, offset: float) -> list[Word]:
        words = json.loads(raw).get("result", [])
        return [{**w, "start": w["start"] + offset, "end": w["end"] + offset} for w in words]

    rec, offset, seconds = recognizer(), 0.0, 0.0
    complete_at = None
    chunks = audio(args)
    try:
        for chunk in chunks:
            seconds += len(chunk) / 2 / RATE
            if rec.AcceptWaveform(chunk):
                complete_at = None
                yield result(rec.Result(), offset)
                continue
            partial = json.loads(rec.PartialResult())["partial"].split()
            if VERB not in partial or OBJECT not in partial:
                complete_at = None
            elif complete_at is None:
                complete_at = seconds
            elif seconds - complete_at >= SETTLE_S:
                words = result(rec.FinalResult(), offset)
                rec, offset, complete_at = recognizer(), seconds, None
                yield words
        yield result(rec.FinalResult(), offset)
    finally:
        chunks.close()


def countdown() -> bool:
    try:
        beep(880, 1320)
        for left in range(COUNTDOWN_S, 0, -1):
            print(f"Starting in {left}... (Ctrl-C cancels)", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCancelled.", flush=True)
        return False
    return True


def launch(cmd: list[str], name: str) -> bool:
    """Run and save the demo; False if the operator asked to stop."""
    stopped = False

    def stop(signum, frame) -> None:
        nonlocal stopped
        stopped = True

    # A handler, not SIG_IGN: exec resets handlers in the child, so Ctrl-C still reaches the rollout.
    # Don't forward it: the child already gets it, and a second signal skips the return to rest.
    signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous = [signal.signal(s, stop) for s in signals]
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)  # no stale keys into the calibration prompt
        print("If it asks about calibration, press a blank ENTER, never 'c'.", flush=True)
        code = subprocess.run(cmd, cwd=ROOT).returncode
        print(f"Run {'finished' if code == 0 else f'FAILED or was stopped (exit {code})'}.", flush=True)
        # Also after a stop, the rollout saves what it recorded. Own session, so Ctrl-C can't cut it short.
        save = ["bash", str(ROOT / "scripts/save_demo.sh"), name]
        if subprocess.run(save, cwd=ROOT, start_new_session=True).returncode:
            print("No demo video was saved for this run.", flush=True)
    finally:
        for s, handler in zip(signals, previous, strict=True):
            signal.signal(s, handler)
    return not stopped


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy", default=os.environ.get("VOICE_POLICY", POLICY))
    p.add_argument("--live", action="store_true", help="really run the arm")
    p.add_argument("--ptt", action="store_true", help="push-to-talk: ENTER, then speak")
    p.add_argument("--mic", help="PulseAudio/PipeWire source (default: system default)")
    p.add_argument("--min-conf", type=float, default=0.65, help="for 'clean' and 'table', 0..1")
    p.add_argument("--model", type=Path, default=MODEL)
    test = p.add_mutually_exclusive_group()
    test.add_argument("--text", action="store_true", help="read phrases from stdin")
    test.add_argument("--wav", help="read a recording")
    args = p.parse_args()

    testing = bool(args.text or args.wav)
    if args.live and testing:
        p.error("--text and --wav are dry-run only")
    if args.live and not sys.stdin.isatty():
        p.error("--live needs a terminal for the calibration prompt and Ctrl-C")
    policy = (ROOT / Path(args.policy).expanduser()).resolve()
    if not (policy / "config.json").is_file():
        p.error(f"no config.json in {policy}")
    if json.loads((policy / "config.json").read_text()).get("type") != "act":
        p.error("test_policy.sh only has the flags for ACT; SmolVLA needs a rename_map")

    model = None
    if not args.text:
        try:
            from vosk import Model, SetLogLevel
        except ImportError:
            p.error("Vosk is not installed; only --text works")
        if not args.model.is_dir():
            p.error(f"no Vosk model in {args.model}")
        SetLogLevel(-1)
        model = Model(str(args.model))

    print(f"{'LIVE, the arm will move' if args.live else 'DRY-RUN'} | policy: {policy}", flush=True)
    while True:
        if args.ptt and not testing:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
            try:
                input("Press ENTER to talk (Ctrl-C quits) ")
            except EOFError:
                return
        else:
            print('Listening for "Hey Claude, clean the table" (Ctrl-C quits)', flush=True)

        phrase = Phrase(args.min_conf, args.ptt)
        utterances = typed() if args.text else spoken(args, model)
        for words in utterances:
            if any(w["word"] != "[unk]" for w in words):
                print("  heard:", " ".join(f"{w['word']}({w['conf']:.2f})" for w in words), flush=True)
            if not phrase.heard(words):
                continue
            name = f"voice_{time.strftime('%Y%m%d_%H%M%S')}"
            cmd = ["bash", str(ROOT / "scripts/test_policy.sh"), str(policy), name]
            if testing:
                print(f"DRY-RUN would run: {shlex.join(cmd)}", flush=True)
                continue
            utterances.close()  # mic off, so nothing queues up and the beep isn't heard
            if args.live and (reason := blocker()):
                print(f"Ignored, {reason}", flush=True)
                beep(330)
            elif countdown():
                reason = blocker()  # again, it may have changed during the countdown
                if not args.live:
                    print(f"DRY-RUN would run: {shlex.join(cmd)}", flush=True)
                    print(f"  then save outputs/demos/{name}/", flush=True)
                    if reason:
                        print(f"  (live would ignore this now, {reason})", flush=True)
                elif reason:
                    print(f"Ignored, {reason}", flush=True)
                    beep(330)
                elif not launch(cmd, name):
                    return
            break
        else:
            if testing or not args.ptt:
                return
            print("Didn't catch that.", flush=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
