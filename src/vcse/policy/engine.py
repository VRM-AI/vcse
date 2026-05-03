"""Policy Execution Engine — post-trust-promotion rule evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from vcse.policy.actions import ALLOWED_ACTIONS
from vcse.policy.rules import ExecutionProfile, ExecutionRule, evaluate_condition, get_decision_field

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


@dataclass
class PolicyExecutionResult:
    applied_rules: list[str]
    actions_taken: list[str]
    final_tier: str
    annotations: list[str]
    requires_review: bool
    blocked: bool


class PolicyExecutionEngine:
    def execute(self, decision: object, profile: ExecutionProfile) -> PolicyExecutionResult:
        sorted_rules = sorted(profile.rules, key=lambda r: (r.priority, r.rule_id))

        applied_rules: list[str] = []
        actions_taken: list[str] = []
        annotations: list[str] = []
        requires_review = False
        blocked = False
        final_tier: str = str(getattr(decision, "recommended_tier", "T0_CANDIDATE"))

        for rule in sorted_rules:
            field_value = get_decision_field(decision, rule.condition_field)
            if not evaluate_condition(field_value, rule.condition_op, rule.condition_value):
                continue

            if rule.action not in ALLOWED_ACTIONS:
                continue

            applied_rules.append(rule.rule_id)

            if rule.action == "DOWNGRADE_TRUST":
                target = str(rule.action_params.get("target_tier", final_tier))
                if _tier_index(target) < _tier_index(final_tier):
                    final_tier = target
                    actions_taken.append("DOWNGRADE_TRUST")

            elif rule.action == "BLOCK_PROMOTION":
                blocked = True
                actions_taken.append("BLOCK_PROMOTION")

            elif rule.action == "REQUIRE_REVIEW":
                requires_review = True
                actions_taken.append("REQUIRE_REVIEW")

            elif rule.action == "FLAG_CONFLICT":
                msg = str(rule.action_params.get("message", f"conflict flagged by rule {rule.rule_id}"))
                annotations.append(msg)
                actions_taken.append("FLAG_CONFLICT")

            elif rule.action == "ANNOTATE_ONLY":
                msg = str(rule.action_params.get("message", f"annotated by rule {rule.rule_id}"))
                annotations.append(msg)
                actions_taken.append("ANNOTATE_ONLY")

        return PolicyExecutionResult(
            applied_rules=applied_rules,
            actions_taken=actions_taken,
            final_tier=final_tier,
            annotations=annotations,
            requires_review=requires_review,
            blocked=blocked,
        )
