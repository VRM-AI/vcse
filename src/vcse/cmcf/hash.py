"""Deterministic CMCF hashing helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def compute_claim_id(subject: str, relation: str, object: str, provenance_id: str | None = None) -> str:
    payload = {
        "subject": subject,
        "relation": relation,
        "object": object,
        "provenance_id": provenance_id or "",
    }
    return sha256_text(canonical_json(payload))


def compute_provenance_id(
    source_type: str,
    source_uri: str | None,
    locator: str | None,
    raw_value: str | None,
) -> str:
    payload = {
        "source_type": source_type,
        "source_uri": source_uri or "",
        "locator": locator or "",
        "raw_value": raw_value or "",
    }
    return sha256_text(canonical_json(payload))


def compute_content_hash(record_without_integrity: dict[str, Any]) -> str:
    return sha256_text(canonical_json(record_without_integrity))
