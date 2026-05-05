"""Ontology governance validation route."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_INVALID_REQUEST, OperationalError
from vcse.api.models import make_ok_response
from vcse.ontology.model import (
    OntologyClaimType,
    OntologyEntityType,
    OntologyRegistry,
    OntologyRelation,
)
from vcse.ontology.validate import validate_ontology_registry

router = APIRouter()


class OntologyRelationPayload(BaseModel):
    relation_id: str
    label: str = ""
    support_profile_id: Optional[str] = None
    activation_status: str
    ontology_version: str
    subject_types: list[str] = []
    object_types: list[str] = []
    functional: bool = False
    allowed_support_profiles: list[str] = []
    inverse_relation_id: Optional[str] = None
    metadata: dict[str, Any] = {}


class OntologyEntityTypePayload(BaseModel):
    entity_type_id: str
    label: str = ""
    activation_status: str
    ontology_version: str
    metadata: dict[str, Any] = {}


class OntologyClaimTypePayload(BaseModel):
    claim_type_id: str
    label: str = ""
    activation_status: str
    ontology_version: str
    metadata: dict[str, Any] = {}


class OntologyValidateRequest(BaseModel):
    ontology_version: str
    relations: list[OntologyRelationPayload] = []
    entity_types: list[OntologyEntityTypePayload] = []
    claim_types: list[OntologyClaimTypePayload] = []


@router.post("/ontology/validate")
def ontology_validate(http_request: Request, req: OntologyValidateRequest) -> dict:
    if not req.ontology_version:
        raise OperationalError(API_INVALID_REQUEST, "ontology_version is required", 400, "ontology_version")

    relations = tuple(
        OntologyRelation(
            relation_id=r.relation_id,
            label=r.label,
            support_profile_id=r.support_profile_id,
            activation_status=r.activation_status,
            ontology_version=r.ontology_version,
            subject_types=tuple(r.subject_types),
            object_types=tuple(r.object_types),
            functional=r.functional,
            allowed_support_profiles=tuple(r.allowed_support_profiles),
            inverse_relation_id=r.inverse_relation_id,
            metadata=r.metadata,
        )
        for r in req.relations
    )

    entity_types = tuple(
        OntologyEntityType(
            entity_type_id=e.entity_type_id,
            label=e.label,
            activation_status=e.activation_status,
            ontology_version=e.ontology_version,
            metadata=e.metadata,
        )
        for e in req.entity_types
    )

    claim_types = tuple(
        OntologyClaimType(
            claim_type_id=c.claim_type_id,
            label=c.label,
            activation_status=c.activation_status,
            ontology_version=c.ontology_version,
            metadata=c.metadata,
        )
        for c in req.claim_types
    )

    registry = OntologyRegistry(
        ontology_version=req.ontology_version,
        relations=relations,
        entity_types=entity_types,
        claim_types=claim_types,
    )

    result = validate_ontology_registry(registry)

    return make_ok_response(http_request, {
        "ontology_status": result.status,
        "issue_count": result.issue_count,
        "issues": [
            {"code": iss.code, "message": iss.message, "path": iss.path}
            for iss in result.issues
        ],
    })
