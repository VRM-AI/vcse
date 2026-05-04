# VCSE v6.10.0 API/Server Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add operational HTTP endpoints (health/readiness/liveness, runtime/proof/bundle validation, query, reason) that expose VCSE capabilities without weakening any correctness, trust, or proof invariants.

**Architecture:** New operational routes live alongside the existing OpenAI-compat `/v1/*` routes under a shared FastAPI app. New routes use a unified `VcseResponse` JSON contract (`status/version/request_id/data/errors`). Existing `/v1/*` routes and their tests are untouched except that `/health` is moved to `routes_health.py` with the new contract format.

**Tech Stack:** FastAPI, Pydantic v2, httpx TestClient, vcse.runtime/proof/distribution/query internals (no LLM, no network, no auto-trust).

---

## File Map

### Create
- `src/vcse/api/models.py` — `VcseResponse`, `VcseError`, `make_ok_response()`, `make_error_response()`
- `src/vcse/api/routes_health.py` — `/health`, `/version`, `/ready`, `/live`
- `src/vcse/api/routes_runtime.py` — `/runtime/validate`, `/proof/validate`
- `src/vcse/api/routes_pack.py` — `/pack/verify-bundle`
- `src/vcse/api/routes_query.py` — `/query`
- `src/vcse/api/routes_reason.py` — `/reason` (returns `API_UNSUPPORTED_OPERATION`)
- `tests/test_api_server.py` — all 17 directive-required tests

### Modify
- `src/vcse/api/errors.py` — add `OperationalError`, add 7 new error code constants
- `src/vcse/api/middleware.py` — echo `X-Request-ID` header if present; add `OperationalError` handler
- `src/vcse/api/server.py` — register the 5 new routers
- `src/vcse/api/routes.py` — remove the `/health` route (moved to `routes_health.py`); update `test_api.py::test_health`
- `tests/test_api.py` — update `test_health` to new format (`"OK"`, new data shape)
- `src/vcse/__init__.py` — bump `__version__` to `"6.10.0"`
- `pyproject.toml` — bump version to `6.10.0`
- `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `README.md` — add operational API section

---

## Task 1: Foundation — models.py + errors.py

**Files:**
- Create: `src/vcse/api/models.py`
- Modify: `src/vcse/api/errors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_server.py` with tests 1 and 16 (app factory + UPPER_SNAKE_CASE contract):

```python
"""Tests for VCSE v6.10.0 operational API server."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vcse.api.server import create_app
from vcse import __version__


def _client() -> TestClient:
    return TestClient(create_app())


# --- Test 1: create_app returns FastAPI app ---
def test_create_app_returns_fastapi() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


# --- Test 16: all machine statuses are UPPER_SNAKE_CASE ---
def test_health_status_is_upper_snake_case() -> None:
    resp = _client().get("/health")
    payload = resp.json()
    assert payload["status"] == payload["status"].upper()
    assert payload["data"]["health"] == payload["data"]["health"].upper()
```

- [ ] **Step 2: Run to verify test 1 passes already (create_app exists), test 16 fails**

```bash
python -m pytest tests/test_api_server.py::test_create_app_returns_fastapi tests/test_api_server.py::test_health_status_is_upper_snake_case -v
```

Expected: `test_create_app_returns_fastapi` PASS, `test_health_status_is_upper_snake_case` FAIL (current health returns `"ok"`)

- [ ] **Step 3: Create `src/vcse/api/models.py`**

```python
"""Operational response contract for VCSE API."""

from __future__ import annotations

from typing import Any

from vcse.api.config import API_VERSION


def _get_request_id(request) -> str:
    return getattr(getattr(request, "state", None), "request_id", "")


def make_ok_response(request, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "OK",
        "version": API_VERSION,
        "request_id": _get_request_id(request),
        "data": data,
        "errors": [],
    }


def make_error_response(
    request, code: str, message: str, path: str = ""
) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "version": API_VERSION,
        "request_id": _get_request_id(request),
        "data": {},
        "errors": [{"code": code, "message": message, "path": path, "details": {}}],
    }
```

- [ ] **Step 4: Extend `src/vcse/api/errors.py`**

Replace entire file:

```python
"""API error models."""

from __future__ import annotations

# --- Operational error codes ---
API_INVALID_REQUEST = "API_INVALID_REQUEST"
API_NOT_FOUND = "API_NOT_FOUND"
API_RUNTIME_INVALID = "API_RUNTIME_INVALID"
API_PROOF_INVALID = "API_PROOF_INVALID"
API_BUNDLE_INVALID = "API_BUNDLE_INVALID"
API_UNSUPPORTED_OPERATION = "API_UNSUPPORTED_OPERATION"
API_INTERNAL_ERROR = "API_INTERNAL_ERROR"


class APIError(ValueError):
    def __init__(
        self,
        error_type: str,
        message: str,
        code: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(f"{error_type}: {message}")
        self.error_type = error_type
        self.message = message
        self.code = code
        self.status_code = status_code


class OperationalError(Exception):
    """Raised by operational route handlers for structured error responses."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        path: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.path = path


