import json

from vcse.interaction.response_modes import ResponseMode, render_response
from vcse.pipeline.runner import cross_pack_reason
from vcse.verifier.final_state import FinalStateEvaluation, FinalStatus


def test_reasoning_does_not_emit_verified_claim_when_unverified() -> None:
    claims = [
        {
            "subject": "Socrates",
            "relation": "has_type",
            "object": "human",
            "pack_id": "pack.a",
            "claim_id": "a1",
            "trust_tier": 3,
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "human",
            "relation": "implies",
            "object": "mortal",
            "pack_id": "pack.b",
            "claim_id": "b1",
            "trust_tier": 2,
            "provenance": {"source_id": "s2"},
        },
    ]
    inferred = cross_pack_reason(claims, rules=None)
    assert len(inferred) == 1
    assert inferred[0]["verification_status"] == "UNVERIFIED"
    assert inferred[0]["proof_count"] == 2
    assert len(inferred[0]["proofs"]) == 2


def test_reasoning_still_emits_valid_verified_claims_unchanged() -> None:
    evaluation = FinalStateEvaluation(
        status=FinalStatus.VERIFIED,
        answer="Socrates is_a Mortal",
        proof_trace=["Socrates is_a Man", "Man is_a Mortal", "Socrates is_a Mortal"],
    )
    assert evaluation.status == FinalStatus.VERIFIED
    assert evaluation.verification_status.value == "VERIFIED"
    assert evaluation.proof_count == 3


def test_json_output_includes_verification_status() -> None:
    evaluation = FinalStateEvaluation(
        status=FinalStatus.VERIFIED,
        answer="Socrates is_a Mortal",
        proof_trace=["Socrates is_a Man", "Man is_a Mortal", "Socrates is_a Mortal"],
    )
    payload = json.loads(render_response(evaluation, ResponseMode.STRICT))
    assert payload["status"] == "VERIFIED"
    assert payload["verification_status"] == "VERIFIED"
    assert payload["proof_count"] == 3
