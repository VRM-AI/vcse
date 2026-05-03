"""Tests for Policy Execution Layer (v6.6.0)."""

from __future__ import annotations

import pytest

from vcse.policy.actions import ALLOWED_ACTIONS, FORBIDDEN_ACTIONS
from vcse.policy.engine import PolicyExecutionEngine, PolicyExecutionResult
from vcse.policy.executor import PolicyExecutor
from vcse.policy.rules import ExecutionProfile, ExecutionRule
from vcse.trust.policy import TrustPolicy
from vcse.trust.promoter import TrustDecision, TrustPromoter


def _decision(
    *,
    claim_id: str = "c1",
    current_tier: str = "T3_CROSS_SUPPORTED",
    recommended_tier: str = "T4_VERIFIER_CONSISTENT",
    proof_count: int = 2,
    verification_status: str = "VERIFIED",
    blocking_issues: list[str] | None = None,
) -> TrustDecision:
    return TrustDecision(
        claim_id=claim_id,
        current_tier=current_tier,
        recommended_tier=recommended_tier,
        passed=True,
        reasons=["VERIFIER_CONSISTENCY_CONFIRMED"],
        blocking_issues=blocking_issues or [],
        ledger_events=[],
        verification_status=verification_status,
        proof_count=proof_count,
    )


def _rule(
    *,
    rule_id: str = "r1",
    condition_field: str = "recommended_tier",
    condition_op: str = "eq",
    condition_value: object = "T4_VERIFIER_CONSISTENT",
    action: str = "ANNOTATE_ONLY",
    action_params: dict | None = None,
    priority: int = 10,
) -> ExecutionRule:
    return ExecutionRule(
        rule_id=rule_id,
        condition_field=condition_field,
        condition_op=condition_op,
        condition_value=condition_value,
        action=action,
        action_params=action_params or {},
        priority=priority,
    )


def _profile(*rules: ExecutionRule, profile_id: str = "test_profile") -> ExecutionProfile:
    return ExecutionProfile(
        profile_id=profile_id,
        description="Test profile",
        rules=tuple(rules),
    )


# ===========================================================================
# 1. Deterministic rule ordering
# ===========================================================================


def test_rules_evaluated_in_priority_order() -> None:
    """Lower priority value fires first; input order must not affect output order."""
    rule_high = _rule(rule_id="high_prio", priority=1, action="ANNOTATE_ONLY",
                      action_params={"message": "first"})
    rule_low = _rule(rule_id="low_prio", priority=100, action="ANNOTATE_ONLY",
                     action_params={"message": "second"})
    # Passed in reverse order to confirm sorting, not insertion order
    profile = _profile(rule_low, rule_high)

    result = PolicyExecutionEngine().execute(_decision(), profile)
    assert result.applied_rules[0] == "high_prio"
    assert result.applied_rules[1] == "low_prio"


# ===========================================================================
# 2. Priority enforcement
# ===========================================================================


def test_priority_block_fires_before_annotate() -> None:
    """BLOCK_PROMOTION at priority 1 fires before ANNOTATE_ONLY at priority 100; both applied."""
    block_rule = _rule(rule_id="blocker", priority=1, action="BLOCK_PROMOTION")
    annotate_rule = _rule(rule_id="annotator", priority=100, action="ANNOTATE_ONLY",
                          action_params={"message": "seen"})
    profile = _profile(annotate_rule, block_rule)  # reversed to confirm sort

    result = PolicyExecutionEngine().execute(_decision(), profile)
    assert result.blocked is True
    assert "blocker" in result.applied_rules
    assert "annotator" in result.applied_rules
    assert result.applied_rules.index("blocker") < result.applied_rules.index("annotator")


# ===========================================================================
# 3. DOWNGRADE_TRUST behavior
# ===========================================================================


def test_downgrade_trust_lowers_tier() -> None:
    """DOWNGRADE_TRUST reduces final_tier to target_tier when target is lower."""
    rule = _rule(
        action="DOWNGRADE_TRUST",
        action_params={"target_tier": "T3_CROSS_SUPPORTED"},
    )
    profile = _profile(rule)
    decision = _decision(recommended_tier="T4_VERIFIER_CONSISTENT")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T3_CROSS_SUPPORTED"
    assert "DOWNGRADE_TRUST" in result.actions_taken


