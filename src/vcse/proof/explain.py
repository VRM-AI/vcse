"""Proof-aware explanation helpers."""

from __future__ import annotations

from typing import Any

from vcse.proof.model import ProofIndex, ProofPath


def select_best_proof(index: ProofIndex, claim_id: str) -> ProofPath | None:
    candidates = index.proofs_for_result(claim_id)
    if not candidates:
        return None
    # ProofIndex storage is already sorted (verified-first, shortest, highest tier, lex id).
    return candidates[0]


def proof_path_to_explanation_trace(proof: ProofPath) -> dict[str, Any]:
    return {
        "proof_id": proof.proof_id,
        "result_claim_id": proof.result_claim_id,
        "result_subject": proof.result_subject,
        "result_relation": proof.result_relation,
        "result_object": proof.result_object,
        "verification_status": proof.verification_status,
        "trust_tier": proof.trust_tier,
        "path_length": proof.path_length,
        "source": proof.source,
        "supporting_claim_ids": list(proof.supporting_claim_ids),
        "trace": [
            f"{step.subject} {step.relation} {step.object}" for step in proof.steps
        ],
        "steps": [
            {
                "claim_id": step.claim_id,
                "subject": step.subject,
                "relation": step.relation,
                "object": step.object,
                "trust_tier": step.trust_tier,
                "verification_status": step.verification_status,
                "pack_id": step.pack_id,
            }
            for step in proof.steps
        ],
    }
