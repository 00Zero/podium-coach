# Podium Coach — context for every Claude Code session on this repo

Read this, then `docs/HANDOFFS.md` and `docs/CONTRACT.md`. They are the source of truth for scope, ownership, and the API between the two halves. Do not expand scope. When in doubt, ask the human you're working with.

## What this is

An agent on the podium. Presenter's iPhone shows a countdown and one cue (≤6 words) at most every 15 s. Inputs: presenter audio from the Google Meet tab, and an iPhone at the back of the room photographing the audience every 30 s. After the talk: a recap of what landed, what to improve, where the audience was most engaged. Full description in `README.md`.

## Today

Saturday Sept 12, 2026, AI Tinkerers *Agents, Everywhere* hackathon, Seattle. Build ends **3:30 pm** Pacific. Video recording starts **2:45** regardless. Submission: public repo, 2-minute video, write-up, social post. Judged remotely 1–5 on functionality, innovation (does the environment change what the agent can do), technical execution (reliability, failure handling), usefulness (presenter stays in control).

## Who you are working with

- **Reed O'Beirne** — branch `reed/server`, owns `server/`: API, `/audience` phone page, Haiku frame scoring, cue loop, `/state`, `/presenter` page. See `docs/AUDIENCE-PAGE.md`.
- **Adam Burgh** — branch `adam/audio`, owns `audio/`, `config/`, `recap/`, `demo/`, `docs/`, `README.md`: transcription → events, cue config, recap prompt + `/end` page, fixtures, video. Not a developer; reads code and git fluently. See `docs/PRESENTER-AUDIO.md`.

Never edit the other person's directory. Shared files (`docs/CONTRACT.md`, `config/cues.json`) change only after saying so out loud. Merge to `main` every time something works — see `docs/GIT-WORKFLOW.md`.

## Decisions already made

1. **No Yoodli dependency.** Optional recap enrichment only if an API key exists. `docs/YOODLI.md`.
2. **Audio from the Meet tab** via `getDisplayMedia` + "Share tab audio" in Chrome. Built third, after file-based and mic-based transcription work. No meeting bots, no Google Meet Media API.
3. **Audience frames:** one per 30 s from an iPhone page over the Cloudflare tunnel (HTTPS required for camera). Sampled frames to Claude Haiku vision with a fixed rubric. No local models, no face detection, frames discarded after scoring.
4. **Cue policy is code.** `config/cues.json` picks the category by priority from deterministic metrics; Claude Sonnet writes ≤6 words; fallback text if the call fails. The phone never shows an error.
5. **One server on Reed's laptop**, in-memory state, `cloudflared tunnel --url http://localhost:3000` for the phones. No Vercel, no Supabase, no deploy. Cloud Run only after the video is recorded, if ever.
6. **Stack:** Reed's choice for the server (default FastAPI; Next.js acceptable). Adam's audio side is Python. Deepgram for transcription (`filler_words=true`, word timestamps); OpenAI transcription as fallback. Anthropic SDK with tool use for all JSON from models.
7. **Transport:** senders POST JSON to `/events`; presenter page polls `/state` every 2 s (SSE if trivial). Everything degrades: a dead input never blanks the podium screen.

## Clock and cut lines

12:50 live transcript or audio moves to Reed · 1:45 first real cue on the phone · 2:15 last start for slide detection · 2:45 stop, record · 3:15 submit. Presenter-facing camera, CopilotKit, bots, deploy, auth, DB: cut.

## Working rules

- Ask before adding any dependency that needs an account, OAuth, or a phone number.
- Before writing to `/events`, curl a hello event and confirm it's logged.
- Keep `demo/replay.py` working; it is the fallback for the video.
- After each step, report: what works, what doesn't, what you'd cut next. Facts, not reassurance.
