"""Post-talk recap: event log -> Claude Sonnet -> recap/out/recap.html.

    python recap/render.py                 # reads GET /events from PODIUM_SERVER_URL
    python recap/render.py --events events.jsonl
    python recap/render.py --no-model      # numbers only, no API call

The prompt lives in recap/prompt.md; this file fills it in and enforces the
output schema with a strict tool. Everything the model is told is computed
here, deterministically, from the event log.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SERVER = os.environ.get("PODIUM_SERVER_URL", "http://localhost:3000")
PROMPT_PATH = ROOT / "recap" / "prompt.md"
OUT_PATH = ROOT / "recap" / "out" / "recap.html"
MODEL = "claude-sonnet-5"
PAUSE_GAP_S = 1.5

RECAP_SCHEMA = {
    "type": "object",
    "properties": {
        "what_landed": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"section": {"type": "string"}, "at": {"type": "string"},
                               "quote": {"type": "string"}, "why": {"type": "string"}},
                "required": ["section", "at", "quote", "why"], "additionalProperties": False,
            },
        },
        "what_to_improve": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"issue": {"type": "string"}, "evidence": {"type": "string"},
                               "suggestion": {"type": "string"}},
                "required": ["issue", "evidence", "suggestion"], "additionalProperties": False,
            },
        },
        "most_engaged": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"at": {"type": "string"}, "score": {"type": "integer"},
                               "quote": {"type": "string"}, "section": {"type": "string"}},
                "required": ["at", "score", "quote", "section"], "additionalProperties": False,
            },
        },
        "least_engaged": {
            "type": "object",
            "properties": {"at": {"type": "string"}, "score": {"type": "integer"},
                           "quote": {"type": "string"}, "section": {"type": "string"}},
            "required": ["at", "score", "quote", "section"], "additionalProperties": False,
        },
        "one_line": {"type": "string"},
    },
    "required": ["what_landed", "what_to_improve", "one_line"],
    "additionalProperties": False,
}


# --------------------------------------------------------------- the events

def load_events(path=None):
    if path:
        rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
        print("read %d events from %s" % (len(rows), path), flush=True)
        return rows
    try:
        r = requests.get(SERVER + "/events", timeout=10)
        r.raise_for_status()
        rows = r.json()
        print("read %d events from %s" % (len(rows), SERVER), flush=True)
        return rows
    except Exception as e:
        print("GET /events failed (%s); falling back to audio/events.local.jsonl" % e, flush=True)
        local = ROOT / "audio" / "events.local.jsonl"
        if not local.exists():
            sys.exit("no events anywhere: start the server or run make demo")
        return [json.loads(l) for l in local.read_text().splitlines() if l.strip()]


def mmss(seconds):
    seconds = max(0, int(round(seconds or 0)))
    return "%d:%02d" % (seconds // 60, seconds % 60)


def summarize(events):
    """Every number the prompt needs, computed from the log alone.

    Only the most recent session counts: a log can hold several runs, either
    because the local file accumulates them or because the server was
    restarted mid-afternoon.
    """
    last_start = max((i for i, e in enumerate(events)
                      if e.get("type") == "session_start"), default=None)
    if last_start is not None and last_start:
        print("log holds %d earlier events; using the last session only" % last_start, flush=True)
        events = events[last_start:]
    chunks = [e for e in events if e.get("type") == "transcript_chunk" and (e.get("payload") or {}).get("words") is not None]
    scores = [e for e in events if e.get("type") == "audience_score"]
    cues = [e for e in events if e.get("type") == "cue"]
    start = next((e for e in events if e.get("type") == "session_start"), None)

    words = []
    for c in chunks:
        words.extend(c["payload"].get("words") or [])
    words.sort(key=lambda w: w.get("start", 0))

    duration = max([c["payload"].get("chunk_end", 0) for c in chunks] + [0])
    minutes = max(duration / 60.0, 1e-9)
    outline = (start or {}).get("payload", {}).get("outline") or []
    planned_minutes = (start or {}).get("payload", {}).get("planned_minutes") or sum(
        s.get("minutes", 0) for s in outline)

    # fillers: count phrase heads, so "you know" is one filler and not two
    def is_head(i, w):
        if not w.get("filler"):
            return False
        return w.get("filler_head", not (i and words[i - 1].get("filler")))

    filler_total = sum(1 for i, w in enumerate(words) if is_head(i, w))

    buckets = {}
    for i, w in enumerate(words):
        if is_head(i, w):
            buckets[int(w["start"] // 60)] = buckets.get(int(w["start"] // 60), 0) + 1
    worst = max(buckets.items(), key=lambda kv: kv[1]) if buckets else None

    # longest stretch with no gap >= 1.5 s
    run_start, best = (words[0]["start"] if words else 0.0), (0.0, 0.0)
    for prev, cur in zip(words, words[1:]):
        if cur["start"] - prev["end"] >= PAUSE_GAP_S:
            if prev["end"] - run_start > best[0]:
                best = (prev["end"] - run_start, run_start)
            run_start = cur["start"]
    if words and words[-1]["end"] - run_start > best[0]:
        best = (words[-1]["end"] - run_start, run_start)

    peak = max((((c["payload"].get("metrics") or {}).get("wpm_60s") or 0),
                c["payload"].get("chunk_end", 0)) for c in chunks) if chunks else (0, 0)

    def at_t(ev):
        return ev.get("t") if ev.get("t") is not None else 0

    return {
        "outline": outline,
        "planned_minutes": planned_minutes,
        "duration_s": duration,
        "words": words,
        "chunks": chunks,
        "avg_wpm": round(len(words) / minutes),
        "max_wpm": peak[0],
        "max_wpm_at": mmss(peak[1]),
        "filler_total": filler_total,
        "fillers_per_min": round(filler_total / minutes, 1),
        "worst_filler_minute": ("%s–%s (%d fillers)" % (mmss(worst[0] * 60), mmss(worst[0] * 60 + 60), worst[1]))
                               if worst else "none",
        "longest_no_pause_s": round(best[0], 1),
        "longest_no_pause_at": mmss(best[1]),
        "cues": [{"at": mmss(at_t(c)), "category": (c.get("payload") or {}).get("category"),
                  "text": (c.get("payload") or {}).get("text")} for c in cues],
        # A frame the model could not read (too dark, pointed at a desk) scores
        # null. Those are not zero engagement, they are no measurement: drop them
        # rather than draw them as a dip the presenter never caused.
        "engagement": [{"t": at_t(s), "score": (s.get("payload") or {}).get("engagement"),
                        "note": (s.get("payload") or {}).get("note", "")} for s in scores
                       if (s.get("payload") or {}).get("engagement") is not None],
        "unreadable_frames": sum(1 for s in scores
                                 if (s.get("payload") or {}).get("engagement") is None),
    }


def fill_prompt(s):
    md = PROMPT_PATH.read_text()
    system = md.split("## System", 1)[1].split("##", 1)[0].strip()
    template = re.search(r"## User message template\s*```(.*?)```", md, re.S).group(1).strip()

    outline_lines = "\n".join(
        "- %s: planned %s, actual n/a (no slide detection)" % (sec.get("title"), mmss(sec.get("minutes", 0) * 60))
        for sec in s["outline"]) or "- (no outline was posted)"
    engagement = "\n".join("- %ss -> %s  %s" % (e["t"], e["score"], e["note"]) for e in s["engagement"]) \
        or "(no audience scores in the log)"
    cue_list = "; ".join("%s %s: %s" % (c["at"], c["category"], c["text"]) for c in s["cues"]) or "none"
    transcript = "\n".join("%s  %s" % (mmss(c["payload"].get("chunk_start", 0)), c["payload"].get("text", ""))
                           for c in s["chunks"] if (c["payload"].get("text") or "").strip()) or "(no transcript)"

    user = (template
            .replace("{{outline_with_actuals}}", outline_lines)
            .replace("{{duration_mmss}}", mmss(s["duration_s"]))
            .replace("{{planned_mmss}}", mmss(s["planned_minutes"] * 60))
            .replace("{{avg_wpm}}", str(s["avg_wpm"]))
            .replace("{{max_wpm}}", str(s["max_wpm"]))
            .replace("{{max_wpm_at}}", s["max_wpm_at"])
            .replace("{{filler_total}}", str(s["filler_total"]))
            .replace("{{fillers_per_min}}", str(s["fillers_per_min"]))
            .replace("{{worst_filler_minute}}", s["worst_filler_minute"])
            .replace("{{longest_no_pause_s}}", str(s["longest_no_pause_s"]))
            .replace("{{longest_no_pause_at}}", s["longest_no_pause_at"])
            .replace("{{cue_list}}", cue_list)
            .replace("{{engagement_series}}", engagement)
            .replace("{{transcript_lines}}", transcript))
    return system, user


_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def tidy(value):
    """Models sometimes emit literal \\u2265 or \\" inside tool-call strings."""
    if isinstance(value, str):
        v = _ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), value)
        return v.replace('\\"', '"').replace("\\'", "'")
    if isinstance(value, list):
        return [tidy(v) for v in value][:3]      # prompt says three items max
    if isinstance(value, dict):
        return {k: tidy(v) for k, v in value.items()}
    return value


