from vcse.memory.relations import RelationSchema
from vcse.memory.world_state import TruthStatus, WorldStateMemory
from vcse.proposer.rule_based import RuleBasedProposer
from vcse.search.beam import BeamSearch
from vcse.verifier.stack import VerifierStack
from vcse.verifier.final_state import FinalStateEvaluation, FinalStateEvaluator, FinalStatus, VerificationStatus


def _verified_state() -> WorldStateMemory:
    state = WorldStateMemory()
    state.add_relation_schema(RelationSchema("is_a", transitive=True))
    state.add_claim("Socrates", "is_a", "Man", TruthStatus.ASSERTED)
    state.add_claim("Man", "is_a", "Mortal", TruthStatus.ASSERTED)
    state.add_goal("Socrates", "is_a", "Mortal")
    return state


def test_verifier_returns_verified_when_proofs_exist() -> None:
    result = BeamSearch(
        proposer=RuleBasedProposer(),
        verifier_stack=VerifierStack.default(),
        final_state_evaluator=FinalStateEvaluator(),
    ).run(_verified_state())
    assert result.evaluation.status == FinalStatus.VERIFIED
    assert result.evaluation.verification_status == VerificationStatus.VERIFIED
    assert result.evaluation.proof_count > 0


def test_verifier_returns_unverified_when_proof_set_empty() -> None:
    result = FinalStateEvaluation(status=FinalStatus.INCONCLUSIVE, answer="A is_a B", proof_trace=[])
    assert result.verification_status == VerificationStatus.UNVERIFIED
    assert result.proof_count == 0
    assert result.proofs == []


def test_zero_proof_is_not_marked_verified() -> None:
    result = FinalStateEvaluation(status=FinalStatus.VERIFIED, answer="A is_a B", proof_trace=[])
    assert result.status == FinalStatus.INCONCLUSIVE
    assert result.verification_status == VerificationStatus.UNVERIFIED
    assert result.proof_count == 0
    assert "No proof trace available" in result.reasons


def test_contradiction_maps_to_failed_verification_status() -> None:
    state = WorldStateMemory()
    first = state.add_claim("x", "equals", "3", TruthStatus.ASSERTED)
    second = state.add_claim("x", "equals", "4", TruthStatus.ASSERTED)
    state.record_contradiction(first, "x equals both 3 and 4", related_element_ids=[second])
    result = FinalStateEvaluator().evaluate(state)
    assert result.status == FinalStatus.CONTRADICTORY
    assert result.verification_status == VerificationStatus.FAILED
