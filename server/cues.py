"""The cue loop — decides WHEN to speak in code, asks Claude only HOW to say it.

Category selection is deterministic and driven entirely by config/cues.json, which
Adam owns. The model writes at most `max_words` words. Any failure at all falls back
to that category's `fallback_text`, so the podium phone never shows an error.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any

import anthropic

CUE_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You write cues for a speaker on stage who can see only a phone \
on the podium. The cue is read at a glance, mid-sentence, while they are talking.

Rules:
- At most {max_words} words. Fewer is better.
- Imperative. Tell them what to do, not what is wrong.
- Plain speech. No jargon, no praise, no hedging, no punctuation beyond a period.
- You may include one number ONLY if it appears verbatim in the live numbers given
  to you. Never round it, never estimate, never invent one. Omit it if unsure.
- Never mention the audience camera, the transcript, or that you are an AI.

Write only the cue text, nothing else."""

_client: anthropic.AsyncAnthropic | None = None


def client() -> anthropic.AsyncAnthropic | None:
    """The Anthropic client, or None when no key is configured."""
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        _client = anthropic.AsyncAnthropic()
    return _client


def matching_categories(state: dict[str, Any], config: dict[str, Any]) -> list[str]:
    """Every matching category, in the configured priority order.

    Conditions mirror `categories[*].condition` in config/cues.json. They are written
    out in code rather than eval'd so a typo in the config cannot crash the loop.
    """
    thresholds = config.get("thresholds", {})
    session = state.get("session", {})
    metrics = state.get("metrics") or {}
    engagement = state.get("engagement", {})

    elapsed = session.get("elapsed_s") or 0.0
    remaining = session.get("remaining_s")
    over_by = session.get("section_over_by_s") or 0.0
    wpm = metrics.get("wpm_60s")
    fillers = metrics.get("fillers_per_min")
    since_pause = metrics.get("seconds_since_pause")
    latest = engagement.get("latest")

    def audience_dropped() -> bool:
        """Low right now AND fell by the configured points inside the window."""
        low = thresholds.get("engagement_low", 2)
        drop = thresholds.get("engagement_drop_points", 2)
        window = thresholds.get("engagement_drop_window_s", 90)
        if latest is None or latest > low:
            return False
        recent = [
            p for p in engagement.get("series", [])
            if p.get("score") is not None and elapsed - (p.get("t") or 0.0) <= window
        ]
        return bool(recent) and (max(p["score"] for p in recent) - latest) >= drop

    tests = {
        "time_over": lambda: remaining is not None and remaining <= 0 and elapsed > 0,
        "time_warning": lambda: remaining is not None and 0 < remaining <= 60,
        "section_drift": lambda: over_by > thresholds.get("section_drift_s", 60),
        "pace_fast": lambda: wpm is not None and wpm > thresholds.get("wpm_fast", 165),
        "fillers": lambda: fillers is not None
        and fillers > thresholds.get("fillers_per_min", 4),
        "audience_drop": audience_dropped,
        "no_pause": lambda: since_pause is not None
        and since_pause > thresholds.get("no_pause_s", 45),
        "pace_slow": lambda: wpm is not None
        and wpm < thresholds.get("wpm_slow", 105)
        and elapsed > 60,
    }

    matched: list[str] = []
    for category in config.get("priority", []):
        test = tests.get(category)
        if test is None:
            continue
        try:
            if test():
                matched.append(category)
        except Exception as exc:  # a bad threshold must never stop the loop
            print(f"[cue] condition {category} failed: {exc}")
    return matched


def facts(state: dict[str, Any]) -> str:
    """The live numbers the model is allowed to quote, as plain lines."""
    session = state.get("session", {})
    metrics = state.get("metrics") or {}
    lines = [
        f"elapsed: {round(session.get('elapsed_s') or 0)}s",
        f"remaining: {round(session.get('remaining_s'))}s"
        if session.get("remaining_s") is not None
        else "remaining: unknown",
        f"current section: {session.get('current_section') or 'unknown'}",
        f"section over by: {round(session.get('section_over_by_s') or 0)}s",
        f"words per minute: {metrics.get('wpm_60s', 'unknown')}",
        f"fillers per minute: {metrics.get('fillers_per_min', 'unknown')}",
        f"seconds since a pause: {metrics.get('seconds_since_pause', 'unknown')}",
        f"audience engagement 1-5: {(state.get('engagement') or {}).get('latest', 'unknown')}",
    ]
    return "\n".join(lines)


