"""Deterministic entity normalization."""

from __future__ import annotations

import re

_NON_WORD_EXCEPT_UNDERSCORE = re.compile(r"[^\w\s_]+")
_WHITESPACE = re.compile(r"\s+")
_REPEATED_UNDERSCORES = re.compile(r"_+")


def normalize_entity(text: str) -> str:
    """Normalize entity text into deterministic key form."""
    normalized = str(text).strip().lower()
    normalized = _NON_WORD_EXCEPT_UNDERSCORE.sub("", normalized)
    normalized = _WHITESPACE.sub("_", normalized)
    normalized = _REPEATED_UNDERSCORES.sub("_", normalized)
    return normalized.strip("_")