def test_downgrade_cannot_upgrade_tier() -> None:
    """DOWNGRADE_TRUST targeting a higher tier must not apply; tier unchanged."""
    rule = _rule(
        action="DOWNGRADE_TRUST",
        action_params={"target_tier": "T5_CERTIFIED"},
    )
    profile = _profile(rule)
    decision = _decision(recommended_tier="T4_VERIFIER_CONSISTENT")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T4_VERIFIER_CONSISTENT"


def test_downgrade_multiple_rules_applies_lowest() -> None:
    """Multiple DOWNGRADE_TRUST rules: lowest target tier wins."""
    rule1 = _rule(rule_id="r1", priority=1, action="DOWNGRADE_TRUST",
                  action_params={"target_tier": "T3_CROSS_SUPPORTED"})
    rule2 = _rule(rule_id="r2", priority=2, action="DOWNGRADE_TRUST",
                  action_params={"target_tier": "T2_SOURCE_TRUSTED"})
    profile = _profile(rule1, rule2)
    decision = _decision(recommended_tier="T4_VERIFIER_CONSISTENT")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T2_SOURCE_TRUSTED"


# ===========================================================================
# 4. BLOCK_PROMOTION behavior
# ===========================================================================


def test_block_promotion_sets_blocked_flag() -> None:
    """BLOCK_PROMOTION action sets blocked=True."""
    rule = _rule(action="BLOCK_PROMOTION")
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(), profile)
    assert result.blocked is True
    assert "BLOCK_PROMOTION" in result.actions_taken


def test_block_promotion_tier_unchanged() -> None:
    """BLOCK_PROMOTION does not alter the final_tier value."""
    rule = _rule(action="BLOCK_PROMOTION")
    profile = _profile(rule)
    decision = _decision(recommended_tier="T4_VERIFIER_CONSISTENT")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T4_VERIFIER_CONSISTENT"
    assert result.blocked is True


# ===========================================================================
# 5. No promotion beyond T3→T4 boundary
# ===========================================================================


def test_engine_cannot_promote_t3_to_t4() -> None:
    """Empty profile: T3 decision stays at T3; engine has no promotion mechanism."""
    profile = _profile()
    decision = _decision(recommended_tier="T3_CROSS_SUPPORTED")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T3_CROSS_SUPPORTED"


def test_forbidden_actions_not_in_allowed_set() -> None:
    """PROMOTE_TO_T4, PROMOTE_TO_T5, OVERRIDE_VERIFIER absent from ALLOWED_ACTIONS."""
    assert "PROMOTE_TO_T4" not in ALLOWED_ACTIONS
    assert "PROMOTE_TO_T5" not in ALLOWED_ACTIONS
    assert "OVERRIDE_VERIFIER" not in ALLOWED_ACTIONS
    assert "PROMOTE_TO_T4" in FORBIDDEN_ACTIONS
    assert "PROMOTE_TO_T5" in FORBIDDEN_ACTIONS
    assert "OVERRIDE_VERIFIER" in FORBIDDEN_ACTIONS


# ===========================================================================
# 6. Interaction with conflict flags
# ===========================================================================


def test_flag_conflict_adds_annotation() -> None:
    """FLAG_CONFLICT action appends to annotations."""
    rule = _rule(
        action="FLAG_CONFLICT",
        action_params={"message": "conflict detected by policy"},
    )
    profile = _profile(rule)
    decision = _decision(recommended_tier="T4_VERIFIER_CONSISTENT")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert any("conflict" in a.lower() for a in result.annotations)
    assert "FLAG_CONFLICT" in result.actions_taken


def test_require_review_sets_flag() -> None:
    """REQUIRE_REVIEW action sets requires_review=True."""
    rule = _rule(action="REQUIRE_REVIEW")
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(), profile)
    assert result.requires_review is True
    assert "REQUIRE_REVIEW" in result.actions_taken


def test_annotate_only_adds_message() -> None:
    """ANNOTATE_ONLY adds message to annotations without blocking."""
    rule = _rule(action="ANNOTATE_ONLY", action_params={"message": "flagged for audit"})
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(), profile)
    assert any("flagged for audit" in a for a in result.annotations)
    assert result.blocked is False
    assert result.requires_review is False


