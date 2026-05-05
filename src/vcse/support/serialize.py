"""Serialization helpers for source support models."""

from __future__ import annotations

import json
import math
from typing import Any

from vcse.support.model import SourceSupportDecision


def source_support_decision_to_dict(decision: SourceSupportDecision) -> dict[str, Any]:
    d = {
        "claim_id": decision.claim_id,
        "final_status": decision.final_status,
        "issues": list(decision.issues),
        "reason_code": decision.reason_code,
        "relation_id": decision.relation_id,
        "source_span_ids": list(decision.source_span_ids),
        "support_profile_id": decision.support_profile_id,
        "supported": decision.supported,
    }
    _assert_json_safe(d)
    return d


def source_support_decision_to_json(decision: SourceSupportDecision) -> str:
    return json.dumps(
        source_support_decision_to_dict(decision),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("NON_FINITE_VALUE: NaN/Inf is not allowed in source support output")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("JSON object keys must be strings")
            _assert_json_safe(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