def call_model(system, user):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[{"name": "write_recap", "description": "Return the post-talk recap.",
                "strict": True, "input_schema": RECAP_SCHEMA}],
        tool_choice={"type": "tool", "name": "write_recap"},
    )
    for block in resp.content:
        if block.type == "tool_use":
            return tidy(block.input)
    raise RuntimeError("model returned no recap: stop_reason=%s" % resp.stop_reason)


# ----------------------------------------------------------------- the page

def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(s, recap):
    def items(rows, fmt):
        return "\n".join("<li>%s</li>" % fmt(r) for r in rows) or "<li class='none'>Not available.</li>"

    spark = ""
    if s["engagement"]:
        pts = s["engagement"]
        w, h = 640, 90
        span = max(1.0, max(p["t"] for p in pts) or 1.0)
        coords = " ".join("%.1f,%.1f" % (p["t"] / span * w, h - ((p["score"] or 0) / 5.0) * h) for p in pts)
        spark = ("<svg viewBox='0 0 %d %d' class='spark'><polyline points='%s' fill='none' "
                 "stroke='#3ddc84' stroke-width='3'/></svg>" % (w, h, coords))

    metric_cards = [
        ("Length", "%s <small>planned %s</small>" % (mmss(s["duration_s"]), mmss(s["planned_minutes"] * 60))),
        ("Average pace", "%s wpm <small>peak %s at %s</small>" % (s["avg_wpm"], s["max_wpm"], s["max_wpm_at"])),
        ("Fillers", "%s <small>%s/min · worst %s</small>" % (s["filler_total"], s["fillers_per_min"], s["worst_filler_minute"])),
        ("Longest run without a pause", "%ss <small>from %s</small>" % (s["longest_no_pause_s"], s["longest_no_pause_at"])),
    ]

    least = recap.get("least_engaged")
    return """<!doctype html>
<meta charset="utf-8"><title>Podium Coach — recap</title>
<style>
 body{background:#0e0e10;color:#eee;font:16px/1.6 -apple-system,system-ui,sans-serif;margin:0;padding:40px 24px;}
 main{max-width:760px;margin:0 auto;}
 h1{font-size:28px;margin:0 0 4px;} .one-line{color:#3ddc84;font-size:19px;margin:0 0 28px;}
 h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:#888;margin:32px 0 10px;}
 .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;}
 .card{background:#17171a;border-radius:10px;padding:12px 14px;}
 .card b{display:block;color:#888;font-weight:500;font-size:13px;} .card span{font-size:20px;}
 small{display:block;color:#777;font-size:12px;font-weight:400;}
 ul{list-style:none;padding:0;margin:0;} li{background:#17171a;border-radius:10px;padding:12px 14px;margin-bottom:8px;}
 li.none{color:#777;background:none;padding-left:0;}
 .at{color:#3ddc84;font-variant-numeric:tabular-nums;margin-right:8px;}
 q{color:#ddd;font-style:italic;} .why{color:#999;font-size:14px;display:block;margin-top:4px;}
 .spark{width:100%%;height:90px;background:#17171a;border-radius:10px;padding:8px;box-sizing:border-box;}
 footer{color:#666;font-size:13px;margin-top:40px;}
</style>
<main>
<h1>Podium Coach — recap</h1>
<p class="one-line">%(one_line)s</p>

<h2>The numbers</h2>
<div class="cards">%(cards)s</div>

<h2>What landed</h2>
<ul>%(landed)s</ul>

<h2>What to improve</h2>
<ul>%(improve)s</ul>

<h2>Where the room leaned in</h2>
%(spark)s
<ul>%(engaged)s</ul>
%(least)s

<h2>Cues shown during the talk</h2>
<ul>%(cues)s</ul>

<footer>Frames were scored and discarded; nothing from the camera is stored. Thresholds in config/cues.json.</footer>
</main>
""" % {
        "one_line": esc(recap.get("one_line", "")),
        "cards": "\n".join("<div class='card'><b>%s</b><span>%s</span></div>" % (k, v) for k, v in metric_cards),
        "landed": items(recap.get("what_landed", []),
                        lambda r: "<span class='at'>%s</span><b>%s</b><br><q>%s</q><span class='why'>%s</span>"
                        % (esc(r.get("at")), esc(r.get("section")), esc(r.get("quote")), esc(r.get("why")))),
        "improve": items(recap.get("what_to_improve", []),
                         lambda r: "<b>%s</b><span class='why'>%s</span><span class='why'>→ %s</span>"
                         % (esc(r.get("issue")), esc(r.get("evidence")), esc(r.get("suggestion")))),
        "spark": spark,
        "engaged": items(recap.get("most_engaged", []),
                         lambda r: "<span class='at'>%s</span>score %s · %s<br><q>%s</q>"
                         % (esc(r.get("at")), esc(r.get("score")), esc(r.get("section")), esc(r.get("quote")))),
        "least": ("<p class='why'>Lowest: %s, score %s, %s — <q>%s</q></p>"
                  % (esc(least.get("at")), esc(least.get("score")), esc(least.get("section")), esc(least.get("quote")))) if least else "",
        "cues": items(s["cues"], lambda c: "<span class='at'>%s</span>%s <small>%s</small>"
                      % (esc(c["at"]), esc(c["text"]), esc(c["category"]))),
    }


def main():
    ap = argparse.ArgumentParser(description="build the post-talk recap page")
    ap.add_argument("--events", help="read a jsonl log instead of GET /events")
    ap.add_argument("--no-model", action="store_true", help="skip the API call; numbers only")
    ap.add_argument("--open", action="store_true", help="open the page when it's built")
    args = ap.parse_args()

    s = summarize(load_events(args.events))
    print("%s of talk, %d words, %d fillers, %d audience scores"
          % (mmss(s["duration_s"]), len(s["words"]), s["filler_total"], len(s["engagement"])), flush=True)

    recap = {"one_line": "Numbers only — the model was not called.",
             "what_landed": [], "what_to_improve": []}
    if not args.no_model:
        system, user = fill_prompt(s)
        try:
            recap = call_model(system, user)
        except Exception as e:                  # a failed recap still shows the metrics
            print("model call failed, rendering numbers only:", e, flush=True)
            recap["one_line"] = "The recap model call failed; the measured numbers are below."

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render_html(s, recap))
    print("wrote %s" % OUT_PATH, flush=True)
    if args.open:
        os.system("open '%s'" % OUT_PATH)


if __name__ == "__main__":
    main()
