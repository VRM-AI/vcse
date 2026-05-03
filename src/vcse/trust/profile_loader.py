from __future__ import annotations

import json
from pathlib import Path

from vcse.trust.profile import (
    TRUST_ACTIONS,
    SelfCertificationPolicy,
    TrustMatch,
    TrustProfile,
    TrustRule,
)


def load_trust_profile(path: Path) -> TrustProfile:
    if path.suffix.lower() != ".json":
        raise ValueError("TRUST_PROFILE_INVALID_FORMAT: only JSON profiles are supported in v6.2")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("TRUST_PROFILE_INVALID_ROOT: profile root must be object")

    for field in ("trust_profile_id", "description", "default_action", "self_certification", "rules"):
        if field not in payload:
            raise ValueError(f"TRUST_PROFILE_MISSING_FIELD: {field}")

    default_action = str(payload["default_action"])
    _validate_action(default_action, where="default_action")

    self_cert_payload = payload["self_certification"]
    if not isinstance(self_cert_payload, dict):
        raise ValueError("TRUST_PROFILE_INVALID_SELF_CERTIFICATION: expected object")

    self_cert = SelfCertificationPolicy(
        allowed=bool(self_cert_payload.get("allowed", False)),
        max_trust_tier=int(self_cert_payload.get("max_trust_tier", 0)),
        requires_signature=bool(self_cert_payload.get("requires_signature", False)),
        requires_stable_source_hash=bool(self_cert_payload.get("requires_stable_source_hash", False)),
        requires_provenance=bool(self_cert_payload.get("requires_provenance", False)),
        requires_no_conflicts=bool(self_cert_payload.get("requires_no_conflicts", False)),
        requires_policy_allowed=bool(self_cert_payload.get("requires_policy_allowed", False)),
        requires_verification_status=(
            None
            if self_cert_payload.get("requires_verification_status") is None
            else str(self_cert_payload["requires_verification_status"])
        ),
    )
    if self_cert.max_trust_tier < 0:
        raise ValueError("TRUST_PROFILE_INVALID_SELF_CERTIFICATION: max_trust_tier must be >= 0")

    rules_payload = payload["rules"]
    if not isinstance(rules_payload, list):
        raise ValueError("TRUST_PROFILE_INVALID_RULES: rules must be list")

    seen_rule_ids: set[str] = set()
    rules: list[TrustRule] = []
    for idx, item in enumerate(rules_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"TRUST_PROFILE_INVALID_RULE: rules[{idx}] must be object")
        if "rule_id" not in item:
            raise ValueError(f"TRUST_PROFILE_MISSING_RULE_ID: rules[{idx}]")
        if "action" not in item:
            raise ValueError(f"TRUST_PROFILE_MISSING_RULE_ACTION: rules[{idx}]")
        if "match" not in item:
            raise ValueError(f"TRUST_PROFILE_MISSING_RULE_MATCH: rules[{idx}]")

        rule_id = str(item["rule_id"])
        if rule_id in seen_rule_ids:
            raise ValueError(f"TRUST_PROFILE_DUPLICATE_RULE_ID: {rule_id}")
        seen_rule_ids.add(rule_id)

        action = str(item["action"])
        _validate_action(action, where=f"rule:{rule_id}")

        match_payload = item["match"]
        if not isinstance(match_payload, dict):
            raise ValueError(f"TRUST_PROFILE_INVALID_RULE_MATCH: {rule_id}")

        allowed_match_fields = {
            "source_uri_prefix",
            "source_type",
            "domain",
            "relation",
            "subject",
            "field",
            "lifecycle_status",
            "verification_status",
            "provenance_status",
            "certification_status",
            "policy_status",
        }
        unknown_fields = sorted(set(match_payload.keys()) - allowed_match_fields)
        if unknown_fields:
            raise ValueError(f"TRUST_PROFILE_UNKNOWN_MATCH_FIELDS: {rule_id}: {','.join(unknown_fields)}")

        trust_tier_value = item.get("trust_tier")
        trust_tier = None if trust_tier_value is None else int(trust_tier_value)
        if trust_tier is not None and trust_tier < 0:
            raise ValueError(f"TRUST_PROFILE_INVALID_TRUST_TIER: {rule_id}")

        rules.append(
            TrustRule(
                rule_id=rule_id,
                action=action,
                match=TrustMatch(**{k: (None if v is None else str(v)) for k, v in match_payload.items()}),
                trust_tier=trust_tier,
                reason=str(item.get("reason", "")),
            )
        )

    return TrustProfile(
        trust_profile_id=str(payload["trust_profile_id"]),
        description=str(payload["description"]),
        default_action=default_action,
        self_certification=self_cert,
        rules=tuple(sorted(rules, key=lambda item: item.rule_id)),
    )


def _validate_action(action: str, where: str) -> None:
    if action not in TRUST_ACTIONS:
        raise ValueError(f"TRUST_PROFILE_UNKNOWN_ACTION: {where}:{action}")