def error_payload(error_type: str, message: str, code: str) -> dict[str, dict[str, str]]:
    return {
        "error": {
            "type": error_type,
            "message": message,
            "code": code,
        }
    }
```

- [ ] **Step 5: Run — test 1 should still pass (create_app unchanged so far)**

```bash
python -m pytest tests/test_api_server.py::test_create_app_returns_fastapi -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/vcse/api/models.py src/vcse/api/errors.py tests/test_api_server.py
git commit -m "feat: add API response contracts and error handling"
```

---

## Task 2: Middleware — echo X-Request-ID + handle OperationalError

**Files:**
- Modify: `src/vcse/api/middleware.py`

- [ ] **Step 1: Add test 6 to `tests/test_api_server.py`**

```python
# --- Test 6: request_id echoed from X-Request-ID header ---
def test_request_id_echoed_from_header() -> None:
    resp = _client().get("/health", headers={"X-Request-ID": "my-test-id-123"})
    assert resp.headers.get("X-Request-ID") == "my-test-id-123"
    payload = resp.json()
    assert payload["request_id"] == "my-test-id-123"
```

- [ ] **Step 2: Run to verify test 6 fails**

```bash
python -m pytest tests/test_api_server.py::test_request_id_echoed_from_header -v
```

Expected: FAIL (health endpoint not yet using new contract; middleware not echoing header)

- [ ] **Step 3: Update `src/vcse/api/middleware.py`**

Replace entire file:

```python
"""API middleware and exception handlers."""

from __future__ import annotations

import asyncio
import logging
import uuid
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vcse.api.config import API_VERSION
from vcse.api.errors import APIError, OperationalError, error_payload
from vcse.perf import stage


_LOG = logging.getLogger("vcse.api")


def install_error_handlers(app: FastAPI, *, max_request_bytes: int = 1_000_000, timeout_seconds: float = 30.0) -> None:
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
                        content=error_payload(
                            "REQUEST_TOO_LARGE",
                            "Request body exceeds configured limit",
                            "REQUEST_TOO_LARGE",
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
                content=error_payload("REQUEST_TIMEOUT", "Request timed out", "REQUEST_TIMEOUT"),
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
        request_id = getattr(getattr(request, "state", None), "request_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "ERROR",
                "version": API_VERSION,
                "request_id": request_id,
                "data": {},
                "errors": [{"code": exc.code, "message": exc.message, "path": exc.path, "details": {}}],
            },
        )

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.error_type, exc.message, exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_payload("INVALID_REQUEST", "Malformed request payload", "INVALID_REQUEST"),
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
            content=error_payload("INTERNAL_ERROR", "Internal server error", "INTERNAL_ERROR"),
        )
```

Note: test 6 will still fail until `/health` uses the new contract. That happens in Task 3.

- [ ] **Step 4: Verify existing API tests still pass**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all PASS (middleware change is backward compat for existing routes)

- [ ] **Step 5: Commit**

```bash
git add src/vcse/api/middleware.py
git commit -m "feat: add API response contracts and error handling"
```

---

## Task 3: Health Routes

**Files:**
- Create: `src/vcse/api/routes_health.py`
- Modify: `src/vcse/api/routes.py` (remove `/health`)
- Modify: `src/vcse/api/server.py` (register health router)
- Modify: `tests/test_api.py` (update `test_health` to new format)

- [ ] **Step 1: Add tests 2-5 and 16 completion to `tests/test_api_server.py`**

Append these tests:

```python
# --- Test 2: GET /health returns OK + HEALTHY ---
def test_health_returns_ok_healthy() -> None:
    resp = _client().get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["service"] == "vcse"
    assert payload["data"]["health"] == "HEALTHY"
    assert "version" in payload
    assert "request_id" in payload
    assert payload["errors"] == []


# --- Test 3: GET /version returns version 6.10.0 ---
def test_version_endpoint() -> None:
    resp = _client().get("/version")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["vcse_version"] == __version__
    assert payload["data"]["api_status"] == "READY"
    assert "python_version" in payload["data"]


# --- Test 4: GET /ready returns READY ---
def test_ready_endpoint() -> None:
    resp = _client().get("/ready")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["ready"] == "READY"


# --- Test 5: GET /live returns ALIVE ---
def test_live_endpoint() -> None:
    resp = _client().get("/live")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["alive"] == "ALIVE"


