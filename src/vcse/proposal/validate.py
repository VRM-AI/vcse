"""Candidate Proposal validation service."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

from vcse.proposal.model import (
    ALLOWED_CLAIM_FIELDS,
    ALLOWED_TOP_LEVEL_FIELDS,
    CANDIDATE_PROPOSAL,
    FACTUAL_CLAIM_PACK,
    FORBIDDEN_CLAIM_FIELDS,
    FORBIDDEN_METADATA_KEYS,
    FORBIDDEN_ROOT_FIELDS,
    INVALID_CANDIDATE_KIND,
    INVALID_CLAIM_STATUS,
    INVALID_CLAIMS,
    INVALID_PROPOSAL_KIND,
    INVALID_SOURCE_SPAN_IDS,
    MAX_PROPOSAL_JSON_BYTES,
    MISSING_CANDIDATE_KIND,
    MISSING_CLAIM_ID,
    MISSING_CLAIM_OBJECT,
    MISSING_CLAIM_PREDICATE,
    MISSING_CLAIM_STATUS,
    MISSING_CLAIM_SUBJECT,
    MISSING_CLAIM_TYPE,
    MISSING_CLAIMS,
    MISSING_PROPOSAL_KIND,
    MISSING_PROPOSAL_VERSION,
    MISSING_SOURCE_SPAN_IDS,
    NON_FINITE_VALUE,
    PAYLOAD_TOO_LARGE,
    PROPOSAL_INVALID,
    PROPOSAL_VALID,
    PROPOSED,
    UNKNOWN_CLAIM_FIELD,
    UNKNOWN_TOP_LEVEL_FIELD,
    CandidateClaimProposal,
    CandidateProposal,
    CandidateProposalValidationResult,
)


def _has_non_finite(value: Any) -> bool:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return True
    if isinstance(value, dict):
        return any(_has_non_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_non_finite(v) for v in value)
    return False


def _invalid(issues: list[str], proposal_kind: str | None = None, candidate_kind: str | None = None) -> CandidateProposalValidationResult:
    return CandidateProposalValidationResult(
        status=PROPOSAL_INVALID,
        accepted=False,
        proposal_kind=proposal_kind,
        candidate_kind=candidate_kind,
        claim_count=0,
        issues=tuple(dict.fromkeys(issues)),
    )


def validate_candidate_proposal_dict(
    payload: Mapping[str, Any],
) -> CandidateProposalValidationResult:
    issues: list[str] = []
    proposal_kind: str | None = None
    candidate_kind: str | None = None

    if not isinstance(payload, dict):
        return _invalid(["INVALID_CLAIMS"])

    # Check for forbidden root-level authority fields first (before unknown-field check)
    for field_name, reason_code in FORBIDDEN_ROOT_FIELDS.items():
        if field_name in payload:
            issues.append(reason_code)

    # Check for unknown top-level fields (excluding forbidden ones which are handled above)
    known_and_forbidden = ALLOWED_TOP_LEVEL_FIELDS | frozenset(FORBIDDEN_ROOT_FIELDS.keys())
    for key in payload:
        if key not in known_and_forbidden:
            issues.append(UNKNOWN_TOP_LEVEL_FIELD)
            break

    # proposal_version
    if "proposal_version" not in payload or not str(payload.get("proposal_version", "")).strip():
        issues.append(MISSING_PROPOSAL_VERSION)

    # proposal_kind
    raw_kind = payload.get("proposal_kind")
    if raw_kind is None or str(raw_kind).strip() == "":
        issues.append(MISSING_PROPOSAL_KIND)
    elif raw_kind != CANDIDATE_PROPOSAL:
        issues.append(INVALID_PROPOSAL_KIND)
    else:
        proposal_kind = raw_kind

    # candidate_kind
    raw_ckind = payload.get("candidate_kind")
    if raw_ckind is None or str(raw_ckind).strip() == "":
        issues.append(MISSING_CANDIDATE_KIND)
    elif raw_ckind != FACTUAL_CLAIM_PACK:
        issues.append(INVALID_CANDIDATE_KIND)
    else:
        candidate_kind = raw_ckind

    # claims
    raw_claims = payload.get("claims")
    if raw_claims is None:
        issues.append(MISSING_CLAIMS)
    elif not isinstance(raw_claims, list):
        issues.append(INVALID_CLAIMS)
    elif len(raw_claims) == 0:
        issues.append(MISSING_CLAIMS)
    else:
        # Validate each claim
        for claim in raw_claims:
            if not isinstance(claim, dict):
                issues.append(INVALID_CLAIMS)
                continue

            # Check forbidden claim-level authority fields
            for field_name, reason_code in FORBIDDEN_CLAIM_FIELDS.items():
                if field_name in claim:
                    issues.append(reason_code)

            # Check for unknown claim fields
            known_and_forbidden_claim = ALLOWED_CLAIM_FIELDS | frozenset(FORBIDDEN_CLAIM_FIELDS.keys())
            for key in claim:
                if key not in known_and_forbidden_claim:
                    issues.append(UNKNOWN_CLAIM_FIELD)
                    break

            # Required claim fields
            if not claim.get("claim_id") or not str(claim.get("claim_id", "")).strip():
                issues.append(MISSING_CLAIM_ID)

            if not claim.get("claim_type") or not str(claim.get("claim_type", "")).strip():
                issues.append(MISSING_CLAIM_TYPE)

            raw_status = claim.get("status")
            if raw_status is None or str(raw_status).strip() == "":
                issues.append(MISSING_CLAIM_STATUS)
            elif raw_status != PROPOSED:
                issues.append(INVALID_CLAIM_STATUS)

            if not claim.get("subject") or not str(claim.get("subject", "")).strip():
                issues.append(MISSING_CLAIM_SUBJECT)

            if not claim.get("predicate") or not str(claim.get("predicate", "")).strip():
                issues.append(MISSING_CLAIM_PREDICATE)

            if not claim.get("object") or not str(claim.get("object", "")).strip():
                issues.append(MISSING_CLAIM_OBJECT)

            spans = claim.get("source_span_ids")
            if spans is None:
                issues.append(MISSING_SOURCE_SPAN_IDS)
            elif not isinstance(spans, list) or len(spans) == 0:
                issues.append(MISSING_SOURCE_SPAN_IDS)
            elif not all(isinstance(s, str) for s in spans):
                issues.append(INVALID_SOURCE_SPAN_IDS)

            # Check NaN/Inf in claim values
            for field_name in ("raw_value", "normalized_value"):
                val = claim.get(field_name)
                if val is not None and _has_non_finite(val):
                    issues.append(NON_FINITE_VALUE)

            # Check metadata for forbidden keys
            meta = claim.get("metadata")
            if isinstance(meta, dict):
                for meta_key, reason_code in FORBIDDEN_METADATA_KEYS.items():
                    if meta_key in meta:
                        issues.append(reason_code)

    # Check NaN/Inf in top-level non-claim fields
    for key in ("verification_request", "metadata"):
        val = payload.get(key)
        if val is not None and _has_non_finite(val):
            issues.append(NON_FINITE_VALUE)

    if issues:
        return _invalid(issues, proposal_kind=proposal_kind, candidate_kind=candidate_kind)

    # Build validated claims
    validated_claims = []
    for claim in raw_claims:  # type: ignore[union-attr]
        validated_claims.append(
            CandidateClaimProposal(
                claim_id=str(claim["claim_id"]),
                claim_type=str(claim["claim_type"]),
                status=str(claim["status"]),
                subject=str(claim["subject"]),
                predicate=str(claim["predicate"]),
                object=str(claim["object"]),
                source_span_ids=tuple(str(s) for s in claim["source_span_ids"]),
                raw_value=claim.get("raw_value"),
                normalized_value=claim.get("normalized_value"),
                metadata=dict(claim.get("metadata") or {}),
            )
        )

    return CandidateProposalValidationResult(
        status=PROPOSAL_VALID,
        accepted=True,
        proposal_kind=proposal_kind,
        candidate_kind=candidate_kind,
        claim_count=len(validated_claims),
        issues=(),
    )


def load_and_validate_candidate_proposal_json(
    raw: str | bytes,
) -> tuple[CandidateProposal | None, CandidateProposalValidationResult]:
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    if len(raw_bytes) > MAX_PROPOSAL_JSON_BYTES:
        result = CandidateProposalValidationResult(
            status=PROPOSAL_INVALID,
            accepted=False,
            proposal_kind=None,
            candidate_kind=None,
            claim_count=0,
            issues=(PAYLOAD_TOO_LARGE,),
        )
        return None, result

    try:
        payload = json.loads(raw_bytes, parse_constant=None)
    except json.JSONDecodeError as exc:
        result = CandidateProposalValidationResult(
            status=PROPOSAL_INVALID,
            accepted=False,
            proposal_kind=None,
            candidate_kind=None,
            claim_count=0,
            issues=(f"INVALID_JSON: {exc}",),
        )
        return None, result

    validation_result = validate_candidate_proposal_dict(payload)
    if not validation_result.accepted:
        return None, validation_result

    raw_claims = payload["claims"]
    claims = tuple(
        CandidateClaimProposal(
            claim_id=str(c["claim_id"]),
            claim_type=str(c["claim_type"]),
            status=str(c["status"]),
            subject=str(c["subject"]),
            predicate=str(c["predicate"]),
            object=str(c["object"]),
            source_span_ids=tuple(str(s) for s in c["source_span_ids"]),
            raw_value=c.get("raw_value"),
            normalized_value=c.get("normalized_value"),
            metadata=dict(c.get("metadata") or {}),
        )
        for c in raw_claims
    )

    proposal = CandidateProposal(
        proposal_version=str(payload["proposal_version"]),
        proposal_kind=str(payload["proposal_kind"]),
        candidate_kind=str(payload["candidate_kind"]),
        claims=claims,
        verification_request=dict(payload.get("verification_request") or {}),
        metadata=dict(payload.get("metadata") or {}),
    )
    return proposal, validation_result
