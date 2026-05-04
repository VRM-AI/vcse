"""Structured deterministic query route."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_INVALID_REQUEST, API_NOT_FOUND, API_RUNTIME_INVALID, OperationalError
from vcse.api.models import make_ok_response
from vcse.query import StructuredQuery, StructuredQueryEngine
from vcse.runtime.hardening import RuntimeArtifactError, load_csrf_checked

router = APIRouter()


class QueryRequest(BaseModel):
    csrf_path: str
    subject: Optional[str] = None
    relation: Optional[str] = None
    object: Optional[str] = None
    trusted_only: bool = False
    explain: bool = False
    proof_index_path: Optional[str] = None


@router.post("/query")
def query(http_request: Request, req: QueryRequest) -> dict:
    if not any([req.subject, req.relation, req.object]):
        raise OperationalError(
            API_INVALID_REQUEST,
            "At least one of subject, relation, or object must be provided",
            400,
            "query_filter",
        )

    csrf_path = Path(req.csrf_path)
    if not csrf_path.exists():
        raise OperationalError(API_NOT_FOUND, f"File not found: {req.csrf_path}", 404, "csrf_path")

    try:
        runtime = load_csrf_checked(csrf_path)
    except RuntimeArtifactError as exc:
        raise OperationalError(API_RUNTIME_INVALID, str(exc), 422, "csrf_path")
    except Exception as exc:
        raise OperationalError(API_RUNTIME_INVALID, f"Failed to load runtime artifact: {exc}", 422, "csrf_path")

    structured_query = StructuredQuery(
        subject=req.subject,
        relation=req.relation,
        object=req.object,
        trusted_only=req.trusted_only,
    )

    result = StructuredQueryEngine().query_csrf(runtime, structured_query)

    return make_ok_response(http_request, {
        "status": result.status,
        "result_count": result.result_count,
        "results": list(result.results),
        "packs_searched": list(result.packs_searched),
        "packs_skipped": list(result.packs_skipped),
        "rows_examined": result.rows_examined,
        "filters_applied": list(result.filters_applied),
    })
