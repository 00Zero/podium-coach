"""Backstop driver — replays the demo/ fixture as transcript_chunk events.

This is NOT transcription. It posts the sample talk script from demo/ with the
metrics the script is written to produce, so the podium phone shows real cues on
camera when Adam's live audio pipeline is not running. Frame scoring and the cue
loop are untouched and real; only the transcript side is simulated.

Lives in server/ because demo/ belongs to Adam. Usage:

    server/.venv/bin/python server/drive_demo.py [--server URL]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone

OUTLINE = [
    {"title": "Why this matters", "minutes": 0.5},
    {"title": "Demo", "minutes": 0.75},
    {"title": "Ask", "minutes": 0.25},
]
PLANNED_MINUTES = 1.5

# (seconds after start, text, wpm_60s, fillers_per_min, seconds_since_pause).
# The numbers follow demo/sample-talk-script.md: fast and filler-heavy in the
# opening, then the no-pause block, then over time at the end.
SCRIPT: list[tuple[float, str, int, float, float]] = [
    (0, "So, um, thanks for having me. I run a tech community in Seattle", 150, 3.0, 4.0),
    (10, "and I've watched, like, a hundred people give talks, and the thing is,", 168, 5.0, 9.0),
    (20, "nobody on stage can see the clock. They can't see the room.", 172, 5.0, 6.0),
    (30, "Basically it's a phone, and the phone shows one thing at a time,", 180, 4.0, 18.0),
    (40, "so right now it would be showing me a countdown and maybe a cue", 186, 3.0, 28.0),
    (50, "and the cue is six words max because you can only read six words at a glance", 190, 3.0, 38.0),
    (60, "and the audio comes from the Google Meet tab which means no bots and no APIs", 192, 2.0, 48.0),
    (70, "and there's a second phone at the back of the room pointed at you all", 188, 2.0, 58.0),
    (80, "which scores how many of you are looking up versus at your laptops", 185, 2.0, 68.0),
    (90, "So, uh, the ask is simple. If you give talks, try it.", 160, 4.0, 5.0),
    (100, "If you organize events, put a phone on the podium.", 155, 3.0, 8.0),
    (110, "And if you're a judge, this is the part where you lean in. Thanks.", 150, 3.0, 6.0),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def post(server: str, event: dict) -> None:
    """Post one event. A failure is printed and ignored, exactly like Adam's sender."""
    request = urllib.request.Request(
        f"{server}/events",
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
    except Exception as exc:
        print(f"  send failed, continuing: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://localhost:3000")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback multiplier.")
    args = parser.parse_args()

    print(f"session_start: {PLANNED_MINUTES} min, {len(OUTLINE)} sections")
    post(args.server, {"type": "session_start", "ts": now_iso(),
                       "payload": {"outline": OUTLINE, "planned_minutes": PLANNED_MINUTES}})

    started = time.monotonic()
    for offset, text, wpm, fillers, since_pause in SCRIPT:
        target = started + offset / args.speed
        time.sleep(max(0.0, target - time.monotonic()))
        print(f"  t={offset:>3.0f}s wpm={wpm} fillers={fillers} pause={since_pause} | {text[:48]}")
        post(args.server, {
            "type": "transcript_chunk",
            "ts": now_iso(),
            "payload": {
                "text": text,
                "chunk_start": offset,
                "chunk_end": offset + 10,
                "metrics": {
                    "wpm_60s": wpm,
                    "fillers_per_min": fillers,
                    "seconds_since_pause": since_pause,
                },
            },
        })

    print("session_end")
    post(args.server, {"type": "session_end", "ts": now_iso(), "payload": {}})


if __name__ == "__main__":
    main()
