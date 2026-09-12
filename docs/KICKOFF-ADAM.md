# Kickoff prompt — Adam's Claude Code session

Paste into Claude Code from the repo root on branch `adam/audio`.

```
Read CLAUDE.md, docs/HANDOFFS.md, docs/CONTRACT.md, and docs/PRESENTER-AUDIO.md. I'm Adam. I'm not a developer; explain choices in one line each and don't ask me to debug — if something fails, diagnose it and propose the fix. I own audio/, config/, recap/, demo/, docs/, README.md. Branch adam/audio. Never touch server/.

Step 1 (20 min): audio/stub_server.py — FastAPI, POST /events appends to events.jsonl and prints one line per event; port 3000. Then audio/transcribe.py that takes an audio file, splits it into 10-second chunks, sends each to Deepgram (nova-3, filler_words=true, smart_format, punctuate), builds the transcript_chunk payload exactly as in CONTRACT.md — words with start/end and filler flags from config/cues.json filler_words — computes the rolling metrics in audio/metrics.py (wpm_60s, fillers_per_min, seconds_since_pause with a 1.5 s gap), and POSTs each chunk to PODIUM_SERVER_URL. Also append every event to audio/events.local.jsonl. Sending must never crash the loop. Test against the stub with any short audio file; if I don't have one yet, generate a 30-second one with macOS `say` so we're not blocked.

Step 2: `--mic` flag — same pipeline from the default input device, live, 10-second chunks, transcript printed as it arrives. Tell me when it's running so I can talk into it.

Step 3: audio/capture.html + audio/chunk_server.py (port 3100) — Chrome page that calls getDisplayMedia with audio, MediaRecorder 10 s chunks, POSTs each chunk to chunk_server which runs the same transcribe-and-post code. Only after steps 1 and 2 work.

Step 4: demo/replay.py per docs/DEMO.md, and a Makefile with `make demo`. Then recap/render.py: GET /events from the server, fill recap/prompt.md, call Claude Sonnet with tool use for the JSON schema, render a plain HTML page at recap/out/recap.html. Test it against events.jsonl from step 1.

Rules: no new dependencies needing accounts without asking. Keep .env out of git; update .env.example if you add a key. Commit after each step with a plain message. After each step tell me what works, what doesn't, and what you'd cut next. If Reed's tunnel URL arrives, I'll paste it; then curl a "hello from adam" event to it before switching PODIUM_SERVER_URL.
```

## Before pasting

1. `git checkout -b adam/audio`
2. Deepgram key in `.env` (console.deepgram.com → API keys; $200 free credit, no card).
3. `ANTHROPIC_API_KEY` in `.env` for the recap.
4. Record the 90-second sample talk on your phone as soon as `demo/sample-talk-script.md` exists — that's the fixture and the video insurance.
