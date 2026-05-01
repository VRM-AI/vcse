"""Policy file loader and validator."""

from __future__ import annotations

import json
from pathlib import Path

from vcse.policy.model import PolicyRule, PolicySet


class PolicyLoadError(ValueError):
    """Raised when policy payload is invalid."""


def load_policy(path: Path) -> PolicySet:
    if not path.exists():
        raise PolicyLoadError(f"policy file not found: {path}")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"invalid policy json: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PolicyLoadError("policy root must be an object")

    policy_id = str(payload.get("policy_id", "")).strip()
    description = str(payload.get("description", "")).strip()
    default_effect = str(payload.get("default_effect", "")).strip()
    rules_payload = payload.get("rules")

    if not policy_id:
        raise PolicyLoadError("missing required field: policy_id")
    if not description:
        raise PolicyLoadError("missing required field: description")
    if default_effect not in {"allow", "block"}:
        raise PolicyLoadError("default_effect must be 'allow' or 'block'")
    if not isinstance(rules_payload, list):
        raise PolicyLoadError("rules must be a list")

    rules: list[PolicyRule] = []
    for idx, item in enumerate(rules_payload, start=1):
        if not isinstance(item, dict):
            raise PolicyLoadError(f"rule #{idx} must be an object")
        rule_id = str(item.get("rule_id", "")).strip()
        effect = str(item.get("effect", "")).strip()
        target_type = str(item.get("target_type", "")).strip()
        target = str(item.get("target", "")).strip()
        reason = str(item.get("reason", "")).strip()

        if not rule_id:
            raise PolicyLoadError(f"rule #{idx}: missing rule_id")
        if effect not in {"allow", "block"}:
            raise PolicyLoadError(f"rule #{idx} ({rule_id}): effect must be 'allow' or 'block'")
        if target_type not in {"relation", "pack", "domain", "inference_rule"}:
            raise PolicyLoadError(
                f"rule #{idx} ({rule_id}): target_type must be relation|pack|domain|inference_rule"
            )
        if not target:
            raise PolicyLoadError(f"rule #{idx} ({rule_id}): missing target")
        if not reason:
            raise PolicyLoadError(f"rule #{idx} ({rule_id}): missing reason")

        rules.append(
            PolicyRule(
                rule_id=rule_id,
                effect=effect,
                target_type=target_type,
                target=target,
                reason=reason,
            )
        )

    ordered = tuple(
        sorted(
            rules,
            key=lambda item: (
                item.target_type,
                item.target,
                0 if item.effect == "block" else 1,
                item.rule_id,
            ),
        )
    )
    return PolicySet(policy_id=policy_id, description=description, default_effect=default_effect, rules=ordered)
