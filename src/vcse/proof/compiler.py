"""Compile ProofIndex from CSRF runtime indexes or claim records."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from vcse.runtime.model import CSRFIndex, CSRFRecord
from vcse.proof.index import build_proof_index
from vcse.proof.model import ProofIndex, ProofPath, ProofStep


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _proof_id(result_claim_id: str, supporting_claim_ids: tuple[str, ...], steps: tuple[ProofStep, ...]) -> str:
    payload = {
        "result_claim_id": result_claim_id,
        "supporting_claim_ids": list(supporting_claim_ids),
        "steps": [
            {
                "claim_id": s.claim_id,
                "subject": s.subject,
                "relation": s.relation,
                "object": s.object,
                "pack_id": s.pack_id,
                "trust_tier": s.trust_tier,
                "verification_status": s.verification_status,
            }
            for s in steps
        ],
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _step_from_csrf(record: CSRFRecord) -> ProofStep:
    return ProofStep(
        claim_id=record.claim_id,
        subject=record.subject,
        relation=record.relation,
        object=record.object,
        pack_id=None,
        trust_tier=record.trust_tier,
        verification_status=record.verification_status,
    )


def _path_from_csrf_record(record: CSRFRecord) -> ProofPath:
    step = _step_from_csrf(record)
    supporting = (record.claim_id,)
    steps = (step,)
    return ProofPath(
        proof_id=_proof_id(record.claim_id, supporting, steps),
        result_claim_id=record.claim_id,
        result_subject=record.subject,
        result_relation=record.relation,
        result_object=record.object,
        supporting_claim_ids=supporting,
        steps=steps,
        path_length=1,
        trust_tier=record.trust_tier,
        verification_status=record.verification_status,
        source="materialized",
    )


def compile_proofs_from_csrf(csrf: CSRFIndex) -> ProofIndex:
    paths: list[ProofPath] = []
    for record in csrf.records:
        paths.append(_path_from_csrf_record(record))
    return build_proof_index(paths)


def _step_from_dict(step: dict[str, Any]) -> ProofStep:
    return ProofStep(
        claim_id=str(step.get("claim_id", "")),
        subject=str(step.get("subject", "")),
        relation=str(step.get("relation", "")),
        object=str(step.get("object", "")),
        pack_id=(str(step["pack_id"]) if step.get("pack_id") not in (None, "") else None),
        trust_tier=(int(step["trust_tier"]) if step.get("trust_tier") is not None else None),
        verification_status=(str(step["verification_status"]) if step.get("verification_status") else None),
    )


def _coerce_record_to_dict(record: Any) -> dict[str, Any] | None:
    if isinstance(record, dict):
        return record
    if isinstance(record, CSRFRecord):
        return {
            "claim_id": record.claim_id,
            "subject": record.subject,
            "relation": record.relation,
            "object": record.object,
            "trust_tier": record.trust_tier,
            "verification_status": record.verification_status,
        }
    # CMCFRecord
    claim = getattr(record, "claim", None)
    if claim is None:
        return None
    trust = getattr(record, "trust", None)
    status = getattr(record, "status", None)
    return {
        "claim_id": getattr(claim, "claim_id", ""),
        "subject": getattr(claim, "subject", ""),
        "relation": getattr(claim, "relation", ""),
        "object": getattr(claim, "object", ""),
        "trust_tier": getattr(trust, "trust_tier", 0) if trust is not None else 0,
        "verification_status": getattr(status, "verification_status", "UNVERIFIED") if status is not None else "UNVERIFIED",
    }


def _path_from_inferred_dict(record: dict[str, Any]) -> ProofPath | None:
    derived_from = record.get("derived_from")
    proofs = record.get("proofs")
    if not derived_from or not proofs:
        return None

    supporting_ids: list[str] = []
    for item in derived_from:
        if isinstance(item, dict):
            cid = str(item.get("claim_id", "")).strip()
            if cid:
                supporting_ids.append(cid)
    if not supporting_ids:
        return None

    steps: list[ProofStep] = []
    for proof in proofs:
        if not isinstance(proof, dict):
            continue
        steps.append(_step_from_dict(proof))
    if not steps:
        return None

    result_claim_id = str(record.get("claim_id", "")).strip()
    if not result_claim_id:
        return None
    subject = str(record.get("subject", ""))
    relation = str(record.get("relation", ""))
    obj = str(record.get("object", ""))
    trust_tier = int(record.get("trust_tier", 0) or 0)
    verification_status = str(record.get("verification_status", "UNVERIFIED"))

    supporting_tuple = tuple(supporting_ids)
    steps_tuple = tuple(steps)
    return ProofPath(
        proof_id=_proof_id(result_claim_id, supporting_tuple, steps_tuple),
        result_claim_id=result_claim_id,
        result_subject=subject,
        result_relation=relation,
        result_object=obj,
        supporting_claim_ids=supporting_tuple,
        steps=steps_tuple,
        path_length=len(supporting_tuple),
        trust_tier=trust_tier,
        verification_status=verification_status,
        source="reasoning",
    )


def _path_from_direct_dict(record: dict[str, Any]) -> ProofPath | None:
    claim_id = str(record.get("claim_id", "")).strip()
    if not claim_id:
        return None
    subject = str(record.get("subject", ""))
    relation = str(record.get("relation", ""))
    obj = str(record.get("object", ""))
    if not subject or not relation or not obj:
        return None
    trust_tier = int(record.get("trust_tier", 0) or 0)
    verification_status = str(record.get("verification_status", "UNVERIFIED"))
    pack_id = record.get("pack_id")
    pack_id_str = str(pack_id) if pack_id not in (None, "") else None

    step = ProofStep(
        claim_id=claim_id,
        subject=subject,
        relation=relation,
        object=obj,
        pack_id=pack_id_str,
        trust_tier=trust_tier,
        verification_status=verification_status,
    )
    supporting = (claim_id,)
    steps = (step,)
    return ProofPath(
        proof_id=_proof_id(claim_id, supporting, steps),
        result_claim_id=claim_id,
        result_subject=subject,
        result_relation=relation,
        result_object=obj,
        supporting_claim_ids=supporting,
        steps=steps,
        path_length=1,
        trust_tier=trust_tier,
        verification_status=verification_status,
        source="materialized",
    )


def compile_proofs_from_records(records: Iterable[Any]) -> ProofIndex:
    paths: list[ProofPath] = []
    for raw in records:
        record = _coerce_record_to_dict(raw)
        if record is None:
            continue
        inferred_path = _path_from_inferred_dict(record)
        if inferred_path is not None:
            paths.append(inferred_path)
            continue
        direct = _path_from_direct_dict(record)
        if direct is not None:
            paths.append(direct)
    return build_proof_index(paths)
