"""Rolling speech metrics over a window of words (docs/PRESENTER-AUDIO.md).

Thresholds and the filler vocabulary live in config/cues.json, never in code.
Everything here is deterministic: no model decides what the numbers are.
"""

import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "cues.json"

_STRIP_PLAIN = re.compile(r"[^\w']+")
_STRIP_PUNCT = re.compile(r"[^\w'?]+")


def load_config(path=CONFIG_PATH):
    with open(path) as f:
        return json.load(f)


def _norm_plain(word):
    return _STRIP_PLAIN.sub("", str(word).lower())


def _norm_punct(word):
    return _STRIP_PUNCT.sub("", str(word).lower())


def _phrase_tokens(phrase):
    """A config entry -> (tokens, keep_question_mark).

    "right?" only matches a word Deepgram punctuated as "right?", so the tag
    question counts and the ordinary word does not.
    """
    keep_q = "?" in phrase
    norm = _norm_punct if keep_q else _norm_plain
    return tuple(t for t in (norm(t) for t in phrase.split()) if t), keep_q


def flag_fillers(words, filler_words):
    """Mark filler words in place.

    Each word dict gets `filler` (bool). The first word of a multi-word filler
    ("you know") also gets `filler_head`, so counting occurrences never
    double-counts a two-word phrase. Extra fields are fine: the contract says
    unknown fields are ignored.
    """
    phrases = sorted(
        (p for p in (_phrase_tokens(f) for f in filler_words) if p[0]),
        key=lambda p: -len(p[0]),
    )
    plain = [_norm_plain(w.get("punctuated") or w["w"]) for w in words]
    punct = [_norm_punct(w.get("punctuated") or w["w"]) for w in words]

    for w in words:
        w["filler"] = False
        w.pop("filler_head", None)

    i = 0
    while i < len(words):
        hit = 0
        for tokens, keep_q in phrases:
            n = len(tokens)
            if i + n > len(words):
                continue
            seq = tuple((punct if keep_q else plain)[i:i + n])
            if seq == tokens:
                hit = n
                break
        if hit:
            for j in range(i, i + hit):
                words[j]["filler"] = True
            words[i]["filler_head"] = True
            i += hit
        else:
            i += 1
    return words


class RollingMetrics:
    """Keeps every word seen so far; reports over the trailing window."""

    MIN_WINDOW_S = 10.0  # don't extrapolate wpm from a two-second sample

    def __init__(self, config=None):
        cfg = config or load_config()
        self.window_s = float(cfg.get("window_s", 60))
        self.pause_gap_s = float(cfg["thresholds"]["pause_gap_s"])
        self.words = []
        self.first_start = None
        self.last_pause_end = None  # start of the word that ended the last pause

    def add_words(self, new_words):
        for w in new_words:
            if w.get("start") is None:
                continue
            if self.words:
                gap = w["start"] - self.words[-1]["end"]
                if gap >= self.pause_gap_s:
                    self.last_pause_end = w["start"]
            if self.first_start is None:
                self.first_start = w["start"]
            self.words.append(w)

    def snapshot(self, now_s):
        if not self.words:
            return {"wpm_60s": 0, "fillers_per_min": 0.0, "seconds_since_pause": 0.0}

        span = max(self.MIN_WINDOW_S, min(self.window_s, now_s - self.first_start))
        cutoff = now_s - self.window_s
        in_window = [w for w in self.words if w["end"] >= cutoff and w["start"] <= now_s]
        minutes = span / 60.0

        wpm = round(len(in_window) / minutes)
        fillers = round(sum(1 for w in in_window if w.get("filler_head")) / minutes, 1)

        last_end = self.words[-1]["end"]
        if now_s - last_end >= self.pause_gap_s:
            since_pause = 0.0  # currently silent: that is the pause
        else:
            ref = self.last_pause_end if self.last_pause_end is not None else self.first_start
            since_pause = round(max(0.0, now_s - ref), 1)

        return {
            "wpm_60s": wpm,
            "fillers_per_min": fillers,
            "seconds_since_pause": since_pause,
        }
