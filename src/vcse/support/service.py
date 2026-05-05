"""Deterministic source support evaluation service."""

from __future__ import annotations

from typing import Mapping

from vcse.support.model import (
    ActiveRelationView,
    CandidateClaimView,
    SourceSpan,
    SourceSupportDecision,
    FINAL_STATUS_INVALID_ONTOLOGY_RELATION,
    FINAL_STATUS_NEEDS_ONTOLOGY,
    FINAL_STATUS_NEEDS_SOURCE,
    FINAL_STATUS_UNKNOWN_SOURCE_SPAN,
    REASON_INVALID_SUPPORT_PROFILE,
    REASON_MISSING_SOURCE_SPAN,
    REASON_MISSING_SUPPORT_PROFILE,
    REASON_RELATION_NOT_ACTIVE,
    REASON_UNKNOWN_SOURCE_SPAN,
)
from vcse.support.profiles import KNOWN_PROFILES, evaluate_profile


def evaluate_source_support(
    claim: CandidateClaimView,
    source_spans: Mapping[str, SourceSpan],
    active_relations: Mapping[str, ActiveRelationView],
) -> SourceSupportDecision:
    """
    Deterministically evaluate whether cited source spans support the claim.

    Invariants:
    - Never emits VERIFIED or CERTIFIED.
    - Never modifies inputs.
    - GROUNDED does not imply SOURCE_SUPPORTED.
    - SOURCE_SUPPORTED requires an active relation with a valid support profile.
    - Proposal-Agent / generative-model judgment cannot assign SOURCE_SUPPORTED.
    """
    # Step 1: missing source span ids
    if not claim.source_span_ids:
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_NEEDS_SOURCE,
            reason_code=REASON_MISSING_SOURCE_SPAN,
            claim_id=claim.claim_id,
            relation_id=claim.relation,
            support_profile_id=None,
            source_span_ids=(),
        )

    # Step 2: unknown source span ids
    unknown = [sid for sid in claim.source_span_ids if sid not in source_spans]
    if unknown:
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_UNKNOWN_SOURCE_SPAN,
            reason_code=REASON_UNKNOWN_SOURCE_SPAN,
            claim_id=claim.claim_id,
            relation_id=claim.relation,
            support_profile_id=None,
            source_span_ids=claim.source_span_ids,
            issues=tuple(f"unknown_span: {sid}" for sid in unknown),
        )

    # Step 3: relation not in active_relations
    if claim.relation not in active_relations:
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_NEEDS_ONTOLOGY,
            reason_code=REASON_RELATION_NOT_ACTIVE,
            claim_id=claim.claim_id,
            relation_id=claim.relation,
            support_profile_id=None,
            source_span_ids=claim.source_span_ids,
        )

    active_relation = active_relations[claim.relation]

    # Step 4: active relation has no support_profile_id
    if not active_relation.support_profile_id:
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_INVALID_ONTOLOGY_RELATION,
            reason_code=REASON_MISSING_SUPPORT_PROFILE,
            claim_id=claim.claim_id,
            relation_id=claim.relation,
            support_profile_id=None,
            source_span_ids=claim.source_span_ids,
        )

    # Step 5: unknown support_profile_id
    if active_relation.support_profile_id not in KNOWN_PROFILES:
        return SourceSupportDecision(
            supported=False,
            final_status=FINAL_STATUS_INVALID_ONTOLOGY_RELATION,
            reason_code=REASON_INVALID_SUPPORT_PROFILE,
            claim_id=claim.claim_id,
            relation_id=claim.relation,
            support_profile_id=active_relation.support_profile_id,
            source_span_ids=claim.source_span_ids,
            issues=(f"unknown_profile: {active_relation.support_profile_id}",),
        )

    # Steps 6–7: run profile check
    return evaluate_profile(
        active_relation.support_profile_id,
        claim,
        source_spans,
        active_relation,
    )
