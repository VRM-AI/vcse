"""Structured deterministic query models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredQuery:
    subject: str | None = None
    relation: str | None = None
    object: str | None = None
    pack_id: str | None = None
    trusted_only: bool = False
    policy_file: str | None = None
    include_provenance: bool = True
    include_inferred: bool = False
    limit: int | None = None


@dataclass(frozen=True)
class StructuredQueryResult:
    status: str
    query: StructuredQuery
    results: tuple[dict, ...]
    result_count: int
    packs_searched: tuple[str, ...]
    packs_skipped: tuple[str, ...]
    rows_examined: int
    filters_applied: tuple[str, ...]
