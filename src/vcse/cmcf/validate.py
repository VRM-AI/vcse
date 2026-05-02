"""CMCF record validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vcse.cmcf.hash import compute_content_hash
from vcse.cmcf.model import CMCFRecord
from vcse.cmcf.serialize import record_to_dict

_LIFECYCLE_ALLOWED = {"candidate", "reviewed", "certified", "trusted", "blocked"}
_VERIFICATION_ALLOWED = {"VERIFIED", "UNVERIFIED", "FAILED", "UNKNOWN"}
_CERTIFICATION_ALLOWED = {"NOT_CERTIFIED", "CERTIFIED", "CERTIFICATION_FAILED", "CERTIFICATION_BLOCKED"}
_PROVENANCE_ALLOWED = {
    "SOURCE_ATTACHED_UNVERIFIED",
    "SOURCE_VERIFIED",
    "MISSING_PROVENANCE",
    "PROVENANCE_INVALID",
}
_POLICY_ALLOWED = {"ALLOWED", "BLOCKED", "UNKNOWN"}


@dataclass(frozen=True)
class CMCFValidationIssue:
    code: str
    severity: str
    message: str
    path: str


def validate_record(record: CMCFRecord) -> list[CMCFValidationIssue]:
    issues: list[CMCFValidationIssue] = []

    if not str(record.cmcf_version).strip():
        issues.append(_issue("CMCF_VERSION_REQUIRED", "error", "cmcf_version is required", "cmcf_version"))

    if not str(record.claim.subject).strip():
        issues.append(_issue("CLAIM_SUBJECT_REQUIRED", "error", "subject must be non-empty", "claim.subject"))
    if not str(record.claim.relation).strip():
        issues.append(_issue("CLAIM_RELATION_REQUIRED", "error", "relation must be non-empty", "claim.relation"))
    if not str(record.claim.object).strip():
        issues.append(_issue("CLAIM_OBJECT_REQUIRED", "error", "object must be non-empty", "claim.object"))
    if not _is_atomic(record.claim.subject, record.claim.relation, record.claim.object):
        issues.append(_issue("CLAIM_NOT_ATOMIC", "error", "claim must be atomic", "claim"))

    if not str(record.provenance.source_type).strip():
        issues.append(_issue("PROVENANCE_REQUIRED", "error", "provenance.source_type is required", "provenance.source_type"))
    if not str(record.provenance.provenance_id).strip():
        issues.append(_issue("PROVENANCE_ID_REQUIRED", "error", "provenance_id is required", "provenance.provenance_id"))

    if record.status.lifecycle_status not in _LIFECYCLE_ALLOWED:
        issues.append(_issue("LIFECYCLE_STATUS_INVALID", "error", "invalid lifecycle_status", "status.lifecycle_status"))
    if record.status.verification_status not in _VERIFICATION_ALLOWED:
        issues.append(
            _issue("VERIFICATION_STATUS_INVALID", "error", "invalid verification_status", "status.verification_status")
        )
    if record.status.certification_status not in _CERTIFICATION_ALLOWED:
        issues.append(
            _issue("CERTIFICATION_STATUS_INVALID", "error", "invalid certification_status", "status.certification_status")
        )
    if record.status.provenance_status not in _PROVENANCE_ALLOWED:
        issues.append(
            _issue("PROVENANCE_STATUS_INVALID", "error", "invalid provenance_status", "status.provenance_status")
        )
    if record.status.policy_status not in _POLICY_ALLOWED:
        issues.append(_issue("POLICY_STATUS_INVALID", "error", "invalid policy_status", "status.policy_status"))

    if not isinstance(record.trust.trust_tier, int) or record.trust.trust_tier < 0:
        issues.append(_issue("TRUST_TIER_INVALID", "error", "trust_tier must be integer >= 0", "trust.trust_tier"))

    if not str(record.integrity.content_hash).strip():
        issues.append(_issue("CONTENT_HASH_REQUIRED", "error", "integrity.content_hash is required", "integrity.content_hash"))
    elif not str(record.integrity.content_hash).startswith("sha256:"):
        issues.append(_issue("CONTENT_HASH_FORMAT_INVALID", "error", "content_hash must start with sha256:", "integrity.content_hash"))
    else:
        payload = record_to_dict(record)
        canonical_payload = _record_without_integrity(payload)
        recomputed = compute_content_hash(canonical_payload)
        if recomputed != record.integrity.content_hash:
            issues.append(
                _issue(
                    "CONTENT_HASH_MISMATCH",
                    "error",
                    "content_hash does not match canonical record content",
                    "integrity.content_hash",
                )
            )

    try:
        record_to_dict(record)
    except ValueError as exc:
        issues.append(_issue("JSON_UNSAFE_VALUE", "error", str(exc), "record"))

    return issues


def _record_without_integrity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "cmcf_version": payload.get("cmcf_version"),
        "claim": payload.get("claim"),
        "provenance": payload.get("provenance"),
        "status": payload.get("status"),
        "trust": payload.get("trust"),
        "metadata": payload.get("metadata"),
    }


def _is_atomic(subject: str, relation: str, object_value: str) -> bool:
    for value in (subject, relation, object_value):
        if "\n" in value or "\r" in value:
            return False
    return True


def _issue(code: str, severity: str, message: str, path: str) -> CMCFValidationIssue:
    return CMCFValidationIssue(code=code, severity=severity, message=message, path=path)
