"""Reason route — deferred to v6.11 (API_UNSUPPORTED_OPERATION)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_UNSUPPORTED_OPERATION, OperationalError

router = APIRouter()


class ReasonRequest(BaseModel):
    csrf_path: Optional[str] = None
    proof_index_path: Optional[str] = None
    trusted_only: bool = False
    explain: bool = False


@router.post("/reason")
def reason(http_request: Request, req: ReasonRequest) -> dict:
    raise OperationalError(
        API_UNSUPPORTED_OPERATION,
        "The /reason endpoint is not yet available in v6.10. "
        "Use the vcse reason CLI command or await v6.11.",
        501,
        "",
    )
