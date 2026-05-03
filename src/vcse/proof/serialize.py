"""Serialization for ProofIndex (.proof.json)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from vcse.proof.index import build_proof_index
from vcse.proof.model import ProofIndex, ProofPath, ProofStep


def _step_to_dict(step: ProofStep) -> dict[str, Any]:
    return {
        "claim_id": step.claim_id,
        "subject": step.subject,
        "relation": step.relation,
        "object": step.object,
        "pack_id": step.pack_id,
        "trust_tier": step.trust_tier,
        "verification_status": step.verification_status,
    }


def _path_to_dict(path: ProofPath) -> dict[str, Any]:
    return {
        "proof_id": path.proof_id,
        "result_claim_id": path.result_claim_id,
        "result_subject": path.result_subject,
        "result_relation": path.result_relation,
        "result_object": path.result_object,
        "supporting_claim_ids": list(path.supporting_claim_ids),
        "steps": [_step_to_dict(step) for step in path.steps],
        "path_length": path.path_length,
        "trust_tier": path.trust_tier,
        "verification_status": path.verification_status,
        "source": path.source,
    }


def proof_index_to_dict(index: ProofIndex) -> dict[str, Any]:
    return {
        "version": "1.0",
        "proofs": [_path_to_dict(path) for path in index.proofs],
        "by_result": {key: list(value) for key, value in sorted(index.by_result.items())},
        "by_support": {key: list(value) for key, value in sorted(index.by_support.items())},
        "by_subject": {key: list(value) for key, value in sorted(index.by_subject.items())},
        "by_relation": {key: list(value) for key, value in sorted(index.by_relation.items())},
        "by_object": {key: list(value) for key, value in sorted(index.by_object.items())},
    }


def _step_from_dict(payload: dict[str, Any]) -> ProofStep:
    return ProofStep(
        claim_id=str(payload.get("claim_id", "")),
        subject=str(payload.get("subject", "")),
        relation=str(payload.get("relation", "")),
        object=str(payload.get("object", "")),
        pack_id=(str(payload["pack_id"]) if payload.get("pack_id") not in (None, "") else None),
        trust_tier=(int(payload["trust_tier"]) if payload.get("trust_tier") is not None else None),
        verification_status=(str(payload["verification_status"]) if payload.get("verification_status") else None),
    )


def _path_from_dict(payload: dict[str, Any]) -> ProofPath:
    return ProofPath(
        proof_id=str(payload["proof_id"]),
        result_claim_id=str(payload["result_claim_id"]),
        result_subject=str(payload.get("result_subject", "")),
        result_relation=str(payload.get("result_relation", "")),
        result_object=str(payload.get("result_object", "")),
        supporting_claim_ids=tuple(str(x) for x in payload.get("supporting_claim_ids", [])),
        steps=tuple(_step_from_dict(step) for step in payload.get("steps", [])),
        path_length=int(payload.get("path_length", 0)),
        trust_tier=int(payload.get("trust_tier", 0)),
        verification_status=str(payload.get("verification_status", "UNVERIFIED")),
        source=str(payload.get("source", "materialized")),
    )


def proof_index_from_dict(payload: dict[str, Any]) -> ProofIndex:
    if not isinstance(payload, dict):
        raise ValueError("PROOF_INVALID_ROOT")
    paths = [_path_from_dict(item) for item in payload.get("proofs", [])]
    return build_proof_index(paths)


def save_proof_index(index: ProofIndex, path: Path) -> None:
    payload = proof_index_to_dict(index)
    _assert_json_safe(payload)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def _assert_json_safe(value: Any) -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN/Inf is not allowed in proof index")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("proof index keys must be strings")
            _assert_json_safe(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
