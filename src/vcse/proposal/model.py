"""Candidate Proposal Contract models and machine constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# --- Proposal kind ---
CANDIDATE_PROPOSAL = "CANDIDATE_PROPOSAL"

# --- Candidate kinds ---
FACTUAL_CLAIM_PACK = "FACTUAL_CLAIM_PACK"

# --- Candidate statuses ---
PROPOSED = "PROPOSED"
STRUCTURALLY_VALID = "STRUCTURALLY_VALID"
CANDIDATE_ACCEPTED = "CANDIDATE_ACCEPTED"
CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
VCSE_EVALUATED = "VCSE_EVALUATED"

# --- Proposal validation statuses ---
PROPOSAL_VALID = "PROPOSAL_VALID"
PROPOSAL_INVALID = "PROPOSAL_INVALID"

# --- Rejection reason codes ---
MISSING_PROPOSAL_VERSION = "MISSING_PROPOSAL_VERSION"
MISSING_PROPOSAL_KIND = "MISSING_PROPOSAL_KIND"
INVALID_PROPOSAL_KIND = "INVALID_PROPOSAL_KIND"
MISSING_CANDIDATE_KIND = "MISSING_CANDIDATE_KIND"
INVALID_CANDIDATE_KIND = "INVALID_CANDIDATE_KIND"
MISSING_CLAIMS = "MISSING_CLAIMS"
INVALID_CLAIMS = "INVALID_CLAIMS"
MISSING_CLAIM_ID = "MISSING_CLAIM_ID"
MISSING_CLAIM_TYPE = "MISSING_CLAIM_TYPE"
MISSING_CLAIM_STATUS = "MISSING_CLAIM_STATUS"
INVALID_CLAIM_STATUS = "INVALID_CLAIM_STATUS"
MISSING_CLAIM_SUBJECT = "MISSING_CLAIM_SUBJECT"
MISSING_CLAIM_PREDICATE = "MISSING_CLAIM_PREDICATE"
MISSING_CLAIM_OBJECT = "MISSING_CLAIM_OBJECT"
MISSING_SOURCE_SPAN_IDS = "MISSING_SOURCE_SPAN_IDS"
INVALID_SOURCE_SPAN_IDS = "INVALID_SOURCE_SPAN_IDS"
FORBIDDEN_VERIFICATION_STATUS = "FORBIDDEN_VERIFICATION_STATUS"
FORBIDDEN_CERTIFICATION_STATUS = "FORBIDDEN_CERTIFICATION_STATUS"
FORBIDDEN_TRUST_TIER = "FORBIDDEN_TRUST_TIER"
FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE = "FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE"
UNKNOWN_TOP_LEVEL_FIELD = "UNKNOWN_TOP_LEVEL_FIELD"
UNKNOWN_CLAIM_FIELD = "UNKNOWN_CLAIM_FIELD"
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
STATUS_CASING_INVALID = "STATUS_CASING_INVALID"
NON_FINITE_VALUE = "NON_FINITE_VALUE"

# --- Payload limit ---
MAX_PROPOSAL_JSON_BYTES = 1_048_576  # 1 MiB

# --- Allowed top-level fields ---
ALLOWED_TOP_LEVEL_FIELDS = frozenset({
    "proposal_version",
    "proposal_kind",
    "candidate_kind",
    "claims",
    "verification_request",
    "metadata",
})

# --- Forbidden top-level fields (authority escalation) ---
FORBIDDEN_ROOT_FIELDS = {
    "verification_status": FORBIDDEN_VERIFICATION_STATUS,
    "certification_status": FORBIDDEN_CERTIFICATION_STATUS,
    "trust_tier": FORBIDDEN_TRUST_TIER,
    "authoritative_support_profile_id": FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE,
}

# --- Allowed claim fields ---
ALLOWED_CLAIM_FIELDS = frozenset({
    "claim_id",
    "claim_type",
    "status",
    "subject",
    "predicate",
    "object",
    "source_span_ids",
    "raw_value",
    "normalized_value",
    "metadata",
})

# --- Forbidden claim fields (authority escalation) ---
FORBIDDEN_CLAIM_FIELDS = {
    "verification_status": FORBIDDEN_VERIFICATION_STATUS,
    "certification_status": FORBIDDEN_CERTIFICATION_STATUS,
    "trust_tier": FORBIDDEN_TRUST_TIER,
    "authoritative_support_profile_id": FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE,
}

# --- Forbidden metadata keys ---
FORBIDDEN_METADATA_KEYS = {
    "verification_status": FORBIDDEN_VERIFICATION_STATUS,
    "certification_status": FORBIDDEN_CERTIFICATION_STATUS,
    "trust_tier": FORBIDDEN_TRUST_TIER,
    "authoritative_support_profile_id": FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE,
    "verified": FORBIDDEN_VERIFICATION_STATUS,
    "certified": FORBIDDEN_CERTIFICATION_STATUS,
    "source_supported": FORBIDDEN_VERIFICATION_STATUS,
}


@dataclass(frozen=True)
class CandidateClaimProposal:
    claim_id: str
    claim_type: str
    status: str
    subject: str
    predicate: str
    object: str
    source_span_ids: tuple[str, ...]
    raw_value: str | None = None
    normalized_value: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateProposal:
    proposal_version: str
    proposal_kind: str
    candidate_kind: str
    claims: tuple[CandidateClaimProposal, ...]
    verification_request: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateProposalValidationResult:
    status: str
    accepted: bool
    proposal_kind: str | None
    candidate_kind: str | None
    claim_count: int
    issues: tuple[str, ...]


@dataclass(frozen=True)
class CandidateProposalAdapterResult:
    status: str
    claim_count: int
    candidate_claims: tuple[dict, ...]
    issues: tuple[str, ...] = ()
