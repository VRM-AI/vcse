"""Ontology governance foundation for VCSE."""

from vcse.ontology.model import (
    ACTIVE,
    APPROVED,
    CONFLICT_CHECKED,
    DEPRECATED,
    IMPACT_ANALYZED,
    KNOWN_LIFECYCLE_STATES,
    NEEDS_REVISION,
    NON_AUTHORITATIVE_STATES,
    PROPOSED,
    QUARANTINED,
    REGRESSION_TESTED,
    REJECTED,
    ROLLED_BACK,
    STAGED,
    STRUCTURALLY_VALID,
    SUPERSEDED,
    OntologyClaimType,
    OntologyEntityType,
    OntologyRegistry,
    OntologyRelation,
)
from vcse.ontology.lifecycle import (
    ONTOLOGY_STATUS_UNKNOWN,
    ONTOLOGY_TRANSITION_ALLOWED,
    ONTOLOGY_TRANSITION_INVALID,
    is_active,
    is_authoritative_for_source_support,
    validate_lifecycle_transition,
)
from vcse.ontology.registry import (
    OntologyRegistryError,
    active_relation_view_from_ontology_relation,
    get_relation,
    relation_map_for_source_support,
)
from vcse.ontology.serialize import (
    ontology_registry_to_dict,
    ontology_registry_to_json,
    ontology_relation_to_dict,
)
from vcse.ontology.validate import (
    ONTOLOGY_INVALID,
    ONTOLOGY_VALID,
    OntologyValidationIssue,
    OntologyValidationResult,
    validate_active_relation_requirements,
    validate_ontology_registry,
    validate_ontology_relation,
)

__all__ = [
    "ACTIVE", "APPROVED", "CONFLICT_CHECKED", "DEPRECATED", "IMPACT_ANALYZED",
    "KNOWN_LIFECYCLE_STATES", "NEEDS_REVISION", "NON_AUTHORITATIVE_STATES",
    "PROPOSED", "QUARANTINED", "REGRESSION_TESTED", "REJECTED", "ROLLED_BACK",
    "STAGED", "STRUCTURALLY_VALID", "SUPERSEDED",
    "OntologyClaimType", "OntologyEntityType", "OntologyRegistry", "OntologyRelation",
    "ONTOLOGY_STATUS_UNKNOWN", "ONTOLOGY_TRANSITION_ALLOWED", "ONTOLOGY_TRANSITION_INVALID",
    "is_active", "is_authoritative_for_source_support", "validate_lifecycle_transition",
    "OntologyRegistryError", "active_relation_view_from_ontology_relation",
    "get_relation", "relation_map_for_source_support",
    "ontology_registry_to_dict", "ontology_registry_to_json", "ontology_relation_to_dict",
    "ONTOLOGY_INVALID", "ONTOLOGY_VALID",
    "OntologyValidationIssue", "OntologyValidationResult",
    "validate_active_relation_requirements", "validate_ontology_registry",
    "validate_ontology_relation",
]
