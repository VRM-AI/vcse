"""API middleware and exception handlers."""

from __future__ import annotations

import asyncio
import logging
import uuid
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vcse.api.errors import (
    API_INTERNAL_ERROR,
    API_INVALID_REQUEST,
    APIError,
    OperationalError,
)
from vcse.api.models import make_error_response
from vcse.perf import stage


_LOG = logging.getLogger("vcse.api")


def install_error_handlers(app: FastAPI, *, max_request_bytes: int = 1_000_000, timeout_seconds: float = 30.0) -> None:
    def _request_id_header(request: Request) -> dict[str, str]:
        request_id = getattr(getattr(request, "state", None), "request_id", "")
        return {"X-Request-ID": request_id} if request_id else {}

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming_id = request.headers.get("x-request-id")
        request_id = incoming_id if incoming_id else uuid.uuid4().hex
        request.state.request_id = request_id
        started = perf_counter()

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > max_request_bytes:
                    return JSONResponse(
                        status_code=413,
                        content=make_error_response(
                            request,
                            API_INVALID_REQUEST,
                            "Request body exceeds configured limit",
                            "body",
                        ),
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass

        try:
            with stage("api.request"):
                response = await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content=make_error_response(
                    request,
                    API_INVALID_REQUEST,
                    "Request timed out",
                ),
                headers={"X-Request-ID": request_id},
            )

        duration_ms = (perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.3f}"
        _LOG.info(
            "request complete",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": getattr(response, "status_code", 200),
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(OperationalError)
    async def handle_operational_error(request: Request, exc: OperationalError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error_response(request, exc.code, exc.message, exc.path),
            headers=_request_id_header(request),
        )

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error_response(request, exc.code, exc.message),
            headers=_request_id_header(request),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=make_error_response(request, API_INVALID_REQUEST, "Malformed request payload"),
            headers=_request_id_header(request),
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
        _LOG.exception(
            "unhandled api error",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=500,
            content=make_error_response(request, API_INTERNAL_ERROR, "Internal server error"),
            headers=_request_id_header(request),
        )
