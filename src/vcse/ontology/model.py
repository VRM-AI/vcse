"""Ontology governance data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# --- Forward lifecycle states (UPPER_SNAKE_CASE) ---
PROPOSED = "PROPOSED"
STRUCTURALLY_VALID = "STRUCTURALLY_VALID"
IMPACT_ANALYZED = "IMPACT_ANALYZED"
CONFLICT_CHECKED = "CONFLICT_CHECKED"
REGRESSION_TESTED = "REGRESSION_TESTED"
APPROVED = "APPROVED"
STAGED = "STAGED"
ACTIVE = "ACTIVE"

# --- Side states ---
NEEDS_REVISION = "NEEDS_REVISION"
REJECTED = "REJECTED"
QUARANTINED = "QUARANTINED"
DEPRECATED = "DEPRECATED"
SUPERSEDED = "SUPERSEDED"
ROLLED_BACK = "ROLLED_BACK"

KNOWN_LIFECYCLE_STATES: frozenset[str] = frozenset({
    PROPOSED, STRUCTURALLY_VALID, IMPACT_ANALYZED, CONFLICT_CHECKED,
    REGRESSION_TESTED, APPROVED, STAGED, ACTIVE,
    NEEDS_REVISION, REJECTED, QUARANTINED, DEPRECATED, SUPERSEDED, ROLLED_BACK,
})

AUTHORITATIVE_STATES: frozenset[str] = frozenset({ACTIVE})

NON_AUTHORITATIVE_STATES: frozenset[str] = KNOWN_LIFECYCLE_STATES - AUTHORITATIVE_STATES


@dataclass(frozen=True)
class OntologyRelation:
    relation_id: str
    label: str
    support_profile_id: str | None
    activation_status: str
    ontology_version: str
    subject_types: tuple[str, ...] = ()
    object_types: tuple[str, ...] = ()
    functional: bool = False
    allowed_support_profiles: tuple[str, ...] = ()
    inverse_relation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OntologyEntityType:
    entity_type_id: str
    label: str
    activation_status: str
    ontology_version: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OntologyClaimType:
    claim_type_id: str
    label: str
    activation_status: str
    ontology_version: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OntologyRegistry:
    ontology_version: str
    relations: tuple[OntologyRelation, ...] = ()
    entity_types: tuple[OntologyEntityType, ...] = ()
    claim_types: tuple[OntologyClaimType, ...] = ()
