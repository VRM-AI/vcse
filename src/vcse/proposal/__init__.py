"""Candidate Proposal Contract — external input safety boundary."""

from vcse.proposal.model import (
    CANDIDATE_ACCEPTED,
    CANDIDATE_PROPOSAL,
    CANDIDATE_REJECTED,
    FACTUAL_CLAIM_PACK,
    MAX_PROPOSAL_JSON_BYTES,
    PROPOSAL_INVALID,
    PROPOSAL_VALID,
    PROPOSED,
    VCSE_EVALUATED,
    CandidateClaimProposal,
    CandidateProposal,
    CandidateProposalAdapterResult,
    CandidateProposalValidationResult,
)

__all__ = [
    "CANDIDATE_ACCEPTED",
    "CANDIDATE_PROPOSAL",
    "CANDIDATE_REJECTED",
    "FACTUAL_CLAIM_PACK",
    "MAX_PROPOSAL_JSON_BYTES",
    "PROPOSAL_INVALID",
    "PROPOSAL_VALID",
    "PROPOSED",
    "VCSE_EVALUATED",
    "CandidateClaimProposal",
    "CandidateProposal",
    "CandidateProposalAdapterResult",
    "CandidateProposalValidationResult",
]
