"""Impact analysis for conflicts using proof reverse-dependency graph."""

from __future__ import annotations

from typing import Iterable

from vcse.conflict.workflow import ConflictImpact, ConflictRef
from vcse.proof.model import ProofIndex


def analyze_conflict_impact(
    conflicts: Iterable[ConflictRef],
    proof_index: ProofIndex | None,
) -> tuple[ConflictImpact, ...]:
    impacts: list[ConflictImpact] = []
    for conflict in conflicts:
        direct_ids = tuple(
            sorted(cid for cid in (conflict.claim_id_a, conflict.claim_id_b) if cid)
        )
        affected_proof_ids: tuple[str, ...] = ()
        affected_result_claim_ids: tuple[str, ...] = ()
        affected_claim_ids: tuple[str, ...] = direct_ids

        if proof_index is not None:
            proof_ids: set[str] = set()
            results: set[str] = set()
            for cid in direct_ids:
                for path in proof_index.proofs_supporting(cid):
                    proof_ids.add(path.proof_id)
                    results.add(path.result_claim_id)
            affected_proof_ids = tuple(sorted(proof_ids))
            affected_result_claim_ids = tuple(sorted(results))
            affected_claim_ids = tuple(sorted(set(direct_ids) | results))

        impact_score = (
            len(direct_ids)
            + len(affected_proof_ids)
            + len(affected_result_claim_ids)
        )
        impacts.append(
            ConflictImpact(
                conflict_id=conflict.conflict_id,
                affected_claim_ids=affected_claim_ids,
                affected_proof_ids=affected_proof_ids,
                affected_result_claim_ids=affected_result_claim_ids,
                impact_score=impact_score,
            )
        )
    return tuple(sorted(impacts, key=lambda item: item.conflict_id))
