# Handoffs

## Split

**Reed:** the server, the `/audience` camera page on his iPhone, frame scoring, the cue loop, `/state`, `/presenter` page. Branch `reed/server`, directory `server/`.

**Adam:** presenter audio → transcript → `transcript_chunk` events, `config/cues.json`, the recap prompt and `/end` page, demo fixtures, README, video, write-up, social post. Branch `adam/audio`, directories `audio/`, `config/`, `recap/`, `demo/`, `docs/`.

## What Adam needs from Reed first (next 10 minutes)

1. Server up with `POST /events` per `docs/CONTRACT.md`: accept `{type, ts, payload}`, append to an in-memory list, log it.
2. `cloudflared tunnel --url http://localhost:3000` → send Adam the HTTPS URL. Phones need HTTPS for the camera; venue Wi-Fi may block LAN.
3. `GET /state` per the contract — what the presenter page on Adam's iPhone reads.

## What Adam gives Reed

- `transcript_chunk` events every ~10 s with word timestamps, fillers flagged, and rolling metrics attached. Adam curls a "hello from adam" event into the endpoint before sending anything real.
- `config/cues.json`: thresholds, priority order, fallback text per category. Reed's cue loop reads it; Adam tunes it.
- `recap/prompt.md` and the `/end` page, which reads `GET /events`.
- `demo/`: 90 s sample audio, outline, six audience frames, `replay.py`.

## Reed's build order

1. Server + tunnel.
2. `/audience` on the iPhone per `docs/AUDIENCE-PAGE.md`. Gate: one frame from the phone lands in the log over the tunnel.
3. Frame → Claude Haiku vision with the fixed rubric → `audience_score` event. Sampled frames only; no local models.
4. Cue loop every 15 s: read the last 60 s, pick a category by `config/cues.json` priority, Sonnet phrases it in ≤6 words, fallback text if the call fails, expose on `/state`. `/presenter` page: dark, cue at ~64 px, countdown at ~40 px, wake lock, nothing else.
5. Slide detection only if step 4 is done before 2:15.

## Adam's build order

Per `docs/PRESENTER-AUDIO.md`: file → mic → Meet tab. Then `demo/`, `recap/`, README, video.

## Clock

- 12:50 — Adam has a live transcript on screen, or hands audio to Reed and takes the audience rubric and recap.
- 1:45 — a cue shows on the presenter phone from real events.
- 2:15 — last moment to start slide detection.
- 2:45 — stop building. Record.
- 3:15 — submit: repo, video, write-up, post.

## Cut

Presenter-facing camera. Meet/Zoom bots. Google Meet Media API. Continuous video to any model. Face detection or identification. Deploy, auth, database. CopilotKit. Yoodli as anything but an optional recap enrichment.

## The one rule

The `/events` shape is agreed once and never changes. Need a field? Add it. Never rename one.
