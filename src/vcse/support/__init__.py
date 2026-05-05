"""Deterministic source support contracts for GSR-readiness."""

from vcse.support.model import (
    ActiveRelationView,
    CandidateClaimView,
    SourceSpan,
    SourceSupportDecision,
    FINAL_STATUS_SOURCE_SUPPORTED,
    FINAL_STATUS_SOURCE_SUPPORT_FAILED,
    FINAL_STATUS_GROUNDED,
    FINAL_STATUS_NEEDS_SOURCE,
    FINAL_STATUS_UNKNOWN_SOURCE_SPAN,
    FINAL_STATUS_NEEDS_ONTOLOGY,
    FINAL_STATUS_INVALID_ONTOLOGY_RELATION,
    FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE,
)
from vcse.support.profiles import (
    SUPPORT_EXACT,
    SUPPORT_NORMALIZED,
    SUPPORT_RULE_DERIVED,
    SUPPORT_AGENT_PROPOSED,
    EXPLORATORY_SUPPORT_PROFILE,
    KNOWN_PROFILES,
)
from vcse.support.service import evaluate_source_support
from vcse.support.serialize import source_support_decision_to_dict, source_support_decision_to_json

__all__ = [
    "ActiveRelationView",
    "CandidateClaimView",
    "SourceSpan",
    "SourceSupportDecision",
    "FINAL_STATUS_SOURCE_SUPPORTED",
    "FINAL_STATUS_SOURCE_SUPPORT_FAILED",
    "FINAL_STATUS_GROUNDED",
    "FINAL_STATUS_NEEDS_SOURCE",
    "FINAL_STATUS_UNKNOWN_SOURCE_SPAN",
    "FINAL_STATUS_NEEDS_ONTOLOGY",
    "FINAL_STATUS_INVALID_ONTOLOGY_RELATION",
    "FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE",
    "SUPPORT_EXACT",
    "SUPPORT_NORMALIZED",
    "SUPPORT_RULE_DERIVED",
    "SUPPORT_AGENT_PROPOSED",
    "EXPLORATORY_SUPPORT_PROFILE",
    "KNOWN_PROFILES",
    "evaluate_source_support",
    "source_support_decision_to_dict",
    "source_support_decision_to_json",
]
