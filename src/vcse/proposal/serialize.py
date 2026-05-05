"""Candidate Proposal deterministic serialization."""

from __future__ import annotations

import json
from typing import Any

from vcse.proposal.model import (
    CandidateProposalAdapterResult,
    CandidateProposalValidationResult,
)


def candidate_proposal_validation_result_to_dict(
    result: CandidateProposalValidationResult,
) -> dict[str, Any]:
    return {
        "status": result.status,
        "accepted": result.accepted,
        "proposal_kind": result.proposal_kind,
        "candidate_kind": result.candidate_kind,
        "claim_count": result.claim_count,
        "issues": list(result.issues),
    }


def candidate_proposal_validation_result_to_json(
    result: CandidateProposalValidationResult,
) -> str:
    return json.dumps(
        candidate_proposal_validation_result_to_dict(result),
        sort_keys=True,
        allow_nan=False,
    )


def candidate_proposal_adapter_result_to_dict(
    result: CandidateProposalAdapterResult,
) -> dict[str, Any]:
    return {
        "status": result.status,
        "claim_count": result.claim_count,
        "candidate_claims": list(result.candidate_claims),
        "issues": list(result.issues),
    }


def candidate_proposal_adapter_result_to_json(
    result: CandidateProposalAdapterResult,
) -> str:
    return json.dumps(
        candidate_proposal_adapter_result_to_dict(result),
        sort_keys=True,
        allow_nan=False,
    )
