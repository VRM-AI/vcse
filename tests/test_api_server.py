"""Tests for VCSE v6.10.0 operational API server."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from vcse.api.errors import APIError
from vcse.api.server import create_app
from vcse import __version__


def _client() -> TestClient:
    return TestClient(create_app())


# --- Test 1: create_app returns FastAPI app ---
def test_create_app_returns_fastapi() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


# --- Test 6: request_id echoed from X-Request-ID header ---
def test_request_id_echoed_from_header() -> None:
    resp = _client().get("/health", headers={"X-Request-ID": "my-test-id-123"})
    assert resp.headers.get("X-Request-ID") == "my-test-id-123"
    payload = resp.json()
    assert payload["request_id"] == "my-test-id-123"


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


# --- Test 3: GET /version returns version ---
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


# --- Test 16: all machine statuses are UPPER_SNAKE_CASE ---
def test_health_status_is_upper_snake_case() -> None:
    resp = _client().get("/health")
    payload = resp.json()
    assert payload["status"] == payload["status"].upper()
    assert payload["data"]["health"] == payload["data"]["health"].upper()


# --- Test 17: default server host is 127.0.0.1 ---
def test_default_host_is_loopback() -> None:
    from vcse.api.config import DEFAULT_HOST
    assert DEFAULT_HOST == "127.0.0.1"


# --- Fixture helpers ---
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


# --- Test 7: missing runtime file returns structured API_NOT_FOUND ---
def test_runtime_validate_missing_file_returns_not_found() -> None:
    resp = _client().post("/runtime/validate", json={"csrf_path": "/tmp/nonexistent_vcse_test_12345.csrf"})
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


# --- Test 11: bundle verify endpoint returns structured bundle result ---
def test_bundle_verify_returns_structured_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # No manifest.json → expect BUNDLE_ERROR (not a server crash)
        resp = _client().post("/pack/verify-bundle", json={"bundle_path": tmp})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert "bundle_status" in payload["data"]
    assert payload["data"]["bundle_status"] in (
        "BUNDLE_VALID", "BUNDLE_INVALID", "BUNDLE_UNSIGNED",
        "BUNDLE_TAMPERED", "BUNDLE_ERROR",
    )


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


# --- Test 13: query endpoint rejects invalid .csrf path ---
def test_query_endpoint_invalid_csrf_returns_error() -> None:
    resp = _client().post("/query", json={
        "csrf_path": "/tmp/vcse_test_nonexistent_query_99999.csrf",
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


# --- Test 14: reason endpoint returns API_UNSUPPORTED_OPERATION ---
def test_reason_endpoint_returns_unsupported_or_valid() -> None:
    resp = _client().post("/reason", json={
        "csrf_path": "/tmp/any.csrf",
        "proof_index_path": None,
        "trusted_only": False,
        "explain": False,
    })
    payload = resp.json()
    assert payload["status"] in ("OK", "ERROR")
    if payload["status"] == "ERROR":
        assert any(e["code"] == "API_UNSUPPORTED_OPERATION" for e in payload["errors"])


# --- Test 15: no response leaks raw traceback ---
def test_no_raw_traceback_in_error_response() -> None:
    resp = _client().post("/runtime/validate", json={"csrf_path": "/tmp/vcse_test_error_99999.csrf"})
    payload = resp.json()
    payload_str = json.dumps(payload)
    assert "Traceback" not in payload_str
    assert "traceback" not in payload_str
    assert 'File "' not in payload_str


def _error_contract_client() -> TestClient:
    app = create_app()
    router = APIRouter()

    @router.get("/_test/api-error")
    def _raise_api_error() -> dict:
        raise APIError("INVALID_REQUEST", "synthetic api error", "API_INVALID_REQUEST", 400)

    @router.get("/_test/internal-error")
    def _raise_internal_error() -> dict:
        raise RuntimeError("synthetic internal error")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _assert_unified_error_contract(payload: dict) -> None:
    assert payload["status"] == "ERROR"
    assert payload["version"] == __version__
    assert "request_id" in payload
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    assert payload["data"] == {}
    assert isinstance(payload["errors"], list)
    assert payload["errors"]
    assert "error" not in payload


def test_request_validation_error_uses_unified_contract() -> None:
    resp = _client().post("/runtime/validate", json={})
    assert resp.status_code == 400
    payload = resp.json()
    _assert_unified_error_contract(payload)
    assert payload["errors"][0]["code"] == "API_INVALID_REQUEST"


def test_malformed_runtime_request_uses_unified_contract() -> None:
    resp = _client().post(
        "/runtime/validate",
        content='{"csrf_path":',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    _assert_unified_error_contract(payload)
    assert payload["errors"][0]["code"] == "API_INVALID_REQUEST"


def test_api_error_handler_uses_unified_contract() -> None:
    client = _error_contract_client()
    resp = client.get("/_test/api-error")
    assert resp.status_code == 400
    payload = resp.json()
    _assert_unified_error_contract(payload)
    assert payload["errors"][0]["code"] == "API_INVALID_REQUEST"


def test_internal_error_handler_uses_api_internal_error_contract() -> None:
    client = _error_contract_client()
    req_id = "err-req-001"
    resp = client.get("/_test/internal-error", headers={"X-Request-ID": req_id})
    assert resp.status_code == 500
    assert resp.headers.get("X-Request-ID") == req_id
    payload = resp.json()
    _assert_unified_error_contract(payload)
    assert payload["request_id"] == req_id
    assert payload["errors"][0]["code"] == "API_INTERNAL_ERROR"
    assert payload["errors"][0]["message"] == "Internal server error"
    payload_text = json.dumps(payload)
    assert "Traceback" not in payload_text
    assert "traceback" not in payload_text
    assert "synthetic internal error" not in payload_text
