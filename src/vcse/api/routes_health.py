"""Operational health, readiness, and liveness routes."""

from __future__ import annotations

import sys

from fastapi import APIRouter, Request

from vcse.api.config import API_VERSION
from vcse.api.models import make_ok_response

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    return make_ok_response(request, {"service": "vcse", "health": "HEALTHY"})


@router.get("/version")
def version(request: Request) -> dict:
    return make_ok_response(request, {
        "vcse_version": API_VERSION,
        "python_version": sys.version,
        "api_status": "READY",
    })


@router.get("/ready")
def ready(request: Request) -> dict:
    return make_ok_response(request, {"ready": "READY"})


@router.get("/live")
def live(request: Request) -> dict:
    return make_ok_response(request, {"alive": "ALIVE"})
