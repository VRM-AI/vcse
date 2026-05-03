"""Compiled Symbolic Runtime Format models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CSRFRecord:
    claim_id: str
    subject: str
    relation: str
    object: str
    trust_tier: int
    lifecycle_status: str
    verification_status: str
    provenance_id: str


@dataclass(frozen=True)
class CSRFIndex:
    records: tuple[CSRFRecord, ...]
    by_subject: dict[str, tuple[int, ...]]
    by_relation: dict[str, tuple[int, ...]]
    by_object: dict[str, tuple[int, ...]]
