# Kickoff prompt — Reed's Claude Code session

Paste into Claude Code from the repo root on branch `reed/server`.

```
Read CLAUDE.md, docs/HANDOFFS.md, docs/CONTRACT.md, and docs/AUDIENCE-PAGE.md. I'm Reed. I own server/ only. Branch reed/server.

Step 1 (15 min): server/ with POST /events (accept {type, ts, payload}, append to an in-memory list, log one line per event), GET /state (return the shape in CONTRACT.md with nulls for anything not computed yet), GET /events?since=. Pick FastAPI unless you have a reason not to. Start command in README's "Running it" section. Then tell me to run `cloudflared tunnel --url http://localhost:3000`.

Step 2: static /audience page per docs/AUDIENCE-PAGE.md — tap to start, rear camera, playsinline, wake lock, 640px JPEG every 30 s posted as audience_frame, on-screen counter of frames sent. I'll test it on my iPhone over the tunnel before you go further. Stop and wait for my result.

Step 3: on each audience_frame, call Claude Haiku with tool use and the fixed rubric in AUDIENCE-PAGE.md; append an audience_score event; drop the frame bytes.

Step 4: cue loop every 15 s reading config/cues.json — category by priority from the latest metrics/engagement, Sonnet phrases ≤6 words, fallback_text on any failure — exposed on /state. Static /presenter page: dark background, cue ~64px, countdown ~40px, engagement as a thin line, wake lock, nothing else.

Rules: no new dependencies needing accounts without asking. Never edit audio/, config/, recap/, demo/, docs/, README.md. Commit after each step. After each step tell me what works, what doesn't, and what you'd cut next.
```
