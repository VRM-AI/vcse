"""Policy executor — combines TrustPromoter with PolicyExecutionEngine."""

from __future__ import annotations

from typing import Any

from vcse.policy.engine import PolicyExecutionEngine, PolicyExecutionResult
from vcse.policy.rules import ExecutionProfile
from vcse.trust.promoter import TrustDecision, TrustPromoter


class PolicyExecutor:
    def __init__(self, promoter: TrustPromoter, engine: PolicyExecutionEngine) -> None:
        self.promoter = promoter
        self.engine = engine

    def run(
        self,
        claim: dict[str, Any],
        profile: ExecutionProfile,
        *,
        support_count: int = 1,
        conflict_count: int = 0,
    ) -> tuple[TrustDecision, PolicyExecutionResult]:
        decision = self.promoter.evaluate_claim(claim, support_count=support_count, conflict_count=conflict_count)
        result = self.engine.execute(decision, profile)
        return decision, result
