"""Renderer Guard + Answer Verification models and machine constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# --- Final statuses ---
RENDER_VALID = "RENDER_VALID"
RENDER_INVALID = "RENDER_INVALID"
RENDER_NEEDS_CLAIM_MAP = "RENDER_NEEDS_CLAIM_MAP"
RENDER_EXCEEDS_VALIDATED_MATERIAL = "RENDER_EXCEEDS_VALIDATED_MATERIAL"
RENDER_POLICY_BLOCKED = "RENDER_POLICY_BLOCKED"

# --- Reason codes ---
RENDER_GUARD_PASSED = "RENDER_GUARD_PASSED"
MISSING_ANSWER_ID = "MISSING_ANSWER_ID"
MISSING_RENDERED_TEXT = "MISSING_RENDERED_TEXT"
MISSING_CLAIM_REFS = "MISSING_CLAIM_REFS"
UNKNOWN_CLAIM_ID = "UNKNOWN_CLAIM_ID"
CLAIM_STATUS_NOT_ALLOWED = "CLAIM_STATUS_NOT_ALLOWED"
RENDERED_TEXT_NOT_CANONICAL = "RENDERED_TEXT_NOT_CANONICAL"
UNSUPPORTED_SEGMENT_PRESENT = "UNSUPPORTED_SEGMENT_PRESENT"
SOURCE_SPAN_MISMATCH = "SOURCE_SPAN_MISMATCH"
INVALID_RENDER_MODE = "INVALID_RENDER_MODE"
INVALID_RENDER_INPUT = "INVALID_RENDER_INPUT"
NON_FINITE_VALUE = "NON_FINITE_VALUE"
UNKNOWN_FIELD = "UNKNOWN_FIELD"

# --- Render modes ---
CANONICAL_ONLY = "CANONICAL_ONLY"
NORMALIZED_CANONICAL = "NORMALIZED_CANONICAL"
EXPLICIT_ALLOWED_RENDERING = "EXPLICIT_ALLOWED_RENDERING"

ALLOWED_RENDER_MODES = frozenset({
    CANONICAL_ONLY,
    NORMALIZED_CANONICAL,
    EXPLICIT_ALLOWED_RENDERING,
})

# --- Default allowed claim statuses (conservative) ---
DEFAULT_ALLOWED_CLAIM_STATUSES = frozenset({"VERIFIED", "CERTIFIED"})


@dataclass(frozen=True)
class RendererGuardPolicy:
    allowed_claim_statuses: frozenset[str] = field(
        default_factory=lambda: frozenset(DEFAULT_ALLOWED_CLAIM_STATUSES)
    )


@dataclass(frozen=True)
class AnswerClaimRef:
    claim_id: str
    rendered_text: str
    role: str = ""
    source_span_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatedClaimView:
    claim_id: str
    subject: str
    relation: str
    object: str
    canonical_text: str
    final_status: str
    source_span_ids: tuple[str, ...] = ()
    support_profile_id: str | None = None
    proof_trace_id: str | None = None
    allowed_renderings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnswerDraft:
    answer_id: str
    render_mode: str
    rendered_text: str
    claim_refs: tuple[AnswerClaimRef, ...]
    unsupported_segments: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RendererGuardDecision:
    answer_id: str
    final_status: str
    valid: bool
    reason_code: str
    issues: tuple[str, ...]
    claim_count: int
    accepted_claim_ids: tuple[str, ...]
    rejected_claim_ids: tuple[str, ...]
    render_mode: str
