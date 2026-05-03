from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustDecision:
    status: str
    action: str
    trust_profile_id: str
    matched_rule_id: str | None
    subject: str | None
    relation: str | None
    object: str | None
    claim_id: str | None
    source_uri: str | None
    trust_tier: int
    reason: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class TrustAssessment:
    status: str
    trust_profile_id: str
    record_count: int
    self_certified_count: int
    certified_count: int
    candidate_count: int
    review_required_count: int
    blocked_count: int
    downgraded_count: int
    decisions: tuple[TrustDecision, ...]
