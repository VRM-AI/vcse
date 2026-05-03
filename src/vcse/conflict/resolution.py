"""Deterministic conflict resolution option generation."""

from __future__ import annotations

import hashlib

from vcse.conflict.workflow import ConflictImpact, ConflictRef, ResolutionOption


_ACTIONS = ("keep_a", "keep_b", "mark_disputed", "require_review")


def _option_id(conflict_id: str, action: str) -> str:
    digest = hashlib.sha256(f"{conflict_id}|{action}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _trust_rationale(conflict: ConflictRef) -> str | None:
    if conflict.trust_tier_a is None or conflict.trust_tier_b is None:
        return None
    if conflict.trust_tier_a == conflict.trust_tier_b:
        return f"Both claims share trust_tier ({conflict.trust_tier_a}); maintainer review required."
    if conflict.trust_tier_a > conflict.trust_tier_b:
        return (
            f"Claim A has higher trust_tier ({conflict.trust_tier_a}) than Claim B "
            f"({conflict.trust_tier_b}); recommended_by_trust=keep_a."
        )
    return (
        f"Claim B has higher trust_tier ({conflict.trust_tier_b}) than Claim A "
        f"({conflict.trust_tier_a}); recommended_by_trust=keep_b."
    )


def generate_resolution_options(
    conflict: ConflictRef,
    impact: ConflictImpact | None = None,
) -> tuple[ResolutionOption, ...]:
    trust_note = _trust_rationale(conflict)
    impact_note = (
        f" Impact: {impact.impact_score} (proofs={len(impact.affected_proof_ids)}, "
        f"results={len(impact.affected_result_claim_ids)})."
        if impact is not None
        else ""
    )

    label_a = conflict.claim_id_a or conflict.object_a
    label_b = conflict.claim_id_b or conflict.object_b

    options: list[ResolutionOption] = []
    for action in _ACTIONS:
        if action == "keep_a":
            rationale = f"Select claim A ({label_a}); suppress claim B ({label_b})."
            selected = conflict.claim_id_a
            suppressed = tuple(cid for cid in (conflict.claim_id_b,) if cid)
        elif action == "keep_b":
            rationale = f"Select claim B ({label_b}); suppress claim A ({label_a})."
            selected = conflict.claim_id_b
            suppressed = tuple(cid for cid in (conflict.claim_id_a,) if cid)
        elif action == "mark_disputed":
            rationale = "Both claims remain candidates; marked disputed pending review."
            selected = None
            suppressed = ()
        else:  # require_review
            rationale = "Maintainer review required; no automatic resolution applied."
            selected = None
            suppressed = ()

        full_rationale = rationale + impact_note
        if trust_note and action in {"keep_a", "keep_b"}:
            full_rationale += f" {trust_note}"

        options.append(
            ResolutionOption(
                option_id=_option_id(conflict.conflict_id, action),
                conflict_id=conflict.conflict_id,
                action=action,
                selected_claim_id=selected,
                suppressed_claim_ids=suppressed,
                rationale=full_rationale,
                reversible=True,
            )
        )
    return tuple(sorted(options, key=lambda item: item.option_id))
