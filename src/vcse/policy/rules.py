"""Policy execution rule models and condition evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionRule:
    rule_id: str
    condition_field: str
    condition_op: str   # eq | ne | lt | gt | lte | gte | in | not_in
    condition_value: Any
    action: str
    action_params: dict[str, Any]
    priority: int       # lower value fires first


@dataclass(frozen=True)
class ExecutionProfile:
    profile_id: str
    description: str
    rules: tuple[ExecutionRule, ...]


_TIER_ORDER = [
    "T0_CANDIDATE",
    "T1_PROVENANCED",
    "T2_SOURCE_TRUSTED",
    "T3_CROSS_SUPPORTED",
    "T4_VERIFIER_CONSISTENT",
    "T5_CERTIFIED",
    "T6_DEPRECATED",
    "T7_CONFLICTED",
]


def _tier_index(tier: str) -> int:
    try:
        return _TIER_ORDER.index(tier)
    except ValueError:
        return -1


def evaluate_condition(field_value: Any, op: str, condition_value: Any) -> bool:
    if op == "eq":
        return field_value == condition_value
    if op == "ne":
        return field_value != condition_value
    if op == "in":
        return field_value in condition_value
    if op == "not_in":
        return field_value not in condition_value
    try:
        fv = float(field_value) if not isinstance(field_value, (int, float)) else field_value
        cv = float(condition_value) if not isinstance(condition_value, (int, float)) else condition_value
    except (TypeError, ValueError):
        return False
    if op == "lt":
        return fv < cv
    if op == "gt":
        return fv > cv
    if op == "lte":
        return fv <= cv
    if op == "gte":
        return fv >= cv
    return False


def get_decision_field(decision: Any, field: str) -> Any:
    return getattr(decision, field, None)


class ExecutionProfileLoadError(ValueError):
    """Raised when an execution profile JSON is invalid."""


def load_execution_profile(path: Any) -> ExecutionProfile:
    import json
    from pathlib import Path as _Path

    p = _Path(path)
    if not p.exists():
        raise ExecutionProfileLoadError(f"profile file not found: {p}")
    try:
        payload = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise ExecutionProfileLoadError(f"invalid profile json: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ExecutionProfileLoadError("profile root must be an object")

    profile_id = str(payload.get("profile_id", "")).strip()
    description = str(payload.get("description", "")).strip()
    rules_payload = payload.get("rules")

    if not profile_id:
        raise ExecutionProfileLoadError("missing required field: profile_id")
    if not isinstance(rules_payload, list):
        raise ExecutionProfileLoadError("rules must be a list")

    rules: list[ExecutionRule] = []
    for idx, item in enumerate(rules_payload, start=1):
        if not isinstance(item, dict):
            raise ExecutionProfileLoadError(f"rule #{idx} must be an object")
        rule_id = str(item.get("rule_id", "")).strip()
        condition_field = str(item.get("condition_field", "")).strip()
        condition_op = str(item.get("condition_op", "eq")).strip()
        condition_value = item.get("condition_value")
        action = str(item.get("action", "")).strip()
        action_params = item.get("action_params") or {}
        priority = int(item.get("priority", 10))

        if not rule_id:
            raise ExecutionProfileLoadError(f"rule #{idx}: missing rule_id")
        if not condition_field:
            raise ExecutionProfileLoadError(f"rule #{idx} ({rule_id}): missing condition_field")
        if not action:
            raise ExecutionProfileLoadError(f"rule #{idx} ({rule_id}): missing action")
        if not isinstance(action_params, dict):
            action_params = {}

        rules.append(ExecutionRule(
            rule_id=rule_id,
            condition_field=condition_field,
            condition_op=condition_op,
            condition_value=condition_value,
            action=action,
            action_params=action_params,
            priority=priority,
        ))

    sorted_rules = tuple(sorted(rules, key=lambda r: (r.priority, r.rule_id)))
    return ExecutionProfile(
        profile_id=profile_id,
        description=description,
        rules=sorted_rules,
    )
