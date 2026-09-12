"""Stand-in for Reed's server so the audio side can be built before his is up.

POST /events        appends to events.jsonl and prints one line per event
GET  /events?since= the log back, minus image_b64 (what recap/render.py reads)
GET  /state         a minimal version of the contract's /state, for eyeballing
Port 3000. Same shapes as docs/CONTRACT.md; no cue loop, no scoring.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "events.jsonl"

app = FastAPI(title="podium-coach stub")

EVENTS = []
SESSION = {"started_at": None, "planned_minutes": None}


def _parse_ts(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def _summary(ev):
    p = ev.get("payload") or {}
    t = ev.get("type")
    if t == "transcript_chunk":
        m = p.get("metrics") or {}
        return "%.0f-%.0fs  wpm %s  fillers %s  since_pause %s  | %s" % (
            p.get("chunk_start", 0), p.get("chunk_end", 0),
            m.get("wpm_60s", "-"), m.get("fillers_per_min", "-"),
            m.get("seconds_since_pause", "-"), (p.get("text") or "")[:70],
        )
    if t == "audience_frame":
        return "%sx%s from %s (%d b64 chars)" % (
            p.get("width"), p.get("height"), p.get("source"), len(p.get("image_b64") or ""))
    return json.dumps({k: v for k, v in p.items() if k != "image_b64"})[:160]


@app.post("/events")
async def post_event(request: Request):
    ev = await request.json()
    ts = _parse_ts(ev.get("ts"))

    if ev.get("type") == "session_start":
        SESSION["started_at"] = ev.get("ts")
        SESSION["planned_minutes"] = (ev.get("payload") or {}).get("planned_minutes")

    start = _parse_ts(SESSION["started_at"])
    ev["t"] = round((ts - start).total_seconds(), 1) if (ts and start) else None

    EVENTS.append(ev)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(ev) + "\n")

    print("[%6s] %-16s %s" % (ev["t"] if ev["t"] is not None else "-", ev.get("type"), _summary(ev)), flush=True)
    return {"ok": True}


@app.get("/events")
def get_events(since: str = None):
    cutoff = _parse_ts(since) if since else None
    out = []
    for ev in EVENTS:
        ts = _parse_ts(ev.get("ts"))
        if cutoff and ts and ts < cutoff:
            continue
        clean = dict(ev)
        clean["payload"] = {k: v for k, v in (ev.get("payload") or {}).items() if k != "image_b64"}
        out.append(clean)
    return out


@app.get("/state")
def get_state():
    latest_metrics = None
    for ev in reversed(EVENTS):
        if ev.get("type") == "transcript_chunk":
            latest_metrics = (ev.get("payload") or {}).get("metrics")
            break
    start = _parse_ts(SESSION["started_at"])
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() if start else None
    planned = SESSION["planned_minutes"]
    return {
        "session": {
            "started_at": SESSION["started_at"],
            "planned_minutes": planned,
            "elapsed_s": round(elapsed) if elapsed is not None else None,
            "remaining_s": round(planned * 60 - elapsed) if (planned and elapsed is not None) else None,
            "current_section": None,
            "section_over_by_s": 0,
        },
        "cue": None,
        "engagement": {"latest": None, "series": []},
        "metrics": latest_metrics,
    }


@app.get("/health")
def health():
    return {"ok": True, "events": len(EVENTS)}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print("stub server on http://localhost:%d  -> %s" % (port, LOG_PATH), flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