def numbers_are_real(text: str, allowed: str) -> bool:
    """Every number in the cue must appear in the facts we gave the model.

    A cue that quotes a wpm the presenter never hit is worse than no cue at all, and
    the model does invent them: it wrote "Slow down. 210 wpm." for a measured 188.
    """
    given = set(re.findall(r"\d+", allowed))
    return all(n in given for n in re.findall(r"\d+", text))


async def phrase(category: str, state: dict[str, Any], config: dict[str, Any]) -> tuple[str, str]:
    """Return (cue_text, source). Source is 'model' or 'fallback'."""
    spec = (config.get("categories") or {}).get(category, {})
    fallback = spec.get("fallback_text", "Keep going.")
    max_words = config.get("max_words", 6)

    api = client()
    if api is None:
        return fallback, "fallback"

    examples = ", ".join(f'"{e}"' for e in spec.get("examples", []))
    prompt = (
        f"Category: {category}\n"
        f"Why it fired: {spec.get('condition', 'n/a')}\n"
        f"Cues of this kind read like: {examples}\n\n"
        f"Live numbers:\n{facts(state)}\n\n"
        f"Write the cue."
    )

    try:
        response = await asyncio.wait_for(
            api.messages.create(
                model=CUE_MODEL,
                max_tokens=256,
                system=SYSTEM_PROMPT.format(max_words=max_words),
                tools=[
                    {
                        "name": "show_cue",
                        "description": "Show one cue on the presenter's podium phone.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": f"The cue, at most {max_words} words.",
                                }
                            },
                            "required": ["text"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    }
                ],
                tool_choice={"type": "tool", "name": "show_cue"},
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=8.0,
        )
    except Exception as exc:
        print(f"[cue] model call failed ({exc.__class__.__name__}), using fallback")
        return fallback, "fallback"

    allowed = facts(state)
    for block in response.content:
        if block.type == "tool_use":
            text = str(block.input.get("text", "")).strip()
            if not text or len(text.split()) > max_words + 1:
                print(f"[cue] model text unusable {text!r}, using fallback")
                break
            if not numbers_are_real(text, allowed):
                print(f"[cue] model invented a number in {text!r}, using fallback")
                break
            return text, "model"
    return fallback, "fallback"


async def run_loop(get_state, get_config, emit) -> None:
    """Every loop_interval_s: pick a category, phrase it, emit a cue event.

    `emit` takes (category, text, reason) and appends the event. A category is not
    repeated inside `min_repeat_s` so the phone is not nagging with the same words
    every 15 seconds; a different, higher-priority category always gets through.
    """
    last_fired: dict[str, float] = {}

    while True:
        config = get_config()
        interval = float(config.get("loop_interval_s", 15))
        await asyncio.sleep(interval)

        try:
            state = get_state()
            if not state.get("session", {}).get("started_at"):
                continue

            now = datetime.now(timezone.utc).timestamp()
            min_repeat = float(config.get("min_repeat_s", 45))

            # Highest-priority category that is not in its repeat cooldown. Falling
            # through matters: if pace_fast is cooling down but fillers are also over
            # threshold, the presenter should hear about the fillers, not silence.
            category = next(
                (
                    c
                    for c in matching_categories(state, config)
                    if now - last_fired.get(c, 0.0) >= min_repeat
                ),
                None,
            )
            if category is None:
                continue

            text, source = await phrase(category, state, config)
            last_fired[category] = now
            emit(category, text, f"{category} matched ({source})")
        except Exception as exc:  # the loop outlives any single bad tick
            print(f"[cue] loop tick failed: {exc.__class__.__name__}: {exc}")
