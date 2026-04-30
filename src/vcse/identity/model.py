"""Canonical entity model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalEntity:
    canonical_id: str
    original_text: str
    normalized: str
    source_id: str
