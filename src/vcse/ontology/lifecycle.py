"""Ontology lifecycle transition validation."""

from __future__ import annotations

from vcse.ontology.model import (
    ACTIVE,
    APPROVED,
    CONFLICT_CHECKED,
    DEPRECATED,
    IMPACT_ANALYZED,
    KNOWN_LIFECYCLE_STATES,
    NEEDS_REVISION,
    PROPOSED,
    QUARANTINED,
    REGRESSION_TESTED,
    REJECTED,
    ROLLED_BACK,
    STAGED,
    STRUCTURALLY_VALID,
    SUPERSEDED,
)

ONTOLOGY_TRANSITION_ALLOWED = "ONTOLOGY_TRANSITION_ALLOWED"
ONTOLOGY_TRANSITION_INVALID = "ONTOLOGY_TRANSITION_INVALID"
ONTOLOGY_STATUS_UNKNOWN = "ONTOLOGY_STATUS_UNKNOWN"

# Allowed forward and side transitions
_ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset({
    # Forward chain
    (PROPOSED, STRUCTURALLY_VALID),
    (STRUCTURALLY_VALID, IMPACT_ANALYZED),
    (IMPACT_ANALYZED, CONFLICT_CHECKED),
    (CONFLICT_CHECKED, REGRESSION_TESTED),
    (REGRESSION_TESTED, APPROVED),
    (APPROVED, STAGED),
    (STAGED, ACTIVE),
    # Side transitions
    (PROPOSED, REJECTED),
    (STRUCTURALLY_VALID, NEEDS_REVISION),
    (IMPACT_ANALYZED, NEEDS_REVISION),
    (CONFLICT_CHECKED, NEEDS_REVISION),
    (REGRESSION_TESTED, NEEDS_REVISION),
    (APPROVED, REJECTED),
    (STAGED, REJECTED),
    (ACTIVE, DEPRECATED),
    (ACTIVE, SUPERSEDED),
    (ACTIVE, ROLLED_BACK),
    # Quarantine from any non-terminal state
    (PROPOSED, QUARANTINED),
    (STRUCTURALLY_VALID, QUARANTINED),
    (IMPACT_ANALYZED, QUARANTINED),
    (CONFLICT_CHECKED, QUARANTINED),
    (REGRESSION_TESTED, QUARANTINED),
    (APPROVED, QUARANTINED),
    (STAGED, QUARANTINED),
    # Revision can re-enter forward chain
    (NEEDS_REVISION, STRUCTURALLY_VALID),
})


def validate_lifecycle_transition(from_status: str, to_status: str) -> tuple[bool, str]:
    """
    Validate an ontology lifecycle state transition.

    Returns (allowed: bool, reason_code: str).

    PROPOSED → ACTIVE is rejected (must traverse forward chain).
    APPROVED and STAGED are not ACTIVE.
    """
    if from_status not in KNOWN_LIFECYCLE_STATES:
        return False, ONTOLOGY_STATUS_UNKNOWN
    if to_status not in KNOWN_LIFECYCLE_STATES:
        return False, ONTOLOGY_STATUS_UNKNOWN
    if (from_status, to_status) in _ALLOWED_TRANSITIONS:
        return True, ONTOLOGY_TRANSITION_ALLOWED
    return False, ONTOLOGY_TRANSITION_INVALID


def is_active(status: str) -> bool:
    return status == ACTIVE


def is_authoritative_for_source_support(status: str) -> bool:
    """Only ACTIVE relations are authoritative for source-support evaluation."""
    return status == ACTIVE
