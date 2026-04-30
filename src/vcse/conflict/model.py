"""Conflict models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Conflict:
    subject: str
    relation: str
    object_a: str
    object_b: str
    source_a: str
    source_b: str
    reason: str