# --- Test 17: default server host documented as 127.0.0.1 ---
def test_default_host_is_loopback() -> None:
    from vcse.api.config import DEFAULT_HOST
    assert DEFAULT_HOST == "127.0.0.1"
```

- [ ] **Step 2: Run to verify tests 2-5, 16, 17 all fail**

```bash
python -m pytest tests/test_api_server.py::test_health_returns_ok_healthy tests/test_api_server.py::test_version_endpoint tests/test_api_server.py::test_ready_endpoint tests/test_api_server.py::test_live_endpoint tests/test_api_server.py::test_health_status_is_upper_snake_case tests/test_api_server.py::test_default_host_is_loopback -v
```

Expected: all FAIL except `test_default_host_is_loopback` (DEFAULT_HOST already 127.0.0.1)

- [ ] **Step 3: Create `src/vcse/api/routes_health.py`**

```python
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
```

- [ ] **Step 4: Remove `/health` from `src/vcse/api/routes.py`**

Delete lines 32–35 in `routes.py` (the `@router.get("/health")` handler). The final file should start with:

```python
"""API route handlers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Query, Request

from vcse.api.config import API_VERSION, MODEL_ID, MODEL_OWNER
from vcse.api.errors import APIError
from vcse.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ResponseMessage,
    ResponsesAPIResponse,
    ResponsesRequest,
    Usage,
)
from vcse.api.translator import translate_user_input
from vcse.perf import stage

router = APIRouter()


def _settings(request: Request):
    return getattr(request.app.state, "settings", None)


@router.get("/v1/models")
def models() -> list[dict[str, str]]:
    return [{"id": MODEL_ID, "object": "model", "owned_by": MODEL_OWNER}]


@router.post("/v1/chat/completions")
def chat_completions(
    http_request: Request,
    request: ChatCompletionRequest,
    debug: bool = Query(False),
) -> ChatCompletionResponse:
    if request.model != MODEL_ID:
        raise APIError("INVALID_REQUEST", f"Unknown model: {request.model}", "MODEL_NOT_FOUND", 400)
    prompt = _extract_last_user_message(request.messages)
    settings = _settings(http_request)
    with stage("api.chat_completion"):
        translated = translate_user_input(
            prompt,
            enable_debug=debug,
            search_backend=getattr(settings, "search_backend", "beam") if settings else "beam",
            enable_ts3=getattr(settings, "ts3_enabled", False) if settings else False,
            enable_index=getattr(settings, "indexing_enabled", False) if settings else False,
        )
    completion_id = _stable_id("chatcmpl", request.model, prompt, translated.content)
    return ChatCompletionResponse(
        id=completion_id,
        choices=[
            Choice(
                index=0,
                message=ResponseMessage(role="assistant", content=translated.content),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        vcse_debug=translated.debug if debug else None,
    )


@router.post("/v1/responses")
def responses(
    http_request: Request,
    request: ResponsesRequest,
    debug: bool = Query(False),
) -> ResponsesAPIResponse:
    if request.model != MODEL_ID:
        raise APIError("INVALID_REQUEST", f"Unknown model: {request.model}", "MODEL_NOT_FOUND", 400)
    prompt = _extract_prompt_from_responses_request(request)
    settings = _settings(http_request)
    with stage("api.responses"):
        translated = translate_user_input(
            prompt,
            enable_debug=debug,
            search_backend=getattr(settings, "search_backend", "beam") if settings else "beam",
            enable_ts3=getattr(settings, "ts3_enabled", False) if settings else False,
            enable_index=getattr(settings, "indexing_enabled", False) if settings else False,
        )
    response_id = _stable_id("resp", request.model, prompt, translated.content)
    return ResponsesAPIResponse(
        id=response_id,
        output_text=translated.content,
        usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        vcse_debug=translated.debug if debug else None,
    )


def _extract_last_user_message(messages: list[Any]) -> str:
    if not messages:
        raise APIError("INVALID_REQUEST", "messages must contain at least one user message", "INVALID_MESSAGES", 400)
    for item in reversed(messages):
        role = getattr(item, "role", None)
        if role == "user":
            content = getattr(item, "content", "")
            if isinstance(content, str):
                return content
            return json.dumps(content, sort_keys=True)
    raise APIError("INVALID_REQUEST", "No user message provided", "INVALID_MESSAGES", 400)


def _extract_prompt_from_responses_request(request: ResponsesRequest) -> str:
    if request.messages:
        return _extract_last_user_message(request.messages)
    if request.input is None:
        raise APIError("INVALID_REQUEST", "responses request requires input or messages", "INVALID_INPUT", 400)
    if isinstance(request.input, str):
        return request.input
    return json.dumps(request.input, sort_keys=True)


def _stable_id(prefix: str, model: str, prompt: str, content: str) -> str:
    digest = hashlib.sha1(f"{model}|{prompt}|{content}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
```

- [ ] **Step 5: Register health router in `src/vcse/api/server.py`**

```python
"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
```

- [ ] **Step 6: Update `tests/test_api.py::test_health`**

Replace `test_health` function in `tests/test_api.py`:

```python
def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'OK'
    assert payload['data']['service'] == 'vcse'
    assert payload['data']['health'] == 'HEALTHY'
    assert payload['version'] == __version__
```

- [ ] **Step 7: Run health route tests**

```bash
python -m pytest tests/test_api_server.py::test_health_returns_ok_healthy tests/test_api_server.py::test_version_endpoint tests/test_api_server.py::test_ready_endpoint tests/test_api_server.py::test_live_endpoint tests/test_api_server.py::test_health_status_is_upper_snake_case tests/test_api_server.py::test_request_id_echoed_from_header tests/test_api_server.py::test_default_host_is_loopback -v
```

Expected: all PASS

- [ ] **Step 8: Verify existing API tests pass with updated test_health**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add src/vcse/api/routes_health.py src/vcse/api/routes.py src/vcse/api/server.py tests/test_api_server.py tests/test_api.py
git commit -m "feat: add health runtime proof and pack API routes"
```

---

## Task 4: Runtime Validation Routes

**Files:**
- Create: `src/vcse/api/routes_runtime.py`
- Modify: `src/vcse/api/server.py`

- [ ] **Step 1: Add tests 7-10 to `tests/test_api_server.py`**

```python
# --- Helpers for runtime/proof fixtures ---
def _write_valid_csrf(path: Path) -> None:
    from vcse.runtime.model import CSRFIndex, CSRFRecord
    from vcse.runtime.serialize import save_csrf
    rec = CSRFRecord(
        claim_id="c1",
        subject="Paris",
        relation="capital_of",
        object="France",
        trust_tier=1,
        lifecycle_status="active",
        verification_status="VERIFIED",
        provenance_id="prov:c1",
    )
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    save_csrf(index, path)


def _write_valid_proof_index(path: Path) -> None:
    from vcse.proof.model import ProofIndex, ProofPath, ProofStep
    from vcse.proof.serialize import save_proof_index
    step = ProofStep(claim_id="c1", subject="Paris", relation="capital_of", object="France", trust_tier=1, verification_status="VERIFIED")
    proof = ProofPath(
        proof_id="proof:c1",
        result_claim_id="c1",
        path_length=1,
        trust_tier=1,
        verification_status="VERIFIED",
        supporting_claim_ids=("c1",),
        steps=(step,),
    )
    index = ProofIndex(
        proofs=(proof,),
        by_result={"c1": (0,)},
        by_support={"c1": (0,)},
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    save_proof_index(index, path)


# --- Test 7: missing runtime file returns structured API_NOT_FOUND ---
def test_runtime_validate_missing_file_returns_not_found() -> None:
    resp = _client().post("/runtime/validate", json={"csrf_path": "/tmp/nonexistent_vcse_test.csrf"})
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["status"] == "ERROR"
    assert any(e["code"] == "API_NOT_FOUND" for e in payload["errors"])


# --- Test 8: invalid runtime file returns structured error ---
def test_runtime_validate_invalid_file_returns_error() -> None:
    with tempfile.NamedTemporaryFile(suffix=".csrf", delete=False, mode="w") as f:
        f.write('{"records": "not_a_list"}')
        bad_path = f.name
    try:
        resp = _client().post("/runtime/validate", json={"csrf_path": bad_path})
        assert resp.status_code in (400, 422)
        payload = resp.json()
        assert payload["status"] == "ERROR"
        assert payload["errors"]
    finally:
        Path(bad_path).unlink(missing_ok=True)


# --- Test 9: valid runtime validate returns RUNTIME_VALID ---
def test_runtime_validate_valid_csrf_returns_runtime_valid() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "runtime.csrf"
        _write_valid_csrf(p)
        resp = _client().post("/runtime/validate", json={"csrf_path": str(p)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["validation_status"] == "RUNTIME_VALID"


# --- Test 10: invalid proof index returns structured error ---
def test_proof_validate_invalid_returns_error() -> None:
    with tempfile.NamedTemporaryFile(suffix=".proof.json", delete=False, mode="w") as f:
        f.write('{"proofs": "not_a_list"}')
        bad_path = f.name
    try:
        resp = _client().post("/proof/validate", json={"proof_path": bad_path})
        assert resp.status_code in (400, 422)
        payload = resp.json()
        assert payload["status"] == "ERROR"
        assert payload["errors"]
    finally:
        Path(bad_path).unlink(missing_ok=True)
```

- [ ] **Step 2: Run to verify tests 7-10 fail**

```bash
python -m pytest tests/test_api_server.py::test_runtime_validate_missing_file_returns_not_found tests/test_api_server.py::test_runtime_validate_invalid_file_returns_error tests/test_api_server.py::test_runtime_validate_valid_csrf_returns_runtime_valid tests/test_api_server.py::test_proof_validate_invalid_returns_error -v
```

Expected: all FAIL (routes don't exist yet)

- [ ] **Step 3: Create `src/vcse/api/routes_runtime.py`**

```python
"""Runtime and proof index validation routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from vcse.api.errors import (
    API_NOT_FOUND,
    API_PROOF_INVALID,
    API_RUNTIME_INVALID,
    OperationalError,
)
from vcse.api.models import make_ok_response
from vcse.proof.validate import validate_proof_index
from vcse.runtime.validate import validate_csrf_index

