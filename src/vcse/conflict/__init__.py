"""Conflict detection and workflow primitives."""

from vcse.conflict.detector import ConflictDetector
from vcse.conflict.model import Conflict
from vcse.conflict.workflow import (
    CONFLICT_WORKFLOW_COMPLETE,
    CONFLICT_WORKFLOW_FAILED,
    CONFLICT_WORKFLOW_NO_CONFLICTS,
    ConflictImpact,
    ConflictRef,
    ConflictWorkflowReport,
    ResolutionOption,
    compute_conflict_id,
    conflict_to_ref,
    derive_refs_from_claims,
)

__all__ = [
    "Conflict",
    "ConflictDetector",
    "ConflictRef",
    "ConflictImpact",
    "ResolutionOption",
    "ConflictWorkflowReport",
    "compute_conflict_id",
    "conflict_to_ref",
    "derive_refs_from_claims",
    "CONFLICT_WORKFLOW_COMPLETE",
    "CONFLICT_WORKFLOW_NO_CONFLICTS",
    "CONFLICT_WORKFLOW_FAILED",
]
