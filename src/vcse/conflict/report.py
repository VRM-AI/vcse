"""Conflict workflow report builder + serialization."""

from __future__ import annotations

from typing import Any, Iterable

from vcse.conflict.impact import analyze_conflict_impact
from vcse.conflict.resolution import generate_resolution_options
from vcse.conflict.workflow import (
    CONFLICT_WORKFLOW_COMPLETE,
    CONFLICT_WORKFLOW_NO_CONFLICTS,
    ConflictImpact,
    ConflictRef,
    ConflictWorkflowReport,
    ResolutionOption,
)
from vcse.proof.model import ProofIndex


def build_conflict_workflow_report(
    conflicts: Iterable[ConflictRef],
    proof_index: ProofIndex | None = None,
) -> ConflictWorkflowReport:
    conflict_list = sorted(conflicts, key=lambda item: item.conflict_id)
    if not conflict_list:
        return ConflictWorkflowReport(
            status=CONFLICT_WORKFLOW_NO_CONFLICTS,
            conflict_count=0,
            conflicts=(),
            impacts=(),
            options=(),
        )

    impacts = analyze_conflict_impact(conflict_list, proof_index)
    impact_lookup = {item.conflict_id: item for item in impacts}

    all_options: list[ResolutionOption] = []
    for conflict in conflict_list:
        all_options.extend(
            generate_resolution_options(conflict, impact_lookup.get(conflict.conflict_id))
        )
    options_sorted = tuple(sorted(all_options, key=lambda item: item.option_id))

    return ConflictWorkflowReport(
        status=CONFLICT_WORKFLOW_COMPLETE,
        conflict_count=len(conflict_list),
        conflicts=tuple(conflict_list),
        impacts=impacts,
        options=options_sorted,
    )


def _conflict_to_dict(conflict: ConflictRef) -> dict[str, Any]:
    return {
        "conflict_id": conflict.conflict_id,
        "subject": conflict.subject,
        "relation": conflict.relation,
        "object_a": conflict.object_a,
        "object_b": conflict.object_b,
        "claim_id_a": conflict.claim_id_a,
        "claim_id_b": conflict.claim_id_b,
        "pack_ids": list(conflict.pack_ids),
        "provenance_refs": list(conflict.provenance_refs),
        "reason": conflict.reason,
        "trust_tier_a": conflict.trust_tier_a,
        "trust_tier_b": conflict.trust_tier_b,
    }


def _impact_to_dict(impact: ConflictImpact) -> dict[str, Any]:
    return {
        "conflict_id": impact.conflict_id,
        "affected_claim_ids": list(impact.affected_claim_ids),
        "affected_proof_ids": list(impact.affected_proof_ids),
        "affected_result_claim_ids": list(impact.affected_result_claim_ids),
        "impact_score": impact.impact_score,
    }


def _option_to_dict(option: ResolutionOption) -> dict[str, Any]:
    return {
        "option_id": option.option_id,
        "conflict_id": option.conflict_id,
        "action": option.action,
        "selected_claim_id": option.selected_claim_id,
        "suppressed_claim_ids": list(option.suppressed_claim_ids),
        "rationale": option.rationale,
        "reversible": option.reversible,
    }


def conflict_workflow_report_to_dict(report: ConflictWorkflowReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "conflict_count": report.conflict_count,
        "conflicts": [_conflict_to_dict(item) for item in report.conflicts],
        "impacts": [_impact_to_dict(item) for item in report.impacts],
        "options": [_option_to_dict(item) for item in report.options],
    }