router = APIRouter()


class _RuntimeValidateRequest:
    pass


from pydantic import BaseModel


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
```

Note: `API_INVALID_REQUEST` is imported from `errors.py` — add it to the import.

Final import line in `routes_runtime.py`:
```python
from vcse.api.errors import (
    API_INVALID_REQUEST,
    API_NOT_FOUND,
    API_PROOF_INVALID,
    API_RUNTIME_INVALID,
    OperationalError,
)
```

- [ ] **Step 4: Register runtime router in `src/vcse/api/server.py`**

Add import and `app.include_router(runtime_router)`:

```python
"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.api.routes_runtime import router as runtime_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(runtime_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
```

- [ ] **Step 5: Run runtime tests**

```bash
python -m pytest tests/test_api_server.py::test_runtime_validate_missing_file_returns_not_found tests/test_api_server.py::test_runtime_validate_invalid_file_returns_error tests/test_api_server.py::test_runtime_validate_valid_csrf_returns_runtime_valid tests/test_api_server.py::test_proof_validate_invalid_returns_error -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/vcse/api/routes_runtime.py src/vcse/api/server.py tests/test_api_server.py
git commit -m "feat: add health runtime proof and pack API routes"
```

---

## Task 5: Pack/Bundle Verification Route

**Files:**
- Create: `src/vcse/api/routes_pack.py`
- Modify: `src/vcse/api/server.py`

- [ ] **Step 1: Add test 11 to `tests/test_api_server.py`**

```python
# --- Test 11: bundle verify endpoint returns structured bundle result ---
def test_bundle_verify_returns_structured_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # Bundle dir with no manifest — expect BUNDLE_ERROR response (not 500)
        resp = _client().post("/pack/verify-bundle", json={"bundle_path": tmp})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert "bundle_status" in payload["data"]
    # No manifest → BUNDLE_ERROR is a valid structured result, not an API crash
    assert payload["data"]["bundle_status"] in (
        "BUNDLE_VALID", "BUNDLE_INVALID", "BUNDLE_UNSIGNED",
        "BUNDLE_TAMPERED", "BUNDLE_ERROR",
    )
