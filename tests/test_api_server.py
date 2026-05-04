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
