"""Deterministic certification gate for pack trust eligibility."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vcse.conflict.detector import ConflictDetector
from vcse.trust.certification import (
    CERTIFICATION_BLOCKED,
    CERTIFICATION_FAILED,
    CERTIFICATION_PASSED,
    CertificationIssue,
    CertificationResult,
)
from vcse.trust.policy import TrustPolicy


class CertificationGate:
    @staticmethod
    def certify_pack(pack_path: Path, policy: TrustPolicy) -> CertificationResult:
        issues: list[CertificationIssue] = []
        claim_count = 0
        conflict_count = 0
        missing_provenance_count = 0

        if not pack_path.exists() or not pack_path.is_dir():
            issues.append(
                CertificationIssue(
                    code="PACK_NOT_FOUND",
                    severity="error",
                    message=f"pack path not found: {pack_path}",
                )
            )
            return _result(pack_path.name, policy, claim_count, conflict_count, missing_provenance_count, issues)

        pack_json_path = pack_path / "pack.json"
        claims_path = pack_path / "claims.jsonl"
        provenance_path = pack_path / "provenance.jsonl"

        if not pack_json_path.exists():
            issues.append(CertificationIssue(code="MISSING_PACK_JSON", severity="error", message="missing pack.json"))
        if not claims_path.exists():
            issues.append(CertificationIssue(code="MISSING_CLAIMS", severity="error", message="missing claims.jsonl"))
        if not provenance_path.exists():
            issues.append(
                CertificationIssue(code="MISSING_PROVENANCE", severity="error", message="missing provenance.jsonl")
            )
        if issues:
            return _result(pack_path.name, policy, claim_count, conflict_count, missing_provenance_count, issues)

        manifest = _safe_json_load(pack_json_path, issues, "INVALID_PACK_JSON")
        if manifest is None:
            return _result(pack_path.name, policy, claim_count, conflict_count, missing_provenance_count, issues)

        pack_id = str(manifest.get("id") or manifest.get("pack_id") or pack_path.name)
        lifecycle_status = str(manifest.get("lifecycle_status", "candidate")).strip() or "candidate"
        if lifecycle_status not in set(policy.allowed_pack_statuses):
            issues.append(
                CertificationIssue(
                    code="PACK_STATUS_NOT_ALLOWED",
                    severity="error",
                    message=f"lifecycle_status '{lifecycle_status}' is not certifiable under policy",
                )
            )

        provenance_rows = _load_jsonl(provenance_path, issues, "INVALID_PROVENANCE_ROW")
        provenance_count = len(provenance_rows)

        claims = _load_jsonl(claims_path, issues, "INVALID_CLAIM_ROW")
        claim_count = len(claims)

        seen_keys: set[tuple[str, str, str]] = set()
        for idx, claim in enumerate(claims, start=1):
            subject = str(claim.get("subject", "")).strip()
            relation = str(claim.get("relation", "")).strip()
            obj = str(claim.get("object", "")).strip()
            claim_id = str(claim.get("claim_id", f"claim:{idx}"))
            source = str(claim.get("provenance", {}).get("source_id", "")).strip()

            if not subject or not relation or not obj:
                issues.append(
                    CertificationIssue(
                        code="INVALID_CLAIM_SHAPE",
                        severity="error",
                        message=f"invalid claim shape at line {idx}",
                        claim_id=claim_id,
                        relation=relation or None,
                        source=source or None,
                    )
                )
                continue

            key = (subject, relation, obj)
            if key in seen_keys:
                issues.append(
                    CertificationIssue(
                        code="DUPLICATE_CLAIM_KEY",
                        severity="error",
                        message="duplicate claim key detected",
                        claim_id=claim_id,
                        relation=relation,
                        source=source or None,
                    )
                )
            else:
                seen_keys.add(key)

            claim_tier = _parse_trust_tier(claim.get("trust_tier", 0))
            if claim_tier < policy.min_trust_tier:
                issues.append(
                    CertificationIssue(
                        code="TRUST_TIER_TOO_LOW",
                        severity="error",
                        message=(
                            f"claim trust tier {claim_tier} below minimum {policy.min_trust_tier}"
                        ),
                        claim_id=claim_id,
                        relation=relation,
                        source=source or None,
                    )
                )

            if policy.allowed_relations is not None and relation not in set(policy.allowed_relations):
                issues.append(
                    CertificationIssue(
                        code="RELATION_NOT_ALLOWED",
                        severity="error",
                        message=f"relation '{relation}' is not allowed by policy",
                        claim_id=claim_id,
                        relation=relation,
                        source=source or None,
                    )
                )

            if policy.blocked_relations is not None and relation in set(policy.blocked_relations):
                issues.append(
                    CertificationIssue(
                        code="RELATION_BLOCKED",
                        severity="error",
                        message=f"relation '{relation}' is blocked by policy",
                        claim_id=claim_id,
                        relation=relation,
                        source=source or None,
                    )
                )

            claim_source = str(claim.get("source_id") or source).strip()
            if (not claim_source) and (not policy.allow_missing_sources):
                issues.append(
                    CertificationIssue(
                        code="MISSING_SOURCE",
                        severity="error",
                        message="claim source_id is required by policy",
                        claim_id=claim_id,
                        relation=relation,
                    )
                )

            if policy.require_provenance:
                prov = claim.get("provenance")
                if not isinstance(prov, dict):
                    missing_provenance_count += 1
                    issues.append(
                        CertificationIssue(
                            code="MISSING_PROVENANCE_FOR_CLAIM",
                            severity="error",
                            message="claim provenance is required by policy",
                            claim_id=claim_id,
                            relation=relation,
                        )
                    )
                else:
                    required = ["source_type", "source_id", "location", "evidence_text"]
                    missing_fields = [field for field in required if str(prov.get(field, "")).strip() == ""]
                    if missing_fields:
                        missing_provenance_count += 1
                        issues.append(
                            CertificationIssue(
                                code="INCOMPLETE_PROVENANCE",
                                severity="error",
                                message="missing provenance fields: " + ",".join(sorted(missing_fields)),
                                claim_id=claim_id,
                                relation=relation,
                                source=source or None,
                            )
                        )

        if policy.require_provenance and provenance_count < claim_count:
            issues.append(
                CertificationIssue(
                    code="PROVENANCE_COUNT_MISMATCH",
                    severity="error",
                    message="provenance.jsonl rows fewer than claims.jsonl rows",
                )
            )

        conflict_count = len(ConflictDetector().detect(claims))
        if conflict_count > 0 and not policy.allow_conflicts:
            issues.append(
                CertificationIssue(
                    code="CONFLICTS_PRESENT",
                    severity="error",
                    message=f"pack has {conflict_count} conflicts and policy disallows conflicts",
                )
            )

        return _result(pack_id, policy, claim_count, conflict_count, missing_provenance_count, issues)


def certification_report_payload(result: CertificationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "pack_id": result.pack_id,
        "policy_id": result.policy_id,
        "claim_count": result.claim_count,
        "certified_claim_count": result.certified_claim_count,
        "blocked_claim_count": result.blocked_claim_count,
        "conflict_count": result.conflict_count,
        "missing_provenance_count": result.missing_provenance_count,
        "issues": [asdict(issue) for issue in result.issues],
    }


def _safe_json_load(path: Path, issues: list[CertificationIssue], code: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        issues.append(CertificationIssue(code=code, severity="error", message=f"{path.name}: {exc.msg}"))
        return None
    if not isinstance(payload, dict):
        issues.append(CertificationIssue(code=code, severity="error", message=f"{path.name} must be an object"))
        return None
    return payload


def _load_jsonl(path: Path, issues: list[CertificationIssue], code: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                CertificationIssue(code=code, severity="error", message=f"{path.name} line {idx}: {exc.msg}")
            )
            continue
        if not isinstance(payload, dict):
            issues.append(
                CertificationIssue(code=code, severity="error", message=f"{path.name} line {idx}: must be object")
            )
            continue
        rows.append(payload)
    return rows


def _parse_trust_tier(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if text.isdigit():
        return int(text)
    if text.upper().startswith("T"):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return int(digits)
    return 0


def _result(
    pack_id: str,
    policy: TrustPolicy,
    claim_count: int,
    conflict_count: int,
    missing_provenance_count: int,
    issues: list[CertificationIssue],
) -> CertificationResult:
    ordered = tuple(
        sorted(
            issues,
            key=lambda item: (
                item.severity,
                item.code,
                item.claim_id or "",
                item.relation or "",
                item.source or "",
                item.message,
            ),
        )
    )
    has_errors = any(item.severity == "error" for item in ordered)
    status = CERTIFICATION_PASSED
    if has_errors:
        status = CERTIFICATION_BLOCKED if claim_count > 0 else CERTIFICATION_FAILED
    blocked_count = len({item.claim_id for item in ordered if item.claim_id})
    return CertificationResult(
        status=status,
        pack_id=pack_id,
        policy_id=policy.policy_id,
        claim_count=claim_count,
        certified_claim_count=max(0, claim_count - blocked_count) if status == CERTIFICATION_PASSED else 0,
        blocked_claim_count=blocked_count if status != CERTIFICATION_PASSED else 0,
        conflict_count=conflict_count,
        missing_provenance_count=missing_provenance_count,
        issues=ordered,
    )
