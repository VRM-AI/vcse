"""CMCF deterministic serialization helpers."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from typing import Any

from vcse.cmcf.model import (
    CMCFClaim,
    CMCFIntegrity,
    CMCFMetadata,
    CMCFProvenance,
    CMCFRecord,
    CMCFStatus,
    CMCFTrust,
)


def record_to_dict(record: CMCFRecord) -> dict[str, Any]:
    payload = asdict(record)
    _assert_json_safe(payload)
    return payload


def record_from_dict(data: dict[str, Any]) -> CMCFRecord:
    if not isinstance(data, dict):
        raise ValueError("CMCF record must be an object")
    try:
        claim = CMCFClaim(**data["claim"])
        provenance = CMCFProvenance(**data["provenance"])
        status = CMCFStatus(**data["status"])
        trust = CMCFTrust(**data["trust"])
        integrity = CMCFIntegrity(**data["integrity"])
        metadata = CMCFMetadata(**data["metadata"])
        record = CMCFRecord(
            cmcf_version=str(data["cmcf_version"]),
            claim=claim,
            provenance=provenance,
            status=status,
            trust=trust,
            integrity=integrity,
            metadata=metadata,
        )
    except KeyError as exc:
        raise ValueError(f"missing field: {exc.args[0]}") from exc
    except TypeError as exc:
        raise ValueError(f"invalid record field shape: {exc}") from exc
    _assert_json_safe(record_to_dict(record))
    return record


def record_to_json(record: CMCFRecord) -> str:
    payload = record_to_dict(record)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def record_from_json(text: str) -> CMCFRecord:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("CMCF JSON root must be an object")
    return record_from_dict(payload)


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN/Inf is not allowed in CMCF record")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("CMCF object keys must be strings")
            _assert_json_safe(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
        return
