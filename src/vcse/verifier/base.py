"""Verifier base types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from vcse.memory.world_state import WorldStateMemory


@dataclass
class VerificationResult:
    passed: bool
    score: float
    status: str
    proof_count: int = 0
    proof_trace: tuple[str, ...] = ()
    reasons: list[str] = field(default_factory=list)
    affected_elements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.proof_count = max(0, int(self.proof_count))
        self.proof_trace = tuple(str(step) for step in (self.proof_trace or ()))

    @classmethod
    def pass_result(
        cls,
        status: str = "PASSED",
        score: float = 1.0,
        reasons: list[str] | None = None,
        affected_elements: list[str] | None = None,
    ) -> "VerificationResult":
        return cls(
            passed=True,
            score=score,
            status=status,
            proof_count=0,
            proof_trace=(),
            reasons=list(reasons or []),
            affected_elements=list(affected_elements or []),
        )

    @classmethod
    def fail_result(
        cls,
        status: str = "FAILED",
        score: float = 0.0,
        reasons: list[str] | None = None,
        affected_elements: list[str] | None = None,
    ) -> "VerificationResult":
        return cls(
            passed=False,
            score=score,
            status=status,
            proof_count=0,
            proof_trace=(),
            reasons=list(reasons or []),
            affected_elements=list(affected_elements or []),
        )


class Verifier(Protocol):
    def evaluate(self, state: WorldStateMemory, transition: object | None = None) -> VerificationResult:
        ...
