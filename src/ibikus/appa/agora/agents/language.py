"""Cheap, offline detection of the request language (good enough to steer small models)."""

from __future__ import annotations

import re

_GERMAN_WORDS = {
    "der",
    "die",
    "das",
    "und",
    "ist",
    "nicht",
    "ich",
    "mir",
    "mich",
    "ein",
    "eine",
    "zwischen",
    "über",
    "was",
    "wie",
    "warum",
    "bitte",
    "erkläre",
    "erzähl",
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def cyrillic_share(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum("Ѐ" <= ch <= "ӿ" for ch in letters) / len(letters)


def detect_language(text: str) -> str | None:
    """Return 'Russian', 'German', 'English' or None (no letters)."""
    if cyrillic_share(text) > 0.3:
        return "Russian"
    words = {w.lower() for w in _WORD.findall(text)}
    if not words:
        return None
    if any(ch in text for ch in "äöüÄÖÜß") or words & _GERMAN_WORDS:
        return "German"
    return "English"
