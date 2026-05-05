"""Ontology governance validation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from vcse.ontology.model import (
    ACTIVE,
    KNOWN_LIFECYCLE_STATES,
    OntologyRegistry,
    OntologyRelation,
)
from vcse.support.profiles import KNOWN_PROFILES


@dataclass(frozen=True)
class OntologyValidationIssue:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class OntologyValidationResult:
    status: str
    issue_count: int
    issues: tuple[OntologyValidationIssue, ...]


ONTOLOGY_VALID = "ONTOLOGY_VALID"
ONTOLOGY_INVALID = "ONTOLOGY_INVALID"


def validate_ontology_relation(relation: OntologyRelation) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    path_prefix = f"relation[{relation.relation_id!r}]"

    if not str(relation.relation_id).strip():
        issues.append(OntologyValidationIssue(
            "MISSING_RELATION_ID", "relation_id is required", "relation_id"
        ))

    if not str(relation.ontology_version).strip():
        issues.append(OntologyValidationIssue(
            "ONTOLOGY_VERSION_REQUIRED", "ontology_version is required", f"{path_prefix}.ontology_version"
        ))

    if not relation.activation_status:
        issues.append(OntologyValidationIssue(
            "MISSING_ACTIVATION_STATUS", "activation_status is required", f"{path_prefix}.activation_status"
        ))
    elif relation.activation_status not in KNOWN_LIFECYCLE_STATES:
        issues.append(OntologyValidationIssue(
            "INVALID_ACTIVATION_STATUS",
            f"unknown activation_status: {relation.activation_status!r}",
            f"{path_prefix}.activation_status",
        ))
    elif relation.activation_status != relation.activation_status.upper():
        issues.append(OntologyValidationIssue(
            "STATUS_CASING_INVALID",
            f"activation_status must be UPPER_SNAKE_CASE: {relation.activation_status!r}",
            f"{path_prefix}.activation_status",
        ))

    if relation.activation_status == ACTIVE:
        if not relation.support_profile_id:
            issues.append(OntologyValidationIssue(
                "ACTIVE_RELATION_MISSING_SUPPORT_PROFILE",
                "ACTIVE relation requires support_profile_id",
                f"{path_prefix}.support_profile_id",
            ))
        elif relation.support_profile_id not in KNOWN_PROFILES:
            issues.append(OntologyValidationIssue(
                "ACTIVE_RELATION_INVALID_SUPPORT_PROFILE",
                f"support_profile_id {relation.support_profile_id!r} is not a known profile",
                f"{path_prefix}.support_profile_id",
            ))

    _check_nan_inf_mapping(relation.metadata, f"{path_prefix}.metadata", issues)
    return issues


def validate_ontology_registry(registry: OntologyRegistry) -> OntologyValidationResult:
    issues: list[OntologyValidationIssue] = []

    if not str(registry.ontology_version).strip():
        issues.append(OntologyValidationIssue(
            "ONTOLOGY_VERSION_REQUIRED", "ontology_version is required", "ontology_version"
        ))

    for relation in registry.relations:
        issues.extend(validate_ontology_relation(relation))

    for et in registry.entity_types:
        if not str(et.entity_type_id).strip():
            issues.append(OntologyValidationIssue(
                "MISSING_RELATION_ID", "entity_type_id is required", "entity_type_id"
            ))
        if not str(et.activation_status).strip():
            issues.append(OntologyValidationIssue(
                "MISSING_ACTIVATION_STATUS", "activation_status is required", f"entity_type[{et.entity_type_id}].activation_status"
            ))

    status = ONTOLOGY_INVALID if issues else ONTOLOGY_VALID
    return OntologyValidationResult(
        status=status,
        issue_count=len(issues),
        issues=tuple(issues),
    )


def validate_active_relation_requirements(relation: OntologyRelation) -> list[OntologyValidationIssue]:
    """Additional checks specifically for ACTIVE relations used in source-support flows."""
    issues: list[OntologyValidationIssue] = []
    if relation.activation_status != ACTIVE:
        issues.append(OntologyValidationIssue(
            "NON_ACTIVE_RELATION_NOT_AUTHORITATIVE",
            f"relation {relation.relation_id!r} has status {relation.activation_status!r} — only ACTIVE relations are authoritative",
            f"relation[{relation.relation_id}].activation_status",
        ))
    if not relation.support_profile_id:
        issues.append(OntologyValidationIssue(
            "MISSING_SUPPORT_PROFILE",
            "support_profile_id is required for authoritative relations",
            f"relation[{relation.relation_id}].support_profile_id",
        ))
    elif relation.support_profile_id not in KNOWN_PROFILES:
        issues.append(OntologyValidationIssue(
            "INVALID_SUPPORT_PROFILE",
            f"support_profile_id {relation.support_profile_id!r} is not a known profile",
            f"relation[{relation.relation_id}].support_profile_id",
        ))
    return issues


def _check_nan_inf_mapping(
    m: Mapping[str, Any],
    prefix: str,
    issues: list[OntologyValidationIssue],
) -> None:
    for k, v in m.items():
        path = f"{prefix}.{k}"
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            issues.append(OntologyValidationIssue("NON_FINITE_VALUE", f"NaN/Inf at {path}", path))
        elif isinstance(v, dict):
            _check_nan_inf_mapping(v, path, issues)
        elif isinstance(v, (list, tuple)):
            for i, item in enumerate(v):
                if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
                    issues.append(OntologyValidationIssue("NON_FINITE_VALUE", f"NaN/Inf at {path}[{i}]", f"{path}[{i}]"))
