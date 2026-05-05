"""Reusable reason service for .csrf runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vcse.conflict.detector import ConflictDetector
from vcse.explain import ExplanationBuilder, ExplanationRenderer as ProofExplanationRenderer
from vcse.pipeline.runner import cross_pack_reason
from vcse.policy import DEFAULT_POLICY, PolicyEnforcer
from vcse.runtime.hardening import RuntimeArtifactError, load_csrf_checked, load_proof_index_checked


REASON_COMPLETE = "REASON_COMPLETE"
REASON_FAILED = "REASON_FAILED"
REASON_RUNTIME_INVALID = "REASON_RUNTIME_INVALID"
REASON_PROOF_INVALID = "REASON_PROOF_INVALID"


@dataclass(frozen=True)
class ReasonServiceRequest:
    csrf_path: Path
    proof_index_path: Path | None = None
    trusted_only: bool = False
    explain: bool = False
    max_results: int | None = None


@dataclass(frozen=True)
class ReasonServiceResult:
    status: str
    inferred_count: int
    inferred_claims: tuple[dict[str, Any], ...]
    explanations: dict[str, Any] | None = None
    runtime_validation: dict[str, Any] | None = None
    proof_validation: dict[str, Any] | None = None
    issues: tuple[str, ...] = field(default_factory=tuple)


def run_reason_service(request: ReasonServiceRequest) -> ReasonServiceResult:
    """
    Load, validate, and reason over a .csrf runtime artifact.

    Returns a structured ReasonServiceResult. Raises RuntimeArtifactError for
    invalid artifacts; callers map those to appropriate API/CLI error responses.
    """
    if not request.csrf_path.exists():
        raise FileNotFoundError(f"Runtime artifact not found: {request.csrf_path}")

    try:
        runtime = load_csrf_checked(request.csrf_path)
    except RuntimeArtifactError:
        raise
    except Exception as exc:
        raise RuntimeArtifactError(f"Failed to load runtime artifact: {exc}") from exc

    if request.proof_index_path is not None:
        if not request.proof_index_path.exists():
            raise FileNotFoundError(f"Proof index not found: {request.proof_index_path}")
        try:
            load_proof_index_checked(request.proof_index_path)
        except RuntimeArtifactError:
            raise
        except Exception as exc:
            raise RuntimeArtifactError(f"Failed to load proof index: {exc}") from exc

    runtime_claims_source: list[dict[str, Any]] = []
    for item in runtime.records:
        if request.trusted_only and item.lifecycle_status not in {"certified", "trusted"}:
            continue
        runtime_claims_source.append(
            {
                "subject": item.subject,
                "relation": item.relation,
                "object": item.object,
                "pack_id": "cmcf",
                "provenance": {"provenance_id": item.provenance_id},
                "trust_tier": item.trust_tier,
                "claim_id": item.claim_id,
                "verification_status": item.verification_status,
                "lifecycle_status": item.lifecycle_status,
            }
        )

    policy_enforcer = PolicyEnforcer()
    runtime_claims: list[dict[str, Any]] = []
    for claim in runtime_claims_source:
        decision = policy_enforcer.evaluate_claim(claim, DEFAULT_POLICY)
        if decision.status != "BLOCKED":
            runtime_claims.append(claim)

    inferred_claims = cross_pack_reason(runtime_claims, rules=None)

    if request.max_results is not None:
        inferred_claims = inferred_claims[: request.max_results]

    explanations: dict[str, Any] | None = None
    if request.explain:
        explanation_result = ExplanationBuilder().explain_reasoning_results(inferred_claims)
        explanations = ProofExplanationRenderer().render_result_json(explanation_result)

    return ReasonServiceResult(
        status=REASON_COMPLETE,
        inferred_count=len(inferred_claims),
        inferred_claims=tuple(inferred_claims),
        explanations=explanations,
    )
