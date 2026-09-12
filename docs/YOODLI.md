# Yoodli — what it is and isn't for this project

Decision: **not a dependency.** Optional recap enrichment only, P2, only if an API key exists.

## Facts (verified Sept 12, 2026)

- The Yoodli MCP that's connected is the API-docs MCP. It exposes 11 REST endpoints; 10 are org admin (user groups, invites, membership expiration).
- The one relevant endpoint: `GET https://app.yoodli.ai/api/v3/speeches/{speechId}/feedback?sections=goals&sections=coaching_feedback&sections=transcript`. Bearer token auth. Returns rubric goal scores (e.g. `pace_control` 4/5 with feedback), coaching remarks (e.g. `conciseness`), timestamped reviewer comments, and a transcript with per-line start/end seconds.
- No upload endpoint. No streaming. No real-time. Recordings must be made or uploaded in Yoodli's own app.
- Free Starter plan: 5 lifetime sessions; any session over 30 s counts. Pro: $8/mo annual, 10/week. Uploaded recordings are supported.
- Open question: whether Adam's plan can generate an API key (developers.yoodli.ai). The developer portal says "no API for end users," but the endpoint exists.

## If a key exists — 30-minute recap enrichment

1. After the talk, upload the recording (Meet recording or the phone video) to Yoodli. Note processing time from the test upload.
2. Speech ID = the slug in the recording's Yoodli URL.
3. `/end?yoodli=<speechId>` → server calls the feedback endpoint → recap shows Yoodli's speaker-side scores next to our audience engagement line: "Yoodli: pace 4/5. The room disagreed at minute 6."

That's a comparison with a contrast, which is a real integration. Without a key, mention Yoodli as prior art in the write-up and don't call it an integration.

## Never

Screen-scraping Yoodli's desktop overlay to relay its live cues. It scores as a wrapper and it isn't buildable today.
