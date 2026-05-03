"""Deterministic canonicalization for signing targets."""

from __future__ import annotations

import json
import math
from typing import Any


def canonical_json(data: Any) -> str:
    """Deterministic JSON with sorted keys, no spaces. Rejects NaN/Inf."""
    _reject_non_finite(data)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(data: Any) -> bytes:
    """UTF-8 encoded canonical JSON."""
    return canonical_json(data).encode("utf-8")


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError(f"non-finite float not allowed in canonical JSON: {value}")
    if isinstance(value, dict):
        for v in value.values():
            _reject_non_finite(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _reject_non_finite(v)
