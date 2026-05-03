"""Conflict workflow data models and identity helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from vcse.conflict.model import Conflict


CONFLICT_WORKFLOW_COMPLETE = "CONFLICT_WORKFLOW_COMPLETE"
CONFLICT_WORKFLOW_NO_CONFLICTS = "CONFLICT_WORKFLOW_NO_CONFLICTS"
CONFLICT_WORKFLOW_FAILED = "CONFLICT_WORKFLOW_FAILED"


@dataclass(frozen=True)
class ConflictRef:
    conflict_id: str
    subject: str
    relation: str
    object_a: str
    object_b: str
    claim_id_a: str | None = None
    claim_id_b: str | None = None
    pack_ids: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    reason: str = ""
    trust_tier_a: int | None = None
    trust_tier_b: int | None = None


@dataclass(frozen=True)
class ConflictImpact:
    conflict_id: str
    affected_claim_ids: tuple[str, ...]
    affected_proof_ids: tuple[str, ...]
    affected_result_claim_ids: tuple[str, ...]
    impact_score: int


@dataclass(frozen=True)
class ResolutionOption:
    option_id: str
    conflict_id: str
    action: str
    selected_claim_id: str | None
    suppressed_claim_ids: tuple[str, ...]
    rationale: str
    reversible: bool = True


@dataclass(frozen=True)
class ConflictWorkflowReport:
    status: str
    conflict_count: int
    conflicts: tuple[ConflictRef, ...]
    impacts: tuple[ConflictImpact, ...]
    options: tuple[ResolutionOption, ...]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def compute_conflict_id(
    subject: str,
    relation: str,
    object_a: str,
    object_b: str,
    claim_ids: Iterable[str | None] = (),
) -> str:
    sorted_objects = sorted([object_a, object_b])
    non_null_ids = sorted({cid for cid in claim_ids if cid})
    payload = {
        "subject": subject,
        "relation": relation,
        "object_a": sorted_objects[0],
        "object_b": sorted_objects[1],
        "claim_ids": list(non_null_ids),
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def conflict_to_ref(
    conflict: Conflict,
    *,
    claim_id_a: str | None = None,
    claim_id_b: str | None = None,
    trust_tier_a: int | None = None,
    trust_tier_b: int | None = None,
) -> ConflictRef:
    cid = compute_conflict_id(
        conflict.subject,
        conflict.relation,
        conflict.object_a,
        conflict.object_b,
        [claim_id_a, claim_id_b],
    )
    return ConflictRef(
        conflict_id=cid,
        subject=conflict.subject,
        relation=conflict.relation,
        object_a=conflict.object_a,
        object_b=conflict.object_b,
        claim_id_a=claim_id_a,
        claim_id_b=claim_id_b,
        pack_ids=tuple(conflict.pack_ids),
        provenance_refs=tuple(conflict.provenance_refs),
        reason=conflict.reason,
        trust_tier_a=trust_tier_a,
        trust_tier_b=trust_tier_b,
    )


def derive_refs_from_claims(
    conflicts: Iterable[Conflict],
    claims: Iterable[dict[str, Any]],
) -> tuple[ConflictRef, ...]:
    """Annotate Conflict instances with claim_ids/trust_tiers when available."""
    claim_lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for claim in claims:
        key = (
            str(claim.get("subject", "")),
            str(claim.get("relation", "")),
            str(claim.get("object", "")),
        )
        claim_lookup.setdefault(key, claim)
    refs: list[ConflictRef] = []
    for conflict in conflicts:
        a = claim_lookup.get((conflict.subject, conflict.relation, conflict.object_a))
        b = claim_lookup.get((conflict.subject, conflict.relation, conflict.object_b))
        refs.append(
            conflict_to_ref(
                conflict,
                claim_id_a=str(a.get("claim_id", "")) if a else None,
                claim_id_b=str(b.get("claim_id", "")) if b else None,
                trust_tier_a=int(a.get("trust_tier", 0)) if a else None,
                trust_tier_b=int(b.get("trust_tier", 0)) if b else None,
            )
        )
    return tuple(refs)
