"""Helpers to build the deterministic ProofIndex container from paths."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from vcse.proof.model import ProofIndex, ProofPath, verification_rank


def _sort_key(path: ProofPath) -> tuple:
    return (
        path.result_claim_id,
        verification_rank(path.verification_status),
        path.path_length,
        -path.trust_tier,
        path.proof_id,
    )


def build_proof_index(paths: Iterable[ProofPath]) -> ProofIndex:
    deduped: dict[str, ProofPath] = {}
    for path in paths:
        deduped[path.proof_id] = path

    sorted_paths = tuple(sorted(deduped.values(), key=_sort_key))

    by_result: dict[str, list[int]] = defaultdict(list)
    by_support: dict[str, list[int]] = defaultdict(list)
    by_subject: dict[str, list[int]] = defaultdict(list)
    by_relation: dict[str, list[int]] = defaultdict(list)
    by_object: dict[str, list[int]] = defaultdict(list)

    for idx, path in enumerate(sorted_paths):
        by_result[path.result_claim_id].append(idx)
        by_subject[path.result_subject].append(idx)
        by_relation[path.result_relation].append(idx)
        by_object[path.result_object].append(idx)
        for cid in path.supporting_claim_ids:
            by_support[cid].append(idx)

    def _freeze(d: dict[str, list[int]]) -> dict[str, tuple[int, ...]]:
        return {key: tuple(value) for key, value in sorted(d.items())}

    return ProofIndex(
        proofs=sorted_paths,
        by_result=_freeze(by_result),
        by_support=_freeze(by_support),
        by_subject=_freeze(by_subject),
        by_relation=_freeze(by_relation),
        by_object=_freeze(by_object),
    )
