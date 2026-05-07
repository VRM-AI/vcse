"""Renderer Guard + Answer Verification API route."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.models import make_ok_response
from vcse.render.model import (
    AnswerClaimRef,
    AnswerDraft,
    RendererGuardPolicy,
    ValidatedClaimView,
    DEFAULT_ALLOWED_CLAIM_STATUSES,
)
from vcse.render.serialize import renderer_guard_decision_to_dict
from vcse.render.service import verify_rendered_answer

router = APIRouter()


class AnswerClaimRefPayload(BaseModel):
    claim_id: str
    rendered_text: str
    role: str = ""
    source_span_ids: list[str] = []
    metadata: dict[str, Any] = {}


class ValidatedClaimViewPayload(BaseModel):
    claim_id: str
    subject: str
    relation: str
    object: str
    canonical_text: str
    final_status: str
    source_span_ids: list[str] = []
    support_profile_id: Optional[str] = None
    proof_trace_id: Optional[str] = None
    allowed_renderings: list[str] = []
    metadata: dict[str, Any] = {}


class AnswerDraftPayload(BaseModel):
    answer_id: str
    render_mode: str
    rendered_text: str
    claim_refs: list[AnswerClaimRefPayload] = []
    unsupported_segments: list[str] = []
    metadata: dict[str, Any] = {}


class RenderVerifyRequest(BaseModel):
    answer: AnswerDraftPayload
    claims: list[ValidatedClaimViewPayload] = []
    allowed_claim_statuses: Optional[list[str]] = None


@router.post("/render/verify")
def render_verify(http_request: Request, req: RenderVerifyRequest) -> dict:
    answer = AnswerDraft(
        answer_id=req.answer.answer_id,
        render_mode=req.answer.render_mode,
        rendered_text=req.answer.rendered_text,
        claim_refs=tuple(
            AnswerClaimRef(
                claim_id=r.claim_id,
                rendered_text=r.rendered_text,
                role=r.role,
                source_span_ids=tuple(r.source_span_ids),
                metadata=r.metadata,
            )
            for r in req.answer.claim_refs
        ),
        unsupported_segments=tuple(req.answer.unsupported_segments),
        metadata=req.answer.metadata,
    )

    claim_views = {
        c.claim_id: ValidatedClaimView(
            claim_id=c.claim_id,
            subject=c.subject,
            relation=c.relation,
            object=c.object,
            canonical_text=c.canonical_text,
            final_status=c.final_status,
            source_span_ids=tuple(c.source_span_ids),
            support_profile_id=c.support_profile_id,
            proof_trace_id=c.proof_trace_id,
            allowed_renderings=tuple(c.allowed_renderings),
            metadata=c.metadata,
        )
        for c in req.claims
    }

    if req.allowed_claim_statuses is not None:
        policy = RendererGuardPolicy(
            allowed_claim_statuses=frozenset(req.allowed_claim_statuses)
        )
    else:
        policy = RendererGuardPolicy()

    decision = verify_rendered_answer(answer, claim_views, policy)
    d = renderer_guard_decision_to_dict(decision)

    return make_ok_response(http_request, {"decision": d})
