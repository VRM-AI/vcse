"""Ledger Event Taxonomy — typed, deterministic outcome records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Validation statuses
LEDGER_EVENT_VALID = "LEDGER_EVENT_VALID"
LEDGER_EVENT_INVALID = "LEDGER_EVENT_INVALID"

# Severity values
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"
SEVERITY_CRITICAL = "CRITICAL"

KNOWN_SEVERITIES: frozenset[str] = frozenset({
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SEVERITY_ERROR,
    SEVERITY_CRITICAL,
})

# Actor types
ACTOR_SYSTEM = "SYSTEM"
ACTOR_USER = "USER"
ACTOR_CLI = "CLI"
ACTOR_API = "API"
ACTOR_TEST = "TEST"
ACTOR_INTERNAL = "INTERNAL"
ACTOR_UNKNOWN = "UNKNOWN"

KNOWN_ACTOR_TYPES: frozenset[str] = frozenset({
    ACTOR_SYSTEM,
    ACTOR_USER,
    ACTOR_CLI,
    ACTOR_API,
    ACTOR_TEST,
    ACTOR_INTERNAL,
    ACTOR_UNKNOWN,
})

# Subject kinds
SUBJECT_CLAIM = "CLAIM"
SUBJECT_SOURCE = "SOURCE"
SUBJECT_SOURCE_SPAN = "SOURCE_SPAN"
SUBJECT_PROPOSAL = "PROPOSAL"
SUBJECT_ONTOLOGY_RELATION = "ONTOLOGY_RELATION"
SUBJECT_PROOF = "PROOF"
SUBJECT_PROMOTION = "PROMOTION"
SUBJECT_CERTIFICATION = "CERTIFICATION"
SUBJECT_CONFLICT = "CONFLICT"
SUBJECT_POLICY = "POLICY"
SUBJECT_RUNTIME = "RUNTIME"
SUBJECT_BUNDLE = "BUNDLE"
SUBJECT_API_REQUEST = "API_REQUEST"
SUBJECT_UNKNOWN = "UNKNOWN"

KNOWN_SUBJECT_KINDS: frozenset[str] = frozenset({
    SUBJECT_CLAIM,
    SUBJECT_SOURCE,
    SUBJECT_SOURCE_SPAN,
    SUBJECT_PROPOSAL,
    SUBJECT_ONTOLOGY_RELATION,
    SUBJECT_PROOF,
    SUBJECT_PROMOTION,
    SUBJECT_CERTIFICATION,
    SUBJECT_CONFLICT,
    SUBJECT_POLICY,
    SUBJECT_RUNTIME,
    SUBJECT_BUNDLE,
    SUBJECT_API_REQUEST,
    SUBJECT_UNKNOWN,
})

# Authority override keys forbidden in details
FORBIDDEN_DETAIL_KEYS: frozenset[str] = frozenset({
    "verification_status",
    "certification_status",
    "trust_tier",
    "authoritative_support_profile_id",
    "verified",
    "certified",
    "source_supported",
})


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    event_type: str
    event_version: str
    timestamp: str
    actor_type: str
    source_system: str
    subject_kind: str
    final_status: str
    reason_code: str
    severity: str = "INFO"
    subject_id: str | None = None
    claim_id: str | None = None
    source_id: str | None = None
    source_span_ids: tuple[str, ...] = ()
    relation_id: str | None = None
    ontology_version: str | None = None
    proposal_id: str | None = None
    request_id: str | None = None
    content_hash: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LedgerEventValidationResult:
    status: str
    valid: bool
    event_type: str | None
    issue_count: int
    issues: tuple[str, ...] = ()
