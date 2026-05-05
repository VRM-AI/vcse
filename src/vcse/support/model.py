"""Source support data models for deterministic GSR-readiness contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SourceSpan:
    source_id: str
    source_span_id: str
    text: str
    source_uri: str | None = None
    content_hash: str | None = None
    span_hash: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateClaimView:
    """Lightweight adapter model for source-support checks. Does not replace CMCF records."""

    claim_id: str
    subject: str
    relation: str
    object: str
    source_span_ids: tuple[str, ...] = ()
    ontology_version: str | None = None


@dataclass(frozen=True)
class ActiveRelationView:
    relation_id: str
    support_profile_id: str
    subject_types: tuple[str, ...] = ()
    object_types: tuple[str, ...] = ()
    functional: bool = False
    ontology_version: str | None = None
    allowed_support_profiles: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceSupportDecision:
    supported: bool
    final_status: str
    reason_code: str
    claim_id: str | None
    relation_id: str | None
    support_profile_id: str | None
    source_span_ids: tuple[str, ...]
    issues: tuple[str, ...] = ()


# Allowed final statuses (all UPPER_SNAKE_CASE)
FINAL_STATUS_SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
FINAL_STATUS_SOURCE_SUPPORT_FAILED = "SOURCE_SUPPORT_FAILED"
FINAL_STATUS_GROUNDED = "GROUNDED"
FINAL_STATUS_NEEDS_SOURCE = "NEEDS_SOURCE"
FINAL_STATUS_UNKNOWN_SOURCE_SPAN = "UNKNOWN_SOURCE_SPAN"
FINAL_STATUS_NEEDS_ONTOLOGY = "NEEDS_ONTOLOGY"
FINAL_STATUS_INVALID_ONTOLOGY_RELATION = "INVALID_ONTOLOGY_RELATION"
FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE = "EXPLORATORY_SUPPORT_CANDIDATE"

# Allowed reason codes (all UPPER_SNAKE_CASE)
REASON_SUPPORT_PROFILE_PASSED = "SUPPORT_PROFILE_PASSED"
REASON_SUPPORT_PROFILE_FAILED = "SUPPORT_PROFILE_FAILED"
REASON_MISSING_SOURCE_SPAN = "MISSING_SOURCE_SPAN"
REASON_UNKNOWN_SOURCE_SPAN = "UNKNOWN_SOURCE_SPAN"
REASON_RELATION_NOT_ACTIVE = "RELATION_NOT_ACTIVE"
REASON_MISSING_SUPPORT_PROFILE = "MISSING_SUPPORT_PROFILE"
REASON_INVALID_SUPPORT_PROFILE = "INVALID_SUPPORT_PROFILE"
REASON_EXPLORATORY_ONLY = "EXPLORATORY_ONLY"


def _check_nan_inf(value: Any, path: str) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError(f"NON_FINITE_VALUE: NaN/Inf not allowed at {path}")
    if isinstance(value, dict):
        for k, v in value.items():
            _check_nan_inf(v, f"{path}.{k}")
    if isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check_nan_inf(v, f"{path}[{i}]")
