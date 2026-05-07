"""Deterministic serialization for renderer guard models."""

from __future__ import annotations

import json
import math
from typing import Any

from vcse.render.model import RendererGuardDecision


def renderer_guard_decision_to_dict(decision: RendererGuardDecision) -> dict[str, Any]:
    d = {
        "accepted_claim_ids": list(decision.accepted_claim_ids),
        "answer_id": decision.answer_id,
        "claim_count": decision.claim_count,
        "final_status": decision.final_status,
        "issues": list(decision.issues),
        "reason_code": decision.reason_code,
        "rejected_claim_ids": list(decision.rejected_claim_ids),
        "render_mode": decision.render_mode,
        "valid": decision.valid,
    }
    _assert_json_safe(d)
    return d


def renderer_guard_decision_to_json(decision: RendererGuardDecision) -> str:
    return json.dumps(
        renderer_guard_decision_to_dict(decision),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("NON_FINITE_VALUE: NaN/Inf not allowed in renderer guard output")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("JSON object keys must be strings")
            _assert_json_safe(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
