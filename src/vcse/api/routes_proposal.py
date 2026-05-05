"""Candidate Proposal validation route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from vcse.api.errors import API_INVALID_REQUEST, OperationalError
from vcse.api.models import make_ok_response
from vcse.proposal.validate import validate_candidate_proposal_dict

router = APIRouter()


@router.post("/proposal/validate")
def proposal_validate(http_request: Request, body: dict[str, Any]) -> dict:
    result = validate_candidate_proposal_dict(body)
    return make_ok_response(
        http_request,
        {
            "proposal_status": result.status,
            "accepted": result.accepted,
            "claim_count": result.claim_count,
            "issues": list(result.issues),
        },
    )
