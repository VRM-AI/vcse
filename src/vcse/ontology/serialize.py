"""Deterministic ontology serialization."""

from __future__ import annotations

import json
import math
from typing import Any

from vcse.ontology.model import OntologyRegistry, OntologyRelation


def ontology_relation_to_dict(relation: OntologyRelation) -> dict[str, Any]:
    d = {
        "activation_status": relation.activation_status,
        "allowed_support_profiles": list(relation.allowed_support_profiles),
        "functional": relation.functional,
        "inverse_relation_id": relation.inverse_relation_id,
        "label": relation.label,
        "metadata": dict(relation.metadata),
        "object_types": list(relation.object_types),
        "ontology_version": relation.ontology_version,
        "relation_id": relation.relation_id,
        "subject_types": list(relation.subject_types),
        "support_profile_id": relation.support_profile_id,
    }
    _assert_json_safe(d)
    return d


def ontology_registry_to_dict(registry: OntologyRegistry) -> dict[str, Any]:
    d = {
        "claim_types": [
            {
                "activation_status": ct.activation_status,
                "claim_type_id": ct.claim_type_id,
                "label": ct.label,
                "metadata": dict(ct.metadata),
                "ontology_version": ct.ontology_version,
            }
            for ct in registry.claim_types
        ],
        "entity_types": [
            {
                "activation_status": et.activation_status,
                "entity_type_id": et.entity_type_id,
                "label": et.label,
                "metadata": dict(et.metadata),
                "ontology_version": et.ontology_version,
            }
            for et in registry.entity_types
        ],
        "ontology_version": registry.ontology_version,
        "relations": [ontology_relation_to_dict(r) for r in registry.relations],
    }
    _assert_json_safe(d)
    return d


def ontology_registry_to_json(registry: OntologyRegistry) -> str:
    return json.dumps(
        ontology_registry_to_dict(registry),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("NON_FINITE_VALUE: NaN/Inf not allowed in ontology serialization")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("JSON object keys must be strings")
            _assert_json_safe(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
