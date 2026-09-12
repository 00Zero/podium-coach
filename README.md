# Podium Coach

An agent that lives on the podium. A phone next to the presenter shows a countdown and, at most every 15 seconds, one cue of six words or fewer: *"Skip architecture. Two minutes left."* It listens to the presenter through the Google Meet they're presenting in, and watches the audience through a phone at the back of the room. When the talk ends, the presenter gets a recap: what landed, what to improve, and where the audience was most engaged — with what was being said at that moment.

Built in four hours at the AI Tinkerers *Agents, Everywhere* global hackathon, Seattle, September 12, 2026, by Reed O'Beirne and Adam Burgh.

## Why the environment matters

<!-- Adam: two paragraphs. Nobody on stage can see the clock, the room, or their own filler words. A chatbox can't either, because it wasn't in the room. The value comes from four things at once: the countdown, the outline, the presenter's own voice, and the audience's attention. -->

## Architecture

```mermaid
flowchart LR
  subgraph Presenter laptop
    MEET[Google Meet tab] -->|getDisplayMedia tab audio| CAP[audio/capture.html]
    CAP -->|10 s chunks| TR[audio/transcribe.py]
    TR -->|Deepgram, word timestamps, fillers| TR
  end
  subgraph Reed's laptop
    SRV[server: POST /events, GET /state]
    CUE[cue loop, every 15 s]
    SCORE[Claude Haiku vision scoring]
    SRV --> CUE
    SRV --> SCORE --> SRV
  end
  TR -->|transcript_chunk| SRV
  AUD[iPhone at back of room: /audience] -->|1 frame / 30 s| SRV
  CUE -->|config/cues.json picks category, Claude Sonnet writes ≤6 words| SRV
  SRV -->|/state, polled every 2 s| POD[iPhone on podium: /presenter]
  SRV -->|GET /events| END[/end recap: Claude Sonnet, recap/prompt.md]
```

Code decides *when* to speak (deterministic metrics: WPM, fillers per minute, seconds since a pause, section time vs. outline, engagement delta). The model only decides *how*. If the model call fails, a fixed fallback line for that category is shown. Nothing on the presenter's screen ever errors.

## Running it

<!-- Reed: fill in once the server exists. -->

```
cp .env.example .env            # fill in keys
# Reed's laptop
cd server && <start command>    # port 3000
cloudflared tunnel --url http://localhost:3000
# Adam's laptop
make install                    # .venv + audio/recap deps
export PODIUM_SERVER_URL=https://xxxx.trycloudflare.com
make hello                      # confirm the server logs an event before sending anything real
make mic                        # laptop microphone, live
make tab                        # Meet tab audio: then open http://localhost:3100 in Chrome
python audio/transcribe.py demo/sample-talk.m4a   # a recorded file, 10-second chunks
# Phones
open https://xxxx.trycloudflare.com/presenter   # podium
open https://xxxx.trycloudflare.com/audience    # back of room
# Full pipeline with no live capture
make stub                       # stand-in for the server, port 3000, if Reed's isn't up
make demo                       # replays the sample talk in real time
make recap                      # builds recap/out/recap.html from the event log
```

## Cue priority

| Priority | Category | Fires when | Example |
|---|---|---|---|
| 1 | time_over | elapsed > planned | Over time. Land it. |
| 2 | time_warning | ≤ 60 s left | One minute. Go to ask. |
| 3 | section_drift | current section > 60 s over plan | Skip architecture. Two min left. |
| 4 | pace_fast | WPM (60 s) > 165 | Slow down. 172 wpm. |
| 5 | fillers | > 4 fillers/min | Pause, don't um. |
| 6 | audience_drop | engagement ≤ 2 and fell 2+ points in 90 s | Ask the room something. |
| 7 | no_pause | > 45 s without a 1.5 s pause | Pause. Let it land. |
| 8 | pace_slow | WPM < 105 | Pick it up. |

Thresholds are in `config/cues.json`, not in code.

## Privacy

Audience frames are sampled once every 30 seconds, sent to a vision model with a fixed rubric that counts posture and attention, and discarded immediately. No frames are stored. No faces are detected or identified. The presenter's audio is transcribed and kept for the recap only.

## Repository

- `docs/HANDOFFS.md` — who does what, the clock, the cut list
- `docs/CONTRACT.md` — the `/events` and `/state` API both halves agree on
- `docs/PRESENTER-AUDIO.md` — Adam's audio pipeline
- `docs/AUDIENCE-PAGE.md` — Reed's camera page and scoring rubric
- `docs/DEMO.md` — fixtures and the video script
- `docs/GIT-WORKFLOW.md` — branches and merge rule
- `docs/YOODLI.md` — why Yoodli is optional, and how to add it if a key exists
- `config/cues.json` — cue thresholds, priority, fallback text
- `recap/prompt.md` — the recap prompt and output schema

## Sponsors used

<!-- Fill at the end, honestly: Claude (Haiku vision, Sonnet cues + recap), Deepgram, OpenRouter/OpenAI if used, Cloud Run if deployed. -->
