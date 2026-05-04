"""Validation for proof index artifacts (.proof.json)."""

from __future__ import annotations

from vcse.proof.model import ProofIndex
from vcse.runtime.validate import RuntimeValidationIssue, RuntimeValidationResult


def validate_proof_index(index: ProofIndex) -> RuntimeValidationResult:
    issues: list[RuntimeValidationIssue] = []
    n = len(index.proofs)

    for i, proof in enumerate(index.proofs):
        path = f"proofs[{i}]"

        if not proof.proof_id:
            issues.append(RuntimeValidationIssue(
                code="PROOF_MISSING_PROOF_ID",
                severity="ERROR",
                message="proof_id is required",
                path=path,
            ))

        if not proof.result_claim_id:
            issues.append(RuntimeValidationIssue(
                code="PROOF_MISSING_RESULT_CLAIM_ID",
                severity="ERROR",
                message="result_claim_id is required",
                path=path,
            ))

        if proof.path_length < 0:
            issues.append(RuntimeValidationIssue(
                code="PROOF_INVALID_PATH_LENGTH",
                severity="ERROR",
                message=f"path_length must be >= 0, got {proof.path_length}",
                path=path,
            ))

        if proof.trust_tier < 0:
            issues.append(RuntimeValidationIssue(
                code="PROOF_INVALID_TRUST_TIER",
                severity="ERROR",
                message=f"trust_tier must be >= 0, got {proof.trust_tier}",
                path=path,
            ))

        if proof.verification_status != proof.verification_status.upper():
            issues.append(RuntimeValidationIssue(
                code="PROOF_STATUS_CASING_INVALID",
                severity="ERROR",
                message=f"verification_status must be UPPER_SNAKE_CASE: {proof.verification_status!r}",
                path=path,
            ))

        if proof.verification_status == "VERIFIED" and (
            proof.path_length == 0 or len(proof.supporting_claim_ids) == 0
        ):
            issues.append(RuntimeValidationIssue(
                code="PROOF_ZERO_PATH_VERIFIED",
                severity="ERROR",
                message="VERIFIED proof must have path_length >= 1 and at least one supporting claim",
                path=path,
            ))

        # Every VERIFIED proof must appear in by_result
        if proof.result_claim_id and proof.result_claim_id not in index.by_result:
            issues.append(RuntimeValidationIssue(
                code="PROOF_MISSING_RESULT_INDEX",
                severity="ERROR",
                message=f"proof {proof.proof_id!r} result_claim_id {proof.result_claim_id!r} not in by_result",
                path=path,
            ))

    # Index range checks
    for index_name, index_map in (
        ("by_result", index.by_result),
        ("by_support", index.by_support),
        ("by_subject", index.by_subject),
        ("by_relation", index.by_relation),
        ("by_object", index.by_object),
    ):
        for key, positions in index_map.items():
            seen: set[int] = set()
            for pos in positions:
                if pos < 0 or pos >= n:
                    issues.append(RuntimeValidationIssue(
                        code="PROOF_INDEX_OUT_OF_RANGE",
                        severity="ERROR",
                        message=f"{index_name}[{key!r}] position {pos} out of range (proofs={n})",
                        path=f"{index_name}[{key}][{pos}]",
                    ))
                if pos in seen:
                    issues.append(RuntimeValidationIssue(
                        code="PROOF_DUPLICATE_INDEX_POSITION",
                        severity="ERROR",
                        message=f"{index_name}[{key!r}] duplicate position {pos}",
                        path=f"{index_name}[{key}]",
                    ))
                seen.add(pos)

    if issues:
        return RuntimeValidationResult(
            status="RUNTIME_INVALID",
            issue_count=len(issues),
            issues=tuple(issues),
        )
    return RuntimeValidationResult(
        status="RUNTIME_VALID",
        issue_count=0,
        issues=(),
    )
