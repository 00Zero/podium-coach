# Presenter audio → transcript → events (Adam)

Lives in `audio/`. A standalone process on Adam's laptop. Its only output is `transcript_chunk` events posted to `PODIUM_SERVER_URL`. It never imports anything from `server/`.

## Build order — do not skip steps

1. **File in, events out.** `python audio/transcribe.py demo/sample-talk.m4a` → transcribes the file in 10-second chunks, prints each chunk, posts each as `transcript_chunk`. Proves the whole pipeline with no microphone and no browser. This is also how `npm run demo` / `make demo` replays the fixture later.
2. **Laptop mic, live.** `python audio/transcribe.py --mic` → same pipeline from the default input device, 10-second chunks. This is the demo if step 3 fails.
3. **Meet tab audio.** `audio/capture.html` opened in Chrome on the laptop that's in the Meet: `getDisplayMedia({video:true, audio:true})`, pick the Meet tab, tick "Share tab audio", `MediaRecorder` 10-second chunks, POST each chunk to a tiny local route (`audio/chunk_server.py`, port 3100) that runs the same transcribe-and-post code. Chrome only.

Gate: live transcript on screen by 12:50 or Adam hands this to Reed and takes the audience rubric.

## Transcription

**Primary: Deepgram** (free $200 credit, no card). Pre-recorded endpoint on each chunk is fine; streaming is not required for a 15-second cue loop.

```
POST https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&filler_words=true&punctuate=true
Authorization: Token $DEEPGRAM_API_KEY
Content-Type: audio/wav   (or audio/webm for MediaRecorder chunks)
```

Use `results.channels[0].alternatives[0].words[]` → `{word, start, end}`. Mark `filler: true` when the word (lowercased, punctuation stripped) is in `config/cues.json → filler_words`. Deepgram emits "um"/"uh" as words only when `filler_words=true`.

**Fallback: OpenAI transcription** (`whisper-1` or `gpt-4o-transcribe`) with `timestamp_granularities=["word"]` and a prompt seed so fillers aren't dropped: `"Um, uh, like, you know, so, okay so..."`. Same output shape.

**Fully offline fallback:** `faster-whisper` with `word_timestamps=True`. Only if both APIs are down. 15 minutes to install; don't start here.

## Metrics (computed in `audio/metrics.py`, over a rolling 60 s window of words)

- `wpm_60s`: words in the last 60 s.
- `fillers_per_min`: words with `filler: true` in the last 60 s.
- `seconds_since_pause`: now minus the end of the last gap ≥ `pause_gap_s` (1.5 s) between consecutive words.

Attach as `payload.metrics` on every chunk. Thresholds live in `config/cues.json`, not in code.

## Sending

```python
import os, requests
SERVER = os.environ.get("PODIUM_SERVER_URL", "http://localhost:3000")

def send(event):
    try:
        r = requests.post(f"{SERVER}/events", json=event, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print("send failed, continuing:", e)
```

Also append every event to `audio/events.local.jsonl` so nothing is lost if the server is down; the recap can replay from it.

## Before the server exists

`python audio/stub_server.py` — FastAPI, one route, appends to `events.jsonl`, prints each event. Point `PODIUM_SERVER_URL` at it. When Reed's tunnel URL arrives, change the env var and run:

```
curl -X POST $PODIUM_SERVER_URL/events -H 'Content-Type: application/json' \
  -d '{"type":"transcript_chunk","ts":"2026-09-12T20:00:00.000Z","payload":{"text":"hello from adam"}}'
```

Reed sees "hello from adam" in his log → integrated.

## Env

```
DEEPGRAM_API_KEY=
OPENAI_API_KEY=          # fallback transcription only
PODIUM_SERVER_URL=http://localhost:3000
```
