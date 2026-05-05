"""Ontology registry resolution — bridge from governance to source-support."""

from __future__ import annotations

from vcse.ontology.lifecycle import is_authoritative_for_source_support
from vcse.ontology.model import ACTIVE, OntologyRegistry, OntologyRelation
from vcse.ontology.validate import validate_active_relation_requirements
from vcse.support.model import ActiveRelationView
from vcse.support.profiles import KNOWN_PROFILES


class OntologyRegistryError(ValueError):
    """Raised when an ACTIVE relation has an invalid support profile."""


def get_relation(registry: OntologyRegistry, relation_id: str) -> OntologyRelation | None:
    for relation in registry.relations:
        if relation.relation_id == relation_id:
            return relation
    return None


def active_relation_view_from_ontology_relation(relation: OntologyRelation) -> ActiveRelationView:
    """
    Convert an ACTIVE OntologyRelation to an ActiveRelationView for source-support evaluation.

    Raises OntologyRegistryError if relation is not ACTIVE or has invalid profile.
    """
    issues = validate_active_relation_requirements(relation)
    if issues:
        codes = ", ".join(i.code for i in issues)
        raise OntologyRegistryError(
            f"relation {relation.relation_id!r} cannot be used for source support: {codes}"
        )
    return ActiveRelationView(
        relation_id=relation.relation_id,
        support_profile_id=relation.support_profile_id or "",
        subject_types=relation.subject_types,
        object_types=relation.object_types,
        functional=relation.functional,
        ontology_version=relation.ontology_version,
        allowed_support_profiles=relation.allowed_support_profiles,
    )


def relation_map_for_source_support(
    registry: OntologyRegistry,
) -> dict[str, ActiveRelationView]:
    """
    Return only ACTIVE relations with valid support_profile_id as ActiveRelationView map.

    Non-ACTIVE relations (PROPOSED, APPROVED, STAGED, etc.) are excluded.
    ACTIVE relations with invalid/missing support_profile_id raise OntologyRegistryError.
    """
    result: dict[str, ActiveRelationView] = {}
    for relation in registry.relations:
        if not is_authoritative_for_source_support(relation.activation_status):
            continue
        # ACTIVE — must have valid support_profile_id
        if not relation.support_profile_id or relation.support_profile_id not in KNOWN_PROFILES:
            raise OntologyRegistryError(
                f"ACTIVE relation {relation.relation_id!r} has invalid support_profile_id "
                f"{relation.support_profile_id!r} — cannot build source-support map"
            )
        result[relation.relation_id] = active_relation_view_from_ontology_relation(relation)
    return result
