"""CSRF serialization helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from vcse.runtime.model import CSRFIndex, CSRFRecord


def save_csrf(index: CSRFIndex, path: Path) -> None:
    payload = _index_to_payload(index)
    _assert_json_safe(payload)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def load_csrf(path: Path) -> CSRFIndex:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("CSRF_INVALID_ROOT")
    _assert_json_safe(payload)

    records_raw = payload.get("records", [])
    if not isinstance(records_raw, list):
        raise ValueError("CSRF_INVALID_RECORDS")
    records = tuple(CSRFRecord(**item) for item in records_raw)

    return CSRFIndex(
        records=records,
        by_subject=_load_index_map(payload.get("by_subject", {})),
        by_relation=_load_index_map(payload.get("by_relation", {})),
        by_object=_load_index_map(payload.get("by_object", {})),
    )


def _index_to_payload(index: CSRFIndex) -> dict[str, Any]:
    return {
        "records": [
            {
                "claim_id": record.claim_id,
                "subject": record.subject,
                "relation": record.relation,
                "object": record.object,
                "trust_tier": record.trust_tier,
                "lifecycle_status": record.lifecycle_status,
                "verification_status": record.verification_status,
                "provenance_id": record.provenance_id,
            }
            for record in index.records
        ],
        "by_subject": {key: list(value) for key, value in sorted(index.by_subject.items())},
        "by_relation": {key: list(value) for key, value in sorted(index.by_relation.items())},
        "by_object": {key: list(value) for key, value in sorted(index.by_object.items())},
    }


def _load_index_map(raw: Any) -> dict[str, tuple[int, ...]]:
    if not isinstance(raw, dict):
        raise ValueError("CSRF_INVALID_INDEX")
    parsed: dict[str, tuple[int, ...]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, list):
            raise ValueError("CSRF_INVALID_INDEX_ENTRY")
        parsed[key] = tuple(int(item) for item in value)
    return parsed


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN/Inf is not allowed in CSRF record")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("CSRF object keys must be strings")
            _assert_json_safe(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
        return
