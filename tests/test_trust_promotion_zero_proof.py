from __future__ import annotations

from vcse.trust.policy import TrustPolicy
from vcse.trust.promoter import TrustPromoter


def _promoter(*, require_gauntlet_pass: bool = True, require_verifier_consistency: bool = True) -> TrustPromoter:
    return TrustPromoter(
        policy=TrustPolicy(
            source_trust_threshold=0.7,
            min_independent_sources=1,
            require_verifier_consistency=require_verifier_consistency,
            require_positive_proof_count=True,
            min_proof_count=1,
            require_gauntlet_pass=require_gauntlet_pass,
        )
    )


def _base_claim() -> dict[str, object]:
    return {
        "claim_id": "c1",
        "subject": "A",
        "relation": "is_a",
        "object": "B",
        "trust_tier": "T0_CANDIDATE",
        "source_id": "official_government",
        "provenance": {"source_id": "official_government"},
        "created_at": "2026-05-01T00:00:00+00:00",
    }


def test_zero_proof_cannot_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "NO_PROOF", "proof_count": 0})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "INSUFFICIENT_VERIFIER_PROOF_COUNT" in decision.blocking_issues


def test_zero_proof_cannot_reach_t5() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "NO_PROOF", "proof_count": 0})
    decision = _promoter(require_gauntlet_pass=False).evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier != "T5_CERTIFIED"
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"


def test_missing_verifier_result_blocks_above_t3() -> None:
    decision = _promoter().evaluate_claim(_base_claim(), support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "VERIFIER_RESULT_REQUIRED" in decision.blocking_issues


def test_verified_with_positive_proofs_can_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "VERIFIED", "proof_count": 2, "verifier_confidence": 0.95})
    decision = _promoter(require_gauntlet_pass=True).evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T4_VERIFIER_CONSISTENT"
    assert "VERIFIER_CONSISTENCY_CONFIRMED" in decision.reasons


def test_nan_confidence_blocks_promotion() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "VERIFIED", "proof_count": 2, "verifier_confidence": float("nan")})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_FINITE_VERIFIER_CONFIDENCE" in decision.blocking_issues


def test_inf_confidence_blocks_promotion() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "VERIFIED", "proof_count": 2, "verifier_confidence": float("inf")})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_FINITE_VERIFIER_CONFIDENCE" in decision.blocking_issues


def test_existing_positive_path_still_passes() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "VERIFIED", "proof_count": 2, "verifier_confidence": 0.9})
    decision = _promoter(require_gauntlet_pass=False).evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T5_CERTIFIED"
    assert decision.passed is True


# --- Negative path coverage: policy override cannot bypass proof gate ---


def test_zero_proof_cannot_reach_t4_even_when_verifier_consistency_disabled() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "NO_PROOF", "proof_count": 0})
    decision = _promoter(require_verifier_consistency=False).evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "ZERO_PROOF_BLOCKED" in decision.blocking_issues


def test_zero_proof_cannot_reach_t5_even_when_verifier_consistency_disabled() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "NO_PROOF", "proof_count": 0})
    decision = _promoter(require_gauntlet_pass=False, require_verifier_consistency=False).evaluate_claim(
        claim, support_count=1, conflict_count=0
    )
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"


# --- Non-VERIFIED statuses blocked regardless of proof count ---


def test_unverified_status_cannot_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "UNVERIFIED", "proof_count": 2})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_VERIFIED_STATUS_BLOCKED" in decision.blocking_issues


def test_indeterminate_status_cannot_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "INDETERMINATE", "proof_count": 2})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_VERIFIED_STATUS_BLOCKED" in decision.blocking_issues


def test_failed_status_cannot_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "FAILED", "proof_count": 2})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_VERIFIED_STATUS_BLOCKED" in decision.blocking_issues


def test_no_proof_status_with_nonzero_proof_count_cannot_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "NO_PROOF", "proof_count": 2})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "NON_VERIFIED_STATUS_BLOCKED" in decision.blocking_issues


# --- VERIFIED + proof_count >= 1 still reaches T4 ---


def test_verified_with_proof_count_one_can_reach_t4() -> None:
    claim = _base_claim()
    claim.update({"verification_status": "VERIFIED", "proof_count": 1})
    decision = _promoter(require_gauntlet_pass=True).evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T4_VERIFIER_CONSISTENT"


# --- Missing verifier blocked ---


def test_missing_verifier_blocks_t4() -> None:
    claim = _base_claim()
    claim.update({"proof_count": 1})
    decision = _promoter().evaluate_claim(claim, support_count=1, conflict_count=0)
    assert decision.recommended_tier == "T3_CROSS_SUPPORTED"
    assert "VERIFIER_RESULT_REQUIRED" in decision.blocking_issues
