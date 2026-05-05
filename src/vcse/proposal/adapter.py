"""Candidate Proposal adapter — converts proposals to candidate claim views."""

from __future__ import annotations

from vcse.proposal.model import (
    CANDIDATE_ACCEPTED,
    CandidateProposal,
    CandidateProposalAdapterResult,
)


def proposal_to_candidate_claim_views(
    proposal: CandidateProposal,
) -> CandidateProposalAdapterResult:
    candidate_claims = tuple(
        {
            "claim_id": claim.claim_id,
            "claim_type": claim.claim_type,
            "status": CANDIDATE_ACCEPTED,
            "subject": claim.subject,
            "relation": claim.predicate,
            "object": claim.object,
            "source_span_ids": list(claim.source_span_ids),
            "raw_value": claim.raw_value,
            "normalized_value": claim.normalized_value,
        }
        for claim in proposal.claims
    )
    return CandidateProposalAdapterResult(
        status=CANDIDATE_ACCEPTED,
        claim_count=len(candidate_claims),
        candidate_claims=candidate_claims,
        issues=(),
    )
