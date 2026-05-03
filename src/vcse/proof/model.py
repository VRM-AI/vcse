"""Proof index data models."""

from __future__ import annotations

from dataclasses import dataclass


_VERIFICATION_ORDER = {
    "VERIFIED": 0,
    "UNKNOWN": 1,
    "UNVERIFIED": 2,
    "FAILED": 3,
}


def verification_rank(status: str) -> int:
    return _VERIFICATION_ORDER.get(status, 99)


@dataclass(frozen=True)
class ProofStep:
    claim_id: str
    subject: str
    relation: str
    object: str
    pack_id: str | None = None
    trust_tier: int | None = None
    verification_status: str | None = None


@dataclass(frozen=True)
class ProofPath:
    proof_id: str
    result_claim_id: str
    result_subject: str
    result_relation: str
    result_object: str
    supporting_claim_ids: tuple[str, ...]
    steps: tuple[ProofStep, ...]
    path_length: int
    trust_tier: int
    verification_status: str
    source: str


@dataclass(frozen=True)
class ProofIndex:
    proofs: tuple[ProofPath, ...]
    by_result: dict[str, tuple[int, ...]]
    by_support: dict[str, tuple[int, ...]]
    by_subject: dict[str, tuple[int, ...]]
    by_relation: dict[str, tuple[int, ...]]
    by_object: dict[str, tuple[int, ...]]

    def proofs_for_result(self, claim_id: str) -> tuple[ProofPath, ...]:
        return tuple(self.proofs[i] for i in self.by_result.get(claim_id, ()))

    def proofs_supporting(self, claim_id: str) -> tuple[ProofPath, ...]:
        return tuple(self.proofs[i] for i in self.by_support.get(claim_id, ()))