```

- [ ] **Step 2: Run to verify test 11 fails**

```bash
python -m pytest tests/test_api_server.py::test_bundle_verify_returns_structured_result -v
```

Expected: FAIL

- [ ] **Step 3: Create `src/vcse/api/routes_pack.py`**

```python
"""Pack bundle verification routes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vcse.api.errors import API_NOT_FOUND, API_BUNDLE_INVALID, OperationalError
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
```

- [ ] **Step 4: Register pack router in `src/vcse/api/server.py`**

```python
"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.api.routes_pack import router as pack_router
from vcse.api.routes_runtime import router as runtime_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(runtime_router)
    app.include_router(pack_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
```

- [ ] **Step 5: Run test 11**

```bash
python -m pytest tests/test_api_server.py::test_bundle_verify_returns_structured_result -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/vcse/api/routes_pack.py src/vcse/api/server.py tests/test_api_server.py
git commit -m "feat: add health runtime proof and pack API routes"
```

---

## Task 6: Query Route

**Files:**
- Create: `src/vcse/api/routes_query.py`
- Modify: `src/vcse/api/server.py`

- [ ] **Step 1: Add tests 12-13 to `tests/test_api_server.py`**

```python
# --- Test 12: query endpoint preserves semantics on valid .csrf ---
def test_query_endpoint_valid_csrf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "runtime.csrf"
        _write_valid_csrf(p)
        resp = _client().post("/query", json={
            "csrf_path": str(p),
            "subject": "Paris",
            "relation": None,
            "object": None,
            "trusted_only": False,
            "explain": False,
            "proof_index_path": None,
        })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["result_count"] >= 1
    assert payload["data"]["results"][0]["subject"] == "Paris"


# --- Test 13: query endpoint rejects invalid .csrf ---
def test_query_endpoint_invalid_csrf_returns_error() -> None:
    resp = _client().post("/query", json={
        "csrf_path": "/tmp/vcse_test_nonexistent_query.csrf",
        "subject": "Paris",
        "relation": None,
        "object": None,
        "trusted_only": False,
        "explain": False,
        "proof_index_path": None,
    })
    assert resp.status_code in (404, 422)
    payload = resp.json()
    assert payload["status"] == "ERROR"
    assert payload["errors"]
```

- [ ] **Step 2: Run to verify tests 12-13 fail**

```bash
python -m pytest tests/test_api_server.py::test_query_endpoint_valid_csrf tests/test_api_server.py::test_query_endpoint_invalid_csrf_returns_error -v
```

Expected: both FAIL

- [ ] **Step 3: Create `src/vcse/api/routes_query.py`**

```python
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
```

- [ ] **Step 4: Register query router in `src/vcse/api/server.py`**

```python
"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.api.routes_pack import router as pack_router
from vcse.api.routes_query import router as query_router
from vcse.api.routes_runtime import router as runtime_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(runtime_router)
    app.include_router(pack_router)
    app.include_router(query_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
```

- [ ] **Step 5: Run query tests**

```bash
python -m pytest tests/test_api_server.py::test_query_endpoint_valid_csrf tests/test_api_server.py::test_query_endpoint_invalid_csrf_returns_error -v
```

Expected: both PASS

- [ ] **Step 6: Commit**

```bash
git add src/vcse/api/routes_query.py src/vcse/api/server.py tests/test_api_server.py
git commit -m "feat: add query and reason API routes"
```

---

## Task 7: Reason Route (Unsupported Operation)

**Files:**
- Create: `src/vcse/api/routes_reason.py`
- Modify: `src/vcse/api/server.py`

- [ ] **Step 1: Add test 14 to `tests/test_api_server.py`**

```python
# --- Test 14: reason endpoint returns API_UNSUPPORTED_OPERATION ---
def test_reason_endpoint_returns_unsupported_or_valid() -> None:
    resp = _client().post("/reason", json={
        "csrf_path": "/tmp/any.csrf",
        "proof_index_path": None,
        "trusted_only": False,
        "explain": False,
    })
    payload = resp.json()
    # Either works correctly or returns API_UNSUPPORTED_OPERATION explicitly
    assert payload["status"] in ("OK", "ERROR")
    if payload["status"] == "ERROR":
        assert any(e["code"] == "API_UNSUPPORTED_OPERATION" for e in payload["errors"])
```

- [ ] **Step 2: Run to verify test 14 fails**

```bash
python -m pytest tests/test_api_server.py::test_reason_endpoint_returns_unsupported_or_valid -v
```

Expected: FAIL (route doesn't exist)

- [ ] **Step 3: Create `src/vcse/api/routes_reason.py`**

```python
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
```

- [ ] **Step 4: Register reason router in `src/vcse/api/server.py`**

```python
"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.api.routes_pack import router as pack_router
from vcse.api.routes_query import router as query_router
from vcse.api.routes_reason import router as reason_router
from vcse.api.routes_runtime import router as runtime_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(runtime_router)
    app.include_router(pack_router)
    app.include_router(query_router)
    app.include_router(reason_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
```

- [ ] **Step 5: Run test 14**

```bash
python -m pytest tests/test_api_server.py::test_reason_endpoint_returns_unsupported_or_valid -v
```

Expected: PASS

- [ ] **Step 6: Add test 15 (no raw traceback) to `tests/test_api_server.py`**

```python
# --- Test 15: no response leaks raw traceback ---
def test_no_raw_traceback_in_error_response() -> None:
    # Trigger an operational error (missing file) and verify no traceback in response
    resp = _client().post("/runtime/validate", json={"csrf_path": "/tmp/vcse_test_no_traceback.csrf"})
    payload = resp.json()
    payload_str = json.dumps(payload)
    assert "Traceback" not in payload_str
    assert "traceback" not in payload_str
    assert "File \"" not in payload_str
```

- [ ] **Step 7: Run test 15**

```bash
python -m pytest tests/test_api_server.py::test_no_raw_traceback_in_error_response -v
```

Expected: PASS (OperationalError handler formats structured JSON, no traceback)

- [ ] **Step 8: Run all new API server tests**

```bash
python -m pytest tests/test_api_server.py -v
```

Expected: all 17 tests PASS

- [ ] **Step 9: Commit**

```bash
git add src/vcse/api/routes_reason.py src/vcse/api/server.py tests/test_api_server.py
git commit -m "feat: add query and reason API routes"
```

---

## Task 8: Server CLI Verification

- [ ] **Step 1: Verify `vcse serve` default host is 127.0.0.1**

```bash
grep -n "DEFAULT_HOST\|127.0.0.1\|run_serve" src/vcse/api/config.py src/vcse/cli.py | head -10
```

Expected output includes `DEFAULT_HOST = "127.0.0.1"` and that `run_serve` uses it.

- [ ] **Step 2: Verify serve command structure**

```bash
python -m vcse serve --help 2>&1 | head -10
```

Expected: shows `--host` and `--port` options (no 0.0.0.0 default visible)

- [ ] **Step 3: Add tests/test_api_server.py note (no action needed — test 17 already passes)**

Test 17 (`test_default_host_is_loopback`) already asserts `DEFAULT_HOST == "127.0.0.1"`. Confirm it passes.

```bash
python -m pytest tests/test_api_server.py::test_default_host_is_loopback -v
```

Expected: PASS

---

## Task 9: Version Bump to 6.10.0

**Files:**
- Modify: `src/vcse/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `src/vcse/__init__.py`**

```python
"""Verifier-Centered Symbolic Engine."""

__all__ = ["__version__"]

__version__ = "6.10.0"
```

- [ ] **Step 2: Update `pyproject.toml`**

Find the `version = "6.9.0"` line and change it to `version = "6.10.0"`.

- [ ] **Step 3: Verify**

```bash
python -c "import vcse; print(vcse.__version__)"
```

Expected: `6.10.0`

- [ ] **Step 4: Run the new API test suite to confirm version is correct**

```bash
python -m pytest tests/test_api_server.py::test_version_endpoint -v
```

Expected: PASS (version endpoint returns `"6.10.0"`)

- [ ] **Step 5: Run targeted suites**

```bash
python -m pytest -q tests/test_runtime_hardening.py tests/test_distribution_bundles.py tests/test_csrf_runtime.py tests/test_proof_index.py
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/vcse/__init__.py pyproject.toml
git commit -m "chore: bump version to 6.10.0"
```

---

## Task 10: Full Test Validation

- [ ] **Step 1: Run full new test suite**

```bash
python -m pytest -q tests/test_api_server.py
```

Expected: 17 tests pass, 0 failures

- [ ] **Step 2: Run targeted existing suites**

```bash
python -m pytest -q tests/test_runtime_hardening.py tests/test_distribution_bundles.py tests/test_csrf_runtime.py tests/test_proof_index.py
```

Expected: all pass

- [ ] **Step 3: Run full suite**

```bash
python -m pytest -q
```

Expected: all pass, `false_verified_count = 0`

- [ ] **Step 4: Run gauntlet**

```bash
vcse gauntlet benchmarks/gauntlet/ --search mcts --ts3 --index
```

Expected: PASSED, `false_verified_count = 0`

---

## Task 11: Documentation Update

**Files:**
- Modify: `docs/API.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `README.md`

- [ ] **Step 1: Add operational API section to `docs/API.md`**

Append to `docs/API.md`:

```markdown
## API / Server Operational Interface (v6.10.0)

VCSE exposes a local-first operational HTTP interface alongside the OpenAI-compat adapter.

### Default binding

`vcse serve` binds to `127.0.0.1:8000` by default. It never binds to `0.0.0.0` unless explicitly overridden.

### Response contract

All operational endpoints use:
```json
{
  "status": "OK",
  "version": "6.10.0",
  "request_id": "...",
  "data": {},
  "errors": []
}
```
- `status`: `"OK"` or `"ERROR"`
- `errors[].code`: UPPER_SNAKE_CASE (e.g. `API_NOT_FOUND`)
- No raw tracebacks in responses

### Health / Readiness / Liveness

- `GET /health` → `{"health": "HEALTHY"}`
- `GET /version` → vcse_version, python_version, api_status
- `GET /ready` → `{"ready": "READY"}`
- `GET /live` → `{"alive": "ALIVE"}`

### Runtime/Proof Validation

- `POST /runtime/validate` — validates a `.csrf` file by path
- `POST /proof/validate` — validates a `.proof.json` file by path

Neither endpoint mutates files or auto-trusts validated artifacts.

### Bundle Verification

- `POST /pack/verify-bundle` — verifies a `.vcsepack` bundle directory

Signature validity is not truth. A `BUNDLE_VALID` result means the bundle is structurally sound and signatures match. It does not mean claims are certified.

### Query Interface

- `POST /query` — deterministic structured query over a validated `.csrf` runtime

Query semantics are identical to `vcse query --csrf`. No claims are created or mutated.

### Reason Interface

- `POST /reason` — currently returns `API_UNSUPPORTED_OPERATION` (deferred to v6.11)

Use `vcse reason` CLI command for reasoning operations.

### Invariants

The API never:
- auto-certifies or auto-trusts any data
- bypasses verifier or trust promotion logic
- exposes private keys
- performs remote key lookup
- introduces probabilistic or LLM-based logic
```

- [ ] **Step 2: Add milestone entry to `docs/ROADMAP.md`**

Add to the roadmap:
```markdown
- v6.10: API/server hardening — operational endpoints (health/readiness, validation, bundle verify, query), unified response contract, X-Request-ID support
```

- [ ] **Step 3: Add brief note to `docs/ARCHITECTURE.md`**

Add under the current milestone state:
```
- v6.10: operational HTTP API surface (health, validation, query endpoints, unified response contract)
```

- [ ] **Step 4: Add to README.md if it has an API or server section**

```bash
grep -n "serve\|API\|api" README.md | head -10
```

Add a brief note about `vcse serve` binding to `127.0.0.1` and the new operational endpoints.

- [ ] **Step 5: Commit**

```bash
git add docs/API.md docs/ARCHITECTURE.md docs/ROADMAP.md README.md
git commit -m "docs: document API operational interface"
```

---

## Task 12: Final Validation and Git Cleanup

- [ ] **Step 1: Clean up generated test artifacts**

```bash
git restore tests/**/pack.json 2>/dev/null || true
rm -rf .vcse
rm -rf examples/packs/*_candidate_*
rm -rf examples/packs/compiled_*
rm -f benchmarks/compiled_*.jsonl
find . -name "*.csrf" -not -path "./tests/fixtures/*" -delete
find . -name "*.proof.json" -not -path "./tests/fixtures/*" -delete
find . -name "*.vcsepack" -not -path "./tests/fixtures/*" -exec rm -rf {} +
find . -name "api_test_*.json" -not -path "./tests/fixtures/*" -delete
```

- [ ] **Step 2: Check git status**

```bash
git status --short
```

Expected: clean (or only docs/plan files)

- [ ] **Step 3: Final full suite run**

```bash
python -m pytest -q tests/test_api_server.py
python -m pytest -q tests/test_runtime_hardening.py tests/test_distribution_bundles.py tests/test_csrf_runtime.py tests/test_proof_index.py
python -m pytest -q
vcse gauntlet benchmarks/gauntlet/ --search mcts --ts3 --index
python -c "import vcse; print(vcse.__version__)"
```

Expected:
- `test_api_server.py`: 17 tests pass
- Targeted suites: all pass
- Full suite: all pass
- Gauntlet: PASSED, `false_verified_count = 0`
- Version: `6.10.0`

---

## Self-Review Checklist

**Spec coverage:**
- [x] API app factory (`create_app`) — Task 3 (server.py)
- [x] Standard response contract (`models.py`) — Task 1
- [x] Request ID echo (`middleware.py`) — Task 2
- [x] Error codes + `OperationalError` — Task 1
- [x] `GET /health`, `/version`, `/ready`, `/live` — Task 3
- [x] `POST /runtime/validate`, `/proof/validate` — Task 4
- [x] `POST /pack/verify-bundle` — Task 5
- [x] `POST /query` — Task 6
- [x] `POST /reason` (unsupported) — Task 7
- [x] CLI default host `127.0.0.1` — confirmed in config.py, Task 8
- [x] All 17 required tests — Tasks 1-7
- [x] Version 6.10.0 — Task 9
- [x] Targeted suites pass — Task 10
- [x] Docs — Task 11
- [x] Git cleanup — Task 12
- [x] Non-negotiable rules: no verifier/trust/proof mutation, no auto-cert, no LLM, no remote keys

**Type consistency check:**
- `make_ok_response(request, data)` used consistently in routes_health, routes_runtime, routes_pack, routes_query
- `OperationalError(code, message, status_code, path)` consistent across all route modules
- `validate_csrf_index` returns `RuntimeValidationResult` with `.status`, `.issue_count`, `.issues` (tuple of `RuntimeValidationIssue`)
- `validate_proof_index` returns same `RuntimeValidationResult` type — confirmed (imports from `vcse.runtime.validate`)
- `verify_pack_bundle` returns `BundleVerificationResult` with `.status`, `.bundle_id`, `.pack_id`, `.file_count`, `.signature_status`, `.integrity_status`, `.issues`
- `StructuredQueryEngine().query_csrf(runtime, query)` returns `StructuredQueryResult` with `.status`, `.result_count`, `.results`, `.packs_searched`, `.packs_skipped`, `.rows_examined`, `.filters_applied`

**Deferred work:**
- `/reason` full implementation — v6.11
- Authentication layer — out of scope
- Remote key lookup — explicitly excluded
- External network binding (non-loopback) — excluded by default
