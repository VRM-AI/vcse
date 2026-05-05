"""Deterministic source support evaluation route."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_INVALID_REQUEST, OperationalError
from vcse.api.models import make_ok_response
from vcse.support.model import ActiveRelationView, CandidateClaimView, SourceSpan
from vcse.support.serialize import source_support_decision_to_dict
from vcse.support.service import evaluate_source_support

router = APIRouter()


class SourceSpanPayload(BaseModel):
    source_id: str
    source_span_id: str
    text: str
    source_uri: Optional[str] = None
    content_hash: Optional[str] = None
    span_hash: Optional[str] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    metadata: dict[str, Any] = {}


class ActiveRelationPayload(BaseModel):
    relation_id: str
    support_profile_id: str
    subject_types: list[str] = []
    object_types: list[str] = []
    functional: bool = False
    ontology_version: Optional[str] = None
    allowed_support_profiles: list[str] = []


class ClaimPayload(BaseModel):
    claim_id: str
    subject: str
    relation: str
    object: str
    source_span_ids: list[str] = []
    ontology_version: Optional[str] = None


class SupportEvaluateRequest(BaseModel):
    claim: ClaimPayload
    source_spans: list[SourceSpanPayload] = []
    active_relations: list[ActiveRelationPayload] = []


@router.post("/support/evaluate")
def support_evaluate(http_request: Request, req: SupportEvaluateRequest) -> dict:
    if not req.claim.relation:
        raise OperationalError(API_INVALID_REQUEST, "claim.relation is required", 400, "claim.relation")

    claim = CandidateClaimView(
        claim_id=req.claim.claim_id,
        subject=req.claim.subject,
        relation=req.claim.relation,
        object=req.claim.object,
        source_span_ids=tuple(req.claim.source_span_ids),
        ontology_version=req.claim.ontology_version,
    )

    spans: dict[str, SourceSpan] = {
        s.source_span_id: SourceSpan(
            source_id=s.source_id,
            source_span_id=s.source_span_id,
            text=s.text,
            source_uri=s.source_uri,
            content_hash=s.content_hash,
            span_hash=s.span_hash,
            start_offset=s.start_offset,
            end_offset=s.end_offset,
            metadata=s.metadata,
        )
        for s in req.source_spans
    }

    relations: dict[str, ActiveRelationView] = {
        r.relation_id: ActiveRelationView(
            relation_id=r.relation_id,
            support_profile_id=r.support_profile_id,
            subject_types=tuple(r.subject_types),
            object_types=tuple(r.object_types),
            functional=r.functional,
            ontology_version=r.ontology_version,
            allowed_support_profiles=tuple(r.allowed_support_profiles),
        )
        for r in req.active_relations
    }

    decision = evaluate_source_support(claim, spans, relations)
    d = source_support_decision_to_dict(decision)

    return make_ok_response(http_request, {
        "support_status": d["final_status"],
        "supported": d["supported"],
        "reason_code": d["reason_code"],
        "claim_id": d["claim_id"],
        "relation_id": d["relation_id"],
        "support_profile_id": d["support_profile_id"],
        "source_span_ids": d["source_span_ids"],
        "issues": d["issues"],
    })
