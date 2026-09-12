"""Audience frame scoring — Claude Haiku vision, one call per frame.

The rubric is fixed for the whole session so scores are comparable across frames.
The frame is scored and then dropped: nothing is written to disk, nobody is
identified. See docs/AUDIENCE-PAGE.md.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import anthropic

SCORING_MODEL = "claude-haiku-4-5"

RUBRIC = """You are scoring a photograph of an audience during a conference talk, \
taken from the back of the room. Score the room as a whole.

Engagement scale:
5 - nearly everyone looking toward the front, some leaning in, no phones or laptops visible.
4 - most looking up; a few on devices.
3 - mixed; about half on devices or looking away.
2 - most on devices or turned away; visible side conversations.
1 - empty seats, people leaving, or nobody looking up.

Rules:
- Count only what is visible. Do not guess at what is outside the frame.
- Do not describe, identify, or characterise any individual person.
- If the frame is dark, blurred, or unreadable, return engagement null and say so in the note.
- The note is for the presenter after the talk. One short sentence about the room."""

TOOL = {
    "name": "report_engagement",
    "description": "Report what the audience photograph shows.",
    "input_schema": {
        "type": "object",
        "properties": {
            "engagement": {
                "type": ["integer", "null"],
                "minimum": 1,
                "maximum": 5,
                "description": "1-5 per the rubric, or null if the frame is unreadable.",
            },
            "heads_up_pct": {"type": "integer", "description": "Percent looking toward the front."},
            "phones_out_pct": {"type": "integer", "description": "Percent on a phone or laptop."},
            "hands_raised": {"type": "integer", "description": "Count of raised hands."},
            "someone_speaking": {"type": "boolean", "description": "Is an audience member speaking."},
            "note": {"type": "string", "description": "One sentence, at most 140 characters."},
        },
        "required": [
            "engagement",
            "heads_up_pct",
            "phones_out_pct",
            "hands_raised",
            "someone_speaking",
            "note",
        ],
        "additionalProperties": False,
    },
}

_client: anthropic.AsyncAnthropic | None = None


def client() -> anthropic.AsyncAnthropic | None:
    """The Anthropic client, or None when no key is configured."""
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        _client = anthropic.AsyncAnthropic()
    return _client


async def score_frame(image_b64: str) -> dict[str, Any] | None:
    """Score one JPEG frame. Returns the audience_score payload, or None on failure.

    None means no event is appended at all, which the contract's degradation rules
    already cover: engagement stays null and the audience cue category never fires.
    """
    api = client()
    if api is None:
        print("[score] no ANTHROPIC_API_KEY, frame dropped unscored")
        return None

    try:
        response = await asyncio.wait_for(
            api.messages.create(
                model=SCORING_MODEL,
                max_tokens=512,
                system=RUBRIC,
                tools=[TOOL],
                tool_choice={"type": "tool", "name": "report_engagement"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": "Score this frame."},
                        ],
                    }
                ],
            ),
            timeout=20.0,
        )
    except Exception as exc:
        print(f"[score] call failed ({exc.__class__.__name__}: {exc})")
        return None

    for block in response.content:
        if block.type == "tool_use":
            payload = dict(block.input)
            note = str(payload.get("note", ""))[:140]
            payload["note"] = note
            return payload
    print("[score] no tool_use block in response")
    return None
