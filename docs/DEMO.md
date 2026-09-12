# Demo fixtures and the 2-minute video (Adam)

## Fixtures in `demo/`

- `sample-talk.m4a` — 90 seconds, recorded on Adam's phone from `sample-talk-script.md`. Deliberately includes ~8 fillers, one 40-second run without a pause, and a section that runs long.
- `sample-outline.txt` — one section per line with minutes: `Why this matters (0.5)`, `Demo (0.75)`, `Ask (0.25)`.
- `audience/frame-01.jpg … frame-06.jpg` — six phone photos of the team pretending to be an audience: two attentive, two mixed, two on phones. 640 px wide.
- `replay.py` — posts the outline as `session_start`, streams the audio through `audio/transcribe.py`, posts the six frames 15 s apart, posts `session_end`. `make demo` runs it. This is the insurance policy: the whole pipeline and the recap, with no live capture.

Record the sample talk as soon as the script exists. Upload a copy to Yoodli immediately to learn its processing time (see `docs/YOODLI.md`).

## Video script — 2:00, recorded by 3:10

| Time | Shot | Audio |
|---|---|---|
| 0:00 | Phone leaning on a bottle at the back of the room, facing chairs. | "Nobody on stage can see the clock, the room, or their own filler words." |
| 0:10 | Presenter's iPhone on the podium: outline pasted, countdown running. | "Podium Coach lives on the podium." |
| 0:25 | Cue appears: "Slow down. 168 wpm." | "Deterministic metrics decide when to speak. The model only picks the words." |
| 0:45 | Split: audience phone view + engagement line dipping. Cue: "Ask them a question." | "A camera at the back scores attention every thirty seconds. Frames are scored and discarded." |
| 1:10 | Talk ends; `/end` recap: what landed, what to improve, three most engaged moments with quotes. | "Afterward: what landed, what to fix, and where the room leaned in — with what you were saying at that moment." |
| 1:40 | Architecture diagram, 8 seconds. | "Google Meet tab capture, Deepgram, Claude Haiku on frames, Claude Sonnet for cues and recap. No bots, no Google APIs." |
| 1:50 | Team, sponsors, privacy line. | "Built in four hours at AI Tinkerers Seattle." |

Record in a hallway, not the main room. Keep `make demo` running as the source of truth if live capture is flaky; the phone screens are real either way.

## Write-up bullets

- The value comes from being in the room: the clock, the slides, the audience's attention, the presenter's own voice, at once.
- The presenter stays in control: one glanceable cue, never a stream; thresholds are visible in `config/cues.json`.
- Code decides *when*; the model decides *how*. That's the failure-handling story.
- Prior art: Yoodli coaches the speaker after the fact. Podium Coach coaches during, and sees the audience.