# ===========================================================================
# 7. Idempotency
# ===========================================================================


def test_idempotency_same_input_same_output() -> None:
    """Same input always produces identical output."""
    rule = _rule(action="ANNOTATE_ONLY", action_params={"message": "noted"})
    profile = _profile(rule)
    decision = _decision()
    engine = PolicyExecutionEngine()

    result1 = engine.execute(decision, profile)
    result2 = engine.execute(decision, profile)
    assert result1.applied_rules == result2.applied_rules
    assert result1.actions_taken == result2.actions_taken
    assert result1.final_tier == result2.final_tier
    assert result1.annotations == result2.annotations
    assert result1.requires_review == result2.requires_review
    assert result1.blocked == result2.blocked


# ===========================================================================
# Condition operator coverage
# ===========================================================================


def test_condition_proof_count_lt_fires() -> None:
    """lt operator: fires when proof_count < threshold."""
    rule = _rule(condition_field="proof_count", condition_op="lt",
                 condition_value=3, action="REQUIRE_REVIEW")
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(proof_count=2), profile)
    assert result.requires_review is True


def test_condition_proof_count_lt_no_fire() -> None:
    """lt operator: does not fire when proof_count >= threshold."""
    rule = _rule(condition_field="proof_count", condition_op="lt",
                 condition_value=3, action="REQUIRE_REVIEW")
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(proof_count=5), profile)
    assert result.requires_review is False


def test_condition_verification_status_eq_fires() -> None:
    """eq on verification_status fires when value matches."""
    rule = _rule(condition_field="verification_status", condition_op="eq",
                 condition_value="VERIFIED", action="ANNOTATE_ONLY",
                 action_params={"message": "verified claim"})
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(verification_status="VERIFIED"), profile)
    assert result.applied_rules == ["r1"]


def test_condition_verification_status_eq_no_fire() -> None:
    """eq on verification_status does not fire when value differs."""
    rule = _rule(condition_field="verification_status", condition_op="eq",
                 condition_value="UNVERIFIED", action="REQUIRE_REVIEW")
    profile = _profile(rule)

    result = PolicyExecutionEngine().execute(_decision(verification_status="VERIFIED"), profile)
    assert result.requires_review is False


def test_no_matching_rules_passthrough() -> None:
    """Empty profile: final_tier unchanged, no actions taken."""
    profile = _profile()
    decision = _decision(recommended_tier="T5_CERTIFIED")

    result = PolicyExecutionEngine().execute(decision, profile)
    assert result.final_tier == "T5_CERTIFIED"
    assert result.applied_rules == []
    assert result.actions_taken == []
    assert result.blocked is False
    assert result.requires_review is False
    assert result.annotations == []


# ===========================================================================
# PolicyExecutor integration
# ===========================================================================


def test_policy_executor_combines_promoter_and_engine() -> None:
    """PolicyExecutor runs TrustPromoter then PolicyExecutionEngine in sequence."""
    promoter = TrustPromoter(
        policy=TrustPolicy(
            source_trust_threshold=0.7,
            min_independent_sources=1,
            require_verifier_consistency=True,
            require_positive_proof_count=True,
            min_proof_count=1,
            require_gauntlet_pass=True,
        )
    )
    engine = PolicyExecutionEngine()
    executor = PolicyExecutor(promoter=promoter, engine=engine)

    claim = {
        "claim_id": "c1",
        "subject": "A", "relation": "is_a", "object": "B",
        "trust_tier": "T0_CANDIDATE",
        "source_id": "official_government",
        "provenance": {"source_id": "official_government"},
        "created_at": "2026-05-01T00:00:00+00:00",
        "verification_status": "VERIFIED",
        "proof_count": 2,
    }
    rule = _rule(
        condition_field="recommended_tier",
        condition_op="eq",
        condition_value="T4_VERIFIER_CONSISTENT",
        action="REQUIRE_REVIEW",
    )
    profile = _profile(rule)

    decision, exec_result = executor.run(claim, profile, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T4_VERIFIER_CONSISTENT"
    assert exec_result.requires_review is True
