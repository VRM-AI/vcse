"""Runtime and proof index validation routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import (
    API_INVALID_REQUEST,
    API_NOT_FOUND,
    API_PROOF_INVALID,
    API_RUNTIME_INVALID,
    OperationalError,
)
from vcse.api.models import make_ok_response
from vcse.proof.validate import validate_proof_index
from vcse.runtime.validate import validate_csrf_index

router = APIRouter()


class RuntimeValidateRequest(BaseModel):
    csrf_path: str


class ProofValidateRequest(BaseModel):
    proof_path: str


@router.post("/runtime/validate")
def runtime_validate(http_request: Request, req: RuntimeValidateRequest) -> dict:
    csrf_path = Path(req.csrf_path)
    if not csrf_path.exists():
        raise OperationalError(API_NOT_FOUND, f"File not found: {req.csrf_path}", 404, "csrf_path")
    if not csrf_path.is_file():
        raise OperationalError(API_INVALID_REQUEST, f"Path is not a file: {req.csrf_path}", 400, "csrf_path")

    try:
        from vcse.runtime.serialize import load_csrf
        index = load_csrf(csrf_path)
    except Exception as exc:
        raise OperationalError(API_RUNTIME_INVALID, f"Failed to load runtime artifact: {exc}", 422, "csrf_path")

    result = validate_csrf_index(index)

    issues = [
        {"code": iss.code, "severity": iss.severity, "message": iss.message, "path": iss.path}
        for iss in result.issues
    ]
    return make_ok_response(http_request, {
        "validation_status": result.status,
        "issue_count": result.issue_count,
        "issues": issues,
    })


@router.post("/proof/validate")
def proof_validate(http_request: Request, req: ProofValidateRequest) -> dict:
    proof_path = Path(req.proof_path)
    if not proof_path.exists():
        raise OperationalError(API_NOT_FOUND, f"File not found: {req.proof_path}", 404, "proof_path")
    if not proof_path.is_file():
        raise OperationalError(API_INVALID_REQUEST, f"Path is not a file: {req.proof_path}", 400, "proof_path")

    try:
        from vcse.proof.loader import load_proof_index
        index = load_proof_index(proof_path)
    except Exception as exc:
        raise OperationalError(API_PROOF_INVALID, f"Failed to load proof index: {exc}", 422, "proof_path")

    result = validate_proof_index(index)

    issues = [
        {"code": iss.code, "severity": iss.severity, "message": iss.message, "path": iss.path}
        for iss in result.issues
    ]
    return make_ok_response(http_request, {
        "validation_status": result.status,
        "issue_count": result.issue_count,
        "issues": issues,
    })
