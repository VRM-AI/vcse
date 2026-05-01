"""Trust policy model and loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrustPolicy:
    policy_id: str = "default_certification"
    min_trust_tier: int = 1
    require_provenance: bool = True
    allow_conflicts: bool = False
    allow_missing_sources: bool = False
    allowed_pack_statuses: tuple[str, ...] = ("candidate", "reviewed")
    allowed_relations: tuple[str, ...] | None = None
    blocked_relations: tuple[str, ...] | None = None
    source_trust_threshold: float = 0.7
    min_independent_sources: int = 2
    require_verifier_consistency: bool = True
    require_gauntlet_pass: bool = True
    allow_single_authoritative_source: bool = False
    high_risk_domain: bool = False


@dataclass(frozen=True)
class StalenessPolicy:
    domain: str = "general"
    freshness_days: int = 365
    relation_overrides: dict[str, int] | None = None

    def freshness_for(self, relation: str) -> int:
        if self.relation_overrides and relation in self.relation_overrides:
            return int(self.relation_overrides[relation])
        return int(self.freshness_days)


def load_policy(path: str | Path | None) -> TrustPolicy:
    if path is None:
        return TrustPolicy()
    payload = json.loads(Path(path).read_text())
    allowed_pack_statuses = payload.get("allowed_pack_statuses", ("candidate", "reviewed"))
    allowed_relations = payload.get("allowed_relations")
    blocked_relations = payload.get("blocked_relations")
    return TrustPolicy(
        policy_id=str(payload.get("policy_id", "default_certification")),
        min_trust_tier=int(payload.get("min_trust_tier", 1)),
        require_provenance=bool(payload.get("require_provenance", True)),
        allow_conflicts=bool(payload.get("allow_conflicts", False)),
        allow_missing_sources=bool(payload.get("allow_missing_sources", False)),
        allowed_pack_statuses=tuple(str(item) for item in allowed_pack_statuses),
        allowed_relations=None
        if allowed_relations is None
        else tuple(sorted(str(item).strip() for item in allowed_relations if str(item).strip())),
        blocked_relations=None
        if blocked_relations is None
        else tuple(sorted(str(item).strip() for item in blocked_relations if str(item).strip())),
        source_trust_threshold=float(payload.get("source_trust_threshold", 0.7)),
        min_independent_sources=int(payload.get("min_independent_sources", 2)),
        require_verifier_consistency=bool(payload.get("require_verifier_consistency", True)),
        require_gauntlet_pass=bool(payload.get("require_gauntlet_pass", True)),
        allow_single_authoritative_source=bool(payload.get("allow_single_authoritative_source", False)),
        high_risk_domain=bool(payload.get("high_risk_domain", False)),
    )
