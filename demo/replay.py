"""Replay a whole talk into the server with no live capture (docs/DEMO.md).

    make demo            # or: python demo/replay.py

Posts session_start from the outline, streams the sample audio through
audio/transcribe.py in real time, posts the audience frames 15 s apart, then
session_end. This is the insurance policy for the video: if the microphone,
the Meet tab, or the phones misbehave, this still produces a full event log
and a real recap.
"""

import argparse
import base64
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "audio"))

from transcribe import SERVER, iso_now, post_session_start, run_file, send  # noqa: E402

DEFAULT_AUDIO = [ROOT / "demo" / "sample-talk.m4a",      # Adam's real recording
                 ROOT / "demo" / "sample-talk-say.m4a"]  # generated stand-in


def pick_audio(given):
    if given:
        return Path(given)
    for p in DEFAULT_AUDIO:
        if p.exists():
            return p
    sys.exit("no audio: put a recording at demo/sample-talk.m4a")


def frame_sender(frames, every_s, stop):
    """Post one audience_frame every `every_s` until told to stop."""
    for i, path in enumerate(frames):
        if stop.wait(0 if i == 0 else every_s):
            return
        try:
            b64 = base64.b64encode(path.read_bytes()).decode()
        except Exception as e:
            print("frame %s unreadable, skipping: %s" % (path.name, e), flush=True)
            continue
        send({"type": "audience_frame", "ts": iso_now(),
              "payload": {"image_b64": b64, "width": 640, "height": 480,
                          "source": "replay:" + path.name}})
        print("posted %s" % path.name, flush=True)


def main():
    ap = argparse.ArgumentParser(description="replay a talk into the server")
    ap.add_argument("--audio", help="default: demo/sample-talk.m4a, else the generated stand-in")
    ap.add_argument("--outline", default=str(ROOT / "demo" / "sample-outline.txt"))
    ap.add_argument("--frames", default=str(ROOT / "demo" / "audience"))
    ap.add_argument("--frame-every-s", type=float, default=15.0)
    ap.add_argument("--chunk-s", type=float, default=10.0)
    ap.add_argument("--fast", action="store_true", help="don't pace it like a live talk")
    args = ap.parse_args()

    audio = pick_audio(args.audio)
    frames = sorted(Path(args.frames).glob("*.jpg")) + sorted(Path(args.frames).glob("*.jpeg"))
    print("replay -> %s\n  audio: %s\n  frames: %s"
          % (SERVER, audio.name, "%d in %s" % (len(frames), args.frames) if frames
             else "none yet (demo/audience/ is empty; engagement will be missing)"), flush=True)

    post_session_start(args.outline)

    stop = threading.Event()
    thread = None
    if frames and not args.fast:
        thread = threading.Thread(target=frame_sender, args=(frames, args.frame_every_s, stop), daemon=True)
        thread.start()

    try:
        run_file(audio, chunk_s=args.chunk_s, realtime=not args.fast)
    finally:
        stop.set()
        if thread:
            thread.join(timeout=2)

    if frames and args.fast:            # fast mode: get the frames in anyway
        for i, path in enumerate(frames):
            send({"type": "audience_frame", "ts": iso_now(),
                  "payload": {"image_b64": base64.b64encode(path.read_bytes()).decode(),
                              "width": 640, "height": 480, "source": "replay:" + path.name}})

    send({"type": "session_end", "ts": iso_now(), "payload": {}})
    print("done. recap: make recap", flush=True)


if __name__ == "__main__":
    main()
