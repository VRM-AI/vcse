from __future__ import annotations

from dataclasses import dataclass

TRUST_ACTIONS = frozenset({"self_certify", "certify", "candidate", "review_required", "block", "downgrade"})


@dataclass(frozen=True)
class TrustMatch:
    source_uri_prefix: str | None = None
    source_type: str | None = None
    domain: str | None = None
    relation: str | None = None
    subject: str | None = None
    field: str | None = None
    lifecycle_status: str | None = None
    verification_status: str | None = None
    provenance_status: str | None = None
    certification_status: str | None = None
    policy_status: str | None = None


@dataclass(frozen=True)
class TrustRule:
    rule_id: str
    action: str
    match: TrustMatch
    trust_tier: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class SelfCertificationPolicy:
    allowed: bool
    max_trust_tier: int
    requires_signature: bool
    requires_stable_source_hash: bool
    requires_provenance: bool
    requires_no_conflicts: bool
    requires_policy_allowed: bool
    requires_verification_status: str | None = None


@dataclass(frozen=True)
class TrustProfile:
    trust_profile_id: str
    description: str
    default_action: str
    self_certification: SelfCertificationPolicy
    rules: tuple[TrustRule, ...]
