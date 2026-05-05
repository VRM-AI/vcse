"""Reason route — functional in v6.11.0 via reason service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import (
    API_INTERNAL_ERROR,
    API_NOT_FOUND,
    API_PROOF_INVALID,
    API_RUNTIME_INVALID,
    OperationalError,
)
from vcse.api.models import make_ok_response
from vcse.reasoning.service import ReasonServiceRequest, run_reason_service
from vcse.runtime.hardening import RuntimeArtifactError

router = APIRouter()


class ReasonRequest(BaseModel):
    csrf_path: str
    proof_index_path: Optional[str] = None
    trusted_only: bool = False
    explain: bool = False
    max_results: Optional[int] = None


@router.post("/reason")
def reason(http_request: Request, req: ReasonRequest) -> dict:
    if not req.csrf_path:
        raise OperationalError(
            API_NOT_FOUND,
            "csrf_path is required",
            400,
            "csrf_path",
        )

    csrf_path = Path(req.csrf_path)
    if not csrf_path.exists():
        raise OperationalError(API_NOT_FOUND, f"File not found: {req.csrf_path}", 404, "csrf_path")

    proof_index_path: Path | None = None
    if req.proof_index_path is not None:
        proof_index_path = Path(req.proof_index_path)
        if not proof_index_path.exists():
            raise OperationalError(
                API_NOT_FOUND,
                f"Proof index not found: {req.proof_index_path}",
                404,
                "proof_index_path",
            )

    service_request = ReasonServiceRequest(
        csrf_path=csrf_path,
        proof_index_path=proof_index_path,
        trusted_only=req.trusted_only,
        explain=req.explain,
        max_results=req.max_results,
    )

    try:
        result = run_reason_service(service_request)
    except FileNotFoundError as exc:
        path_field = "proof_index_path" if proof_index_path and "Proof index" in str(exc) else "csrf_path"
        raise OperationalError(API_NOT_FOUND, str(exc), 404, path_field)
    except RuntimeArtifactError as exc:
        msg = str(exc)
        if "PROOF_VALIDATION_FAILED" in msg:
            raise OperationalError(API_PROOF_INVALID, msg, 422, "proof_index_path")
        raise OperationalError(API_RUNTIME_INVALID, msg, 422, "csrf_path")
    except Exception as exc:
        raise OperationalError(API_INTERNAL_ERROR, f"Reason service failed: {exc}", 500, "")

    return make_ok_response(
        http_request,
        {
            "reason_status": result.status,
            "inferred_count": result.inferred_count,
            "inferred_claims": list(result.inferred_claims),
            "explanations": result.explanations,
        },
    )
