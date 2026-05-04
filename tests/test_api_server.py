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
