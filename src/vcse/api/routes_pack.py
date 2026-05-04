"""Pack bundle verification routes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_BUNDLE_INVALID, API_NOT_FOUND, OperationalError
from vcse.api.models import make_ok_response
from vcse.distribution.verify import verify_pack_bundle

router = APIRouter()


class BundleVerifyRequest(BaseModel):
    bundle_path: str
    public_key_path: Optional[str] = None


@router.post("/pack/verify-bundle")
def bundle_verify(http_request: Request, req: BundleVerifyRequest) -> dict:
    bundle_path = Path(req.bundle_path)
    if not bundle_path.exists():
        raise OperationalError(API_NOT_FOUND, f"Bundle path not found: {req.bundle_path}", 404, "bundle_path")

    public_key_path = Path(req.public_key_path) if req.public_key_path else None
    if public_key_path is not None and not public_key_path.exists():
        raise OperationalError(API_NOT_FOUND, f"Public key not found: {req.public_key_path}", 404, "public_key_path")

    try:
        result = verify_pack_bundle(bundle_path, public_key_path)
    except Exception as exc:
        raise OperationalError(API_BUNDLE_INVALID, f"Bundle verification error: {exc}", 422, "bundle_path")

    return make_ok_response(http_request, {
        "bundle_status": result.status,
        "bundle_id": result.bundle_id,
        "pack_id": result.pack_id,
        "file_count": result.file_count,
        "signature_status": result.signature_status,
        "integrity_status": result.integrity_status,
        "issues": list(result.issues),
    })
