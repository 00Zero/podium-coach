# Audience camera page and scoring (Reed)

Lives in `server/` (route + static page). Reed's iPhone at the back of the room, rear camera facing the audience, leaning on a water bottle. One frame every 30 seconds. Frames are scored and discarded; nothing is stored, nobody is identified.

## `/audience` page — iOS Safari rules

Each of these costs 20 minutes if learned by trial:

1. **HTTPS only.** `getUserMedia` on an iPhone needs a secure context → the Cloudflare tunnel URL, never a LAN IP.
2. **Camera starts from a tap.** One big "Start monitoring" button. No autoplay.
3. `<video autoplay muted playsinline>` — without `playsinline`, iOS goes full-screen and the canvas grab is blank.
4. `facingMode: { ideal: "environment" }` — rear camera, wider and sharper.
5. Safari suspends the page on lock or when backgrounded. Auto-Lock → Never, `await navigator.wakeLock.request("screen")` after the tap, and the phone stays on that tab.

Grab: draw the video to a canvas 640 px wide, `canvas.toBlob(cb, "image/jpeg", 0.7)`, base64, POST as `audience_frame` per `docs/CONTRACT.md`. ~50 KB every 30 s; cellular is fine. Show the last score and a "frames sent: N" counter on the page so a glance confirms it's alive.

Gate before writing the rubric: page opens on the phone over the tunnel, tap start, own face in the video element, one frame in the server log.

Fallback with zero code change: same page on a laptop webcam at the back of the room.

## Scoring — Claude Haiku vision, one call per frame

Use the Anthropic SDK with tool use so the output is JSON, not prose. One tool, `report_engagement`, with this schema:

```json
{"engagement": {"type": "integer", "minimum": 1, "maximum": 5},
 "heads_up_pct": {"type": "integer"},
 "phones_out_pct": {"type": "integer"},
 "hands_raised": {"type": "integer"},
 "someone_speaking": {"type": "boolean"},
 "note": {"type": "string", "maxLength": 140}}
```

Rubric in the system prompt (fixed, never changed mid-session, so scores are comparable across frames):

- 5: nearly everyone looking toward the front, some leaning in, no phones/laptops visible.
- 4: most looking up; a few on devices.
- 3: mixed; about half on devices or looking away.
- 2: most on devices or turned away; visible side conversations.
- 1: empty seats, people leaving, or nobody looking up.

Rules for the model: count only what's visible; do not describe or identify individuals; if the frame is dark or unreadable, return `engagement: null` and say so in `note`.

Append the result as an `audience_score` event. Drop the frame bytes immediately.

## What the cue loop does with it

From `config/cues.json`: `audience_drop` fires when `engagement.latest <= 2` and the score fell 2+ points within the last 90 s. Priority is below time and pace, above pauses.

## What the recap does with it

Peaks and troughs in the engagement series, joined to the transcript at those times → "where the audience was most engaged," with a quote of what was being said. This is the closing shot of the video.
