"""Presenter audio -> Deepgram -> transcript_chunk events (docs/PRESENTER-AUDIO.md).

    python audio/transcribe.py demo/sample-talk.m4a      # file in, events out
    python audio/transcribe.py --mic                     # live, default input device

Standalone: posts to PODIUM_SERVER_URL and imports nothing from server/.
Every event is also appended to audio/events.local.jsonl. A failed post is
logged and ignored -- the loop never dies because the server is down.
"""

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import RollingMetrics, flag_fillers, load_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SERVER = os.environ.get("PODIUM_SERVER_URL", "http://localhost:3000")
LOCAL_LOG = Path(__file__).resolve().parent / "events.local.jsonl"

SAMPLE_RATE = 16000
DEEPGRAM_URL = (
    "https://api.deepgram.com/v1/listen"
    "?model=nova-3&smart_format=true&filler_words=true&punctuate=true"
)


# ---------------------------------------------------------------- plumbing

def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def send(event):
    """Append locally, then post. Never raises."""
    try:
        with open(LOCAL_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print("local log failed, continuing:", e, flush=True)
    try:
        r = requests.post(SERVER + "/events", json=event, timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        print("send failed, continuing:", e, flush=True)
        return False


def wav_bytes(pcm, sample_rate=SAMPLE_RATE):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def read_pcm_wav(path):
    """-> (pcm bytes, sample rate, channels).

    afconvert writes WAVE_FORMAT_EXTENSIBLE headers, which Python's `wave`
    module refuses, so walk the RIFF chunks ourselves.
    """
    raw = Path(path).read_bytes()
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file: %s" % path)
    pos, rate, channels, pcm = 12, SAMPLE_RATE, 1, b""
    while pos + 8 <= len(raw):
        cid = raw[pos:pos + 4]
        size = int.from_bytes(raw[pos + 4:pos + 8], "little")
        body = raw[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            channels = int.from_bytes(body[2:4], "little")
            rate = int.from_bytes(body[4:8], "little")
        elif cid == b"data":
            pcm = body
        pos += 8 + size + (size % 2)
    return pcm, rate, channels


def to_wav_file(path):
    """Any audio file -> 16 kHz mono 16-bit WAV, using macOS's built-in afconvert."""
    out = Path(tempfile.mkdtemp(prefix="podium-")) / "audio.wav"
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@%d" % SAMPLE_RATE, "-c", "1", str(path), str(out)],
        check=True, capture_output=True,
    )
    return out


# ---------------------------------------------------------- transcription

def deepgram_words(audio, content_type="audio/wav"):
    """-> (text, [{w, start, end, punctuated}]). Returns ('', []) on failure."""
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        print("no DEEPGRAM_API_KEY, skipping transcription", flush=True)
        return "", []
    headers = {"Authorization": "Token " + key, "Content-Type": content_type}
    for attempt in (1, 2):
        try:
            r = requests.post(DEEPGRAM_URL, headers=headers, data=audio, timeout=25)
            r.raise_for_status()
            alt = r.json()["results"]["channels"][0]["alternatives"][0]
            words = [
                {"w": w["word"], "start": float(w["start"]), "end": float(w["end"]),
                 "punctuated": w.get("punctuated_word", w["word"])}
                for w in alt.get("words", [])
            ]
            return alt.get("transcript", ""), words
        except Exception as e:
            print("deepgram attempt %d failed: %s" % (attempt, e), flush=True)
            time.sleep(0.5)
    return openai_words(audio, content_type)


def openai_words(audio, content_type="audio/wav"):
    """Fallback only, and only if OPENAI_API_KEY is set."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return "", []
    ext = "webm" if "webm" in content_type else "wav"
    try:
        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": "Bearer " + key},
            files={"file": ("chunk." + ext, audio, content_type)},
            data=[("model", "whisper-1"), ("response_format", "verbose_json"),
                  ("timestamp_granularities[]", "word"),
                  ("prompt", "Um, uh, like, you know, so, okay so...")],
            timeout=30,
        )
        r.raise_for_status()
        j = r.json()
        words = [{"w": w["word"], "start": float(w["start"]), "end": float(w["end"]),
                  "punctuated": w["word"]} for w in j.get("words", [])]
        print("used openai fallback", flush=True)
        return j.get("text", ""), words
    except Exception as e:
        print("openai fallback failed, continuing:", e, flush=True)
        return "", []


# ----------------------------------------------------------------- events

class ChunkPipeline:
    """One talk: keeps the rolling window, turns audio chunks into events."""

    def __init__(self, config=None, verbose=True):
        self.config = config or load_config()
        self.metrics = RollingMetrics(self.config)
        self.verbose = verbose

    def handle(self, audio, chunk_start, chunk_end, content_type="audio/wav"):
        text, words = deepgram_words(audio, content_type)
        for w in words:                      # Deepgram times are chunk-relative
            w["start"] = round(w["start"] + chunk_start, 2)
            w["end"] = round(w["end"] + chunk_start, 2)
        flag_fillers(words, self.config["filler_words"])
        self.metrics.add_words(words)
        m = self.metrics.snapshot(chunk_end)

        event = {
            "type": "transcript_chunk",
            "ts": iso_now(),
            "payload": {
                "text": text,
                "words": [{"w": w["w"], "start": w["start"], "end": w["end"],
                           "filler": w["filler"], **({"filler_head": True} if w.get("filler_head") else {})}
                          for w in words],
                "chunk_start": round(chunk_start, 2),
                "chunk_end": round(chunk_end, 2),
                "metrics": m,
            },
        }
        send(event)
        if self.verbose:
            print("[%5.1f-%5.1fs] wpm %3s | fillers %4s/min | since pause %5ss | %s"
                  % (chunk_start, chunk_end, m["wpm_60s"], m["fillers_per_min"],
                     m["seconds_since_pause"], text or "(silence)"), flush=True)
        return event


def post_session_start(outline_path=None, planned_minutes=None):
    outline = []
    if outline_path:
        for line in Path(outline_path).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            title, _, mins = line.rpartition("(")
            try:
                outline.append({"title": title.strip(), "minutes": float(mins.rstrip(") "))})
            except ValueError:
                outline.append({"title": line, "minutes": 1.0})
    total = planned_minutes or sum(s["minutes"] for s in outline) or 7
    send({"type": "session_start", "ts": iso_now(),
          "payload": {"outline": outline, "planned_minutes": round(total, 2)}})
    return outline


# ------------------------------------------------------------------ modes

def run_file(path, chunk_s=10.0, realtime=False, pipeline=None):
    pcm, rate, channels = read_pcm_wav(to_wav_file(path))
    pipe = pipeline or ChunkPipeline()
    bytes_per_s = rate * channels * 2
    per_chunk = int(chunk_s * bytes_per_s)
    print("%s: %.1fs of audio, %gs chunks" % (Path(path).name, len(pcm) / bytes_per_s, chunk_s), flush=True)
    for idx in range(0, max(1, -(-len(pcm) // per_chunk))):
        frames = pcm[idx * per_chunk:(idx + 1) * per_chunk]
        if not frames:
            break
        start = idx * chunk_s
        end = start + len(frames) / float(bytes_per_s)
        t0 = time.time()
        pipe.handle(wav_bytes(frames, rate), start, end)
        if realtime:
            time.sleep(max(0.0, (end - start) - (time.time() - t0)))
    return pipe


def run_mic(chunk_s=10.0, pipeline=None):
    import queue
    import sounddevice as sd

    pipe = pipeline or ChunkPipeline()
    q = queue.Queue()

    def cb(indata, frames, time_info, status):
        if status:
            print("audio status:", status, flush=True)
        q.put(bytes(indata))

    per_chunk = int(chunk_s * SAMPLE_RATE) * 2  # bytes, 16-bit mono
    print("listening on default input (%s). Ctrl-C to stop."
          % sd.query_devices(kind="input")["name"], flush=True)
    buf, idx = b"", 0
    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=cb):
        try:
            while True:
                buf += q.get()
                if len(buf) >= per_chunk:
                    chunk, buf = buf[:per_chunk], buf[per_chunk:]
                    # time is measured along the audio stream, not the wall clock,
                    # so a slow Deepgram call never shifts the word timestamps
                    pipe.handle(wav_bytes(chunk), idx * chunk_s, (idx + 1) * chunk_s)
                    idx += 1
        except KeyboardInterrupt:
            print("\nstopped.", flush=True)
    return pipe


def main():
    ap = argparse.ArgumentParser(description="presenter audio -> transcript_chunk events")
    ap.add_argument("audio", nargs="?", help="audio file; omit with --mic")
    ap.add_argument("--mic", action="store_true", help="live from the default input device")
    ap.add_argument("--chunk-s", type=float, default=10.0)
    ap.add_argument("--realtime", action="store_true", help="file mode: pace it like a live talk")
    ap.add_argument("--outline", help="post session_start from this outline file first")
    ap.add_argument("--session-end", action="store_true", help="post session_end when done")
    args = ap.parse_args()

    print("posting to %s" % SERVER, flush=True)
    if args.outline:
        post_session_start(args.outline)

    if args.mic:
        run_mic(args.chunk_s)
    elif args.audio:
        run_file(args.audio, args.chunk_s, args.realtime)
    else:
        ap.error("give an audio file or --mic")

    if args.session_end:
        send({"type": "session_end", "ts": iso_now(), "payload": {}})


if __name__ == "__main__":
    main()
