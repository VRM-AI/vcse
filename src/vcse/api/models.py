"""Operational response contract for VCSE API."""

from __future__ import annotations

from typing import Any

from vcse.api.config import API_VERSION


def _get_request_id(request: Any) -> str:
    return getattr(getattr(request, "state", None), "request_id", "")


def make_ok_response(request: Any, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "OK",
        "version": API_VERSION,
        "request_id": _get_request_id(request),
        "data": data,
        "errors": [],
    }


def make_error_response(
    request: Any,
    code: str,
    message: str,
    path: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "version": API_VERSION,
        "request_id": _get_request_id(request),
        "data": {},
        "errors": [{"code": code, "message": message, "path": path, "details": details or {}}],
    }
