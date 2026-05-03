from __future__ import annotations

from vcse.trust.policy import TrustPolicy
from vcse.trust.promoter import TrustPromoter


def _promoter(*, require_gauntlet_pass: bool = True) -> TrustPromoter:
    return TrustPromoter(
        policy=TrustPolicy(
            source_trust_threshold=0.7,
            min_independent_sources=1,
            require_verifier_consistency=True,
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
