"""Trust certification result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CertificationIssue:
    code: str
    severity: str
    message: str
    claim_id: str | None = None
    relation: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class CertificationResult:
    status: str
    pack_id: str
    policy_id: str
    claim_count: int
    certified_claim_count: int
    blocked_claim_count: int
    conflict_count: int
    missing_provenance_count: int
    issues: tuple[CertificationIssue, ...]
    policy_decisions: tuple[dict[str, str | None], ...] = ()


CERTIFICATION_PASSED = "CERTIFICATION_PASSED"
CERTIFICATION_FAILED = "CERTIFICATION_FAILED"
CERTIFICATION_BLOCKED = "CERTIFICATION_BLOCKED"
