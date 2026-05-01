"""Deterministic policy enforcement."""

from __future__ import annotations

from typing import Any

from vcse.policy.model import PolicyDecision, PolicySet


class PolicyEnforcer:
    def evaluate_relation(self, relation: str, policy: PolicySet) -> PolicyDecision:
        return self._evaluate("relation", relation, policy)

    def evaluate_pack(self, pack_id: str, policy: PolicySet) -> PolicyDecision:
        return self._evaluate("pack", pack_id, policy)

    def evaluate_domain(self, domain: str, policy: PolicySet) -> PolicyDecision:
        return self._evaluate("domain", domain, policy)

    def evaluate_inference_rule(self, rule_id: str, policy: PolicySet) -> PolicyDecision:
        return self._evaluate("inference_rule", rule_id, policy)

    def evaluate_claim(self, claim: Any, policy: PolicySet) -> PolicyDecision:
        if isinstance(claim, dict):
            relation = str(claim.get("relation", "")).strip()
        else:
            relation = str(getattr(claim, "relation", "")).strip()
        return self.evaluate_relation(relation, policy)

    def _evaluate(self, target_type: str, target: str, policy: PolicySet) -> PolicyDecision:
        clean_target = str(target).strip()
        matches = [
            rule
            for rule in policy.rules
            if rule.target_type == target_type and rule.target == clean_target
        ]
        blocked = next((rule for rule in matches if rule.effect == "block"), None)
        if blocked is not None:
            return PolicyDecision(
                status="BLOCKED",
                policy_id=policy.policy_id,
                target_type=target_type,
                target=clean_target,
                matched_rule_id=blocked.rule_id,
                reason=blocked.reason,
            )

        allowed = next((rule for rule in matches if rule.effect == "allow"), None)
        if allowed is not None:
            return PolicyDecision(
                status="ALLOWED",
                policy_id=policy.policy_id,
                target_type=target_type,
                target=clean_target,
                matched_rule_id=allowed.rule_id,
                reason=allowed.reason,
            )

        if policy.default_effect == "block":
            return PolicyDecision(
                status="BLOCKED",
                policy_id=policy.policy_id,
                target_type=target_type,
                target=clean_target,
                matched_rule_id=None,
                reason="blocked by policy default_effect=block",
            )
        return PolicyDecision(
            status="ALLOWED",
            policy_id=policy.policy_id,
            target_type=target_type,
            target=clean_target,
            matched_rule_id=None,
            reason="allowed by policy default_effect=allow",
        )
