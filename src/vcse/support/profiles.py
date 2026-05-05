"""Deterministic source support profile registry."""

from __future__ import annotations

import unicodedata
from typing import Mapping

from vcse.support.model import (
    ActiveRelationView,
    CandidateClaimView,
    SourceSpan,
    FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE,
    FINAL_STATUS_SOURCE_SUPPORTED,
    FINAL_STATUS_SOURCE_SUPPORT_FAILED,
    REASON_EXPLORATORY_ONLY,
    REASON_SUPPORT_PROFILE_FAILED,
    REASON_SUPPORT_PROFILE_PASSED,
    SourceSupportDecision,
)

SUPPORT_EXACT = "SUPPORT_EXACT"
SUPPORT_NORMALIZED = "SUPPORT_NORMALIZED"
SUPPORT_RULE_DERIVED = "SUPPORT_RULE_DERIVED"
SUPPORT_AGENT_PROPOSED = "SUPPORT_AGENT_PROPOSED"
EXPLORATORY_SUPPORT_PROFILE = "EXPLORATORY_SUPPORT_PROFILE"

KNOWN_PROFILES: frozenset[str] = frozenset({
    SUPPORT_EXACT,
    SUPPORT_NORMALIZED,
    SUPPORT_RULE_DERIVED,
    SUPPORT_AGENT_PROPOSED,
    EXPLORATORY_SUPPORT_PROFILE,
})


def _spans_for_claim(
    claim: CandidateClaimView,
    source_spans: Mapping[str, SourceSpan],
) -> list[SourceSpan]:
    return [source_spans[sid] for sid in claim.source_span_ids if sid in source_spans]


def _exact_check(term: str, text: str) -> bool:
    return bool(term) and term in text


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.casefold()
    s = " ".join(s.split())
    return s


def _normalized_check(term: str, text: str) -> bool:
    if not term:
        return False
    return _normalize(term) in _normalize(text)


def evaluate_profile(
    profile_id: str,
    claim: CandidateClaimView,
    source_spans: Mapping[str, SourceSpan],
    active_relation: ActiveRelationView,
) -> SourceSupportDecision:
    """
    Run a deterministic profile check. Returns a SourceSupportDecision with
    SOURCE_SUPPORTED or SOURCE_SUPPORT_FAILED (or EXPLORATORY_SUPPORT_CANDIDATE).

    Never emits VERIFIED or CERTIFIED.
    """
    spans = _spans_for_claim(claim, source_spans)

    if profile_id == SUPPORT_EXACT:
        passed = any(
            _exact_check(claim.subject, span.text) and _exact_check(claim.object, span.text)
            for span in spans
        )
        return SourceSupportDecision(
            supported=passed,
            final_status=FINAL_STATUS_SOURCE_SUPPORTED if passed else FINAL_STATUS_SOURCE_SUPPORT_FAILED,
            reason_code=REASON_SUPPORT_PROFILE_PASSED if passed else REASON_SUPPORT_PROFILE_FAILED,
            claim_id=claim.claim_id,
            relation_id=active_relation.relation_id,
            support_profile_id=profile_id,
            source_span_ids=claim.source_span_ids,
        )

    if profile_id == SUPPORT_NORMALIZED:
        passed = any(
            _normalized_check(claim.subject, span.text) and _normalized_check(claim.object, span.text)
            for span in spans
        )
        return SourceSupportDecision(
            supported=passed,
            final_status=FINAL_STATUS_SOURCE_SUPPORTED if passed else FINAL_STATUS_SOURCE_SUPPORT_FAILED,
            reason_code=REASON_SUPPORT_PROFILE_PASSED if passed else REASON_SUPPORT_PROFILE_FAILED,
            claim_id=claim.claim_id,
            relation_id=active_relation.relation_id,
            support_profile_id=profile_id,
            source_span_ids=claim.source_span_ids,
        )

    if profile_id == SUPPORT_RULE_DERIVED:
        # Skeleton: full rule-derived support requires future ontology/rule integration.
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_SOURCE_SUPPORT_FAILED,
            reason_code=REASON_SUPPORT_PROFILE_FAILED,
            claim_id=claim.claim_id,
            relation_id=active_relation.relation_id,
            support_profile_id=profile_id,
            source_span_ids=claim.source_span_ids,
            issues=("RULE_DERIVED_SUPPORT_REQUIRES_RULE_PROOF_INTEGRATION",),
        )

    if profile_id in (SUPPORT_AGENT_PROPOSED, EXPLORATORY_SUPPORT_PROFILE):
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE,
            reason_code=REASON_EXPLORATORY_ONLY,
            claim_id=claim.claim_id,
            relation_id=active_relation.relation_id,
            support_profile_id=profile_id,
            source_span_ids=claim.source_span_ids,
            issues=("support_profile_authoritative=false", "may_enter_vcse_knowledge=false"),
        )

    # Unknown profile — caller should have caught this before reaching here
    return SourceSupportDecision(
        supported=False,
        final_status=FINAL_STATUS_SOURCE_SUPPORT_FAILED,
        reason_code=REASON_SUPPORT_PROFILE_FAILED,
        claim_id=claim.claim_id,
        relation_id=active_relation.relation_id,
        support_profile_id=profile_id,
        source_span_ids=claim.source_span_ids,
        issues=(f"UNKNOWN_PROFILE: {profile_id}",),
    )
