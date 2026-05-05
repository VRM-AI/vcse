"""Ledger Event Taxonomy validation route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from vcse.api.models import make_ok_response
from vcse.ledger.validate import validate_ledger_event_dict

router = APIRouter()


@router.post("/ledger/validate")
def ledger_validate(http_request: Request, body: dict[str, Any]) -> dict:
    result = validate_ledger_event_dict(body)
    return make_ok_response(
        http_request,
        {
            "ledger_event_status": result.status,
            "valid": result.valid,
            "event_type": result.event_type,
            "issue_count": result.issue_count,
            "issues": list(result.issues),
        },
    )
