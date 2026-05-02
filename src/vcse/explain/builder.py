"""Deterministic explanation builders."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from vcse.explain.model import ExplanationNode, ExplanationResult, ProofTrace

_STATUS_COMPLETE = "EXPLANATION_COMPLETE"
_STATUS_NO_TRACE = "EXPLANATION_NO_TRACE"


class ExplanationBuilder:
    def explain_claim(self, result: dict[str, Any]) -> ProofTrace:
        subject = str(result.get("subject", "")).strip()
        relation = str(result.get("relation", "")).strip()
        object_value = str(result.get("object", "")).strip()
        pack_id = _optional_str(result.get("pack_id"))
        claim_id = _optional_str(result.get("claim_id"))
        verification_status = self._resolve_explicit_verification_status(result)
        trace_id = _trace_id(subject, relation, object_value, pack_id, claim_id, verification_status)

        nodes: list[ExplanationNode] = []
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="result",
                sequence_index=len(nodes),
                message=f"{subject} {relation} {object_value}",
                subject=subject,
                relation=relation,
                object=object_value,
                pack_id=pack_id,
                claim_id=claim_id,
                verification_status=verification_status,
            )
        )
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="explicit_claim",
                sequence_index=len(nodes),
                message=f"explicit claim: {subject} {relation} {object_value}",
                subject=subject,
                relation=relation,
                object=object_value,
                pack_id=pack_id,
                claim_id=claim_id,
                trust_tier=_optional_int(result.get("trust_tier")),
                lifecycle_status=_optional_str(result.get("lifecycle_status")),
                verification_status=verification_status,
            )
        )
        provenance_text = _provenance_text(result.get("provenance"))
        if provenance_text is not None:
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="provenance",
                    sequence_index=len(nodes),
                    message=f"provenance: {provenance_text}",
                    provenance=provenance_text,
                )
            )
        if result.get("trust_tier") is not None:
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="trust",
                    sequence_index=len(nodes),
                    message=f"trust_tier: {result.get('trust_tier')}",
                    trust_tier=_optional_int(result.get("trust_tier")),
                )
            )
        if result.get("lifecycle_status") is not None:
            lifecycle_status = _optional_str(result.get("lifecycle_status"))
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="trust",
                    sequence_index=len(nodes),
                    message=f"lifecycle_status: {lifecycle_status}",
                    lifecycle_status=lifecycle_status,
                )
            )
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="verification",
                sequence_index=len(nodes),
                message=f"verification_status: {verification_status}",
                verification_status=verification_status,
            )
        )

        return ProofTrace(
            trace_id=trace_id,
            result_subject=subject,
            result_relation=relation,
            result_object=object_value,
            verification_status=verification_status,
            proof_count=0,
            nodes=tuple(nodes),
            summary=f"explicit claim explanation ({verification_status})",
        )

    def explain_inferred_claim(self, result: dict[str, Any]) -> ProofTrace:
        subject = str(result.get("subject", "")).strip()
        relation = str(result.get("relation", "")).strip()
        object_value = str(result.get("object", "")).strip()
        pack_id = _optional_str(result.get("pack_id"))
        claim_id = _optional_str(result.get("claim_id"))

        candidate_steps = _proof_steps(result)
        declared_proof_count = _optional_int(result.get("proof_count"))
        if declared_proof_count is None:
            proof_count = len(candidate_steps)
        else:
            proof_count = max(0, declared_proof_count)
        proofs = candidate_steps if proof_count > 0 else []
        source_status = _optional_str(result.get("verification_status"))
        verification_status = "UNVERIFIED"
        if source_status == "VERIFIED" and proof_count > 0:
            verification_status = "VERIFIED"
        elif source_status == "UNVERIFIED":
            verification_status = "UNVERIFIED"
        elif source_status == "FAILED":
            verification_status = "FAILED"

        trace_id = _trace_id(subject, relation, object_value, pack_id, claim_id, verification_status)
        nodes: list[ExplanationNode] = []
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="result",
                sequence_index=len(nodes),
                message=f"{subject} {relation} {object_value}",
                subject=subject,
                relation=relation,
                object=object_value,
                pack_id=pack_id,
                claim_id=claim_id,
                verification_status=verification_status,
            )
        )
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="inferred_claim",
                sequence_index=len(nodes),
                message=f"inferred claim: {subject} {relation} {object_value}",
                subject=subject,
                relation=relation,
                object=object_value,
                pack_id=pack_id,
                claim_id=claim_id,
                trust_tier=_optional_int(result.get("trust_tier")),
                verification_status=verification_status,
            )
        )

        if proof_count > 0:
            for step in proofs:
                nodes.append(
                    _node(
                        trace_id=trace_id,
                        node_type="proof_step",
                        sequence_index=len(nodes),
                        message=step["message"],
                        subject=step.get("subject"),
                        relation=step.get("relation"),
                        object=step.get("object"),
                        pack_id=step.get("pack_id"),
                        claim_id=step.get("claim_id"),
                    )
                )
            summary = f"inferred claim explanation with {proof_count} proof step(s)"
        else:
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="verification",
                    sequence_index=len(nodes),
                    message="no proof trace is available; result must not be treated as verified",
                    verification_status="UNVERIFIED",
                )
            )
            verification_status = "UNVERIFIED"
            summary = "no proof trace is available"

        if result.get("policy_id") is not None or result.get("policy_decision") is not None:
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="policy",
                    sequence_index=len(nodes),
                    message=(
                        f"policy: id={_optional_str(result.get('policy_id')) or 'unknown'} "
                        f"decision={_optional_str(result.get('policy_decision')) or 'unknown'}"
                    ),
                    policy_id=_optional_str(result.get("policy_id")),
                    policy_decision=_optional_str(result.get("policy_decision")),
                )
            )
        if result.get("conflict_status") is not None:
            nodes.append(
                _node(
                    trace_id=trace_id,
                    node_type="conflict",
                    sequence_index=len(nodes),
                    message=f"conflict_status: {_optional_str(result.get('conflict_status'))}",
                    conflict_status=_optional_str(result.get("conflict_status")),
                )
            )
        nodes.append(
            _node(
                trace_id=trace_id,
                node_type="verification",
                sequence_index=len(nodes),
                message=f"verification_status: {verification_status}",
                verification_status=verification_status,
            )
        )
        return ProofTrace(
            trace_id=trace_id,
            result_subject=subject,
            result_relation=relation,
            result_object=object_value,
            verification_status=verification_status,
            proof_count=proof_count,
            nodes=tuple(nodes),
            summary=summary,
        )

    def explain_query_results(self, results: Iterable[dict[str, Any]]) -> ExplanationResult:
        traces = [self.explain_claim(item) for item in _sorted_results(results)]
        if not traces:
            return ExplanationResult(status=_STATUS_NO_TRACE, traces=tuple(), trace_count=0)
        return ExplanationResult(status=_STATUS_COMPLETE, traces=tuple(traces), trace_count=len(traces))

    def explain_reasoning_results(self, results: Iterable[dict[str, Any]]) -> ExplanationResult:
        traces = [self.explain_inferred_claim(item) for item in _sorted_results(results)]
        if not traces:
            return ExplanationResult(status=_STATUS_NO_TRACE, traces=tuple(), trace_count=0)
        return ExplanationResult(status=_STATUS_COMPLETE, traces=tuple(traces), trace_count=len(traces))

    def _resolve_explicit_verification_status(self, result: dict[str, Any]) -> str:
        explicit = _optional_str(result.get("verification_status"))
        if explicit in {"VERIFIED", "UNVERIFIED", "FAILED"}:
            return explicit
        return "UNKNOWN"


def _sorted_results(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [item for item in results if isinstance(item, dict)]
    return sorted(
        rows,
        key=lambda item: (
            str(item.get("subject", "")),
            str(item.get("relation", "")),
            str(item.get("object", "")),
            str(item.get("pack_id", "")),
            str(item.get("claim_id", "")),
        ),
    )


def _proof_steps(result: dict[str, Any]) -> list[dict[str, str | None]]:
    proof_rows = result.get("proofs")
    if isinstance(proof_rows, list):
        items: list[dict[str, str | None]] = []
        for row in proof_rows:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    "subject": _optional_str(row.get("subject")),
                    "relation": _optional_str(row.get("relation")),
                    "object": _optional_str(row.get("object")),
                    "pack_id": _optional_str(row.get("pack_id")),
                    "claim_id": _optional_str(row.get("claim_id")),
                    "message": _proof_message_from_dict(row),
                }
            )
        return items

    derived_from = result.get("derived_from")
    if isinstance(derived_from, list) and derived_from:
        steps: list[dict[str, str | None]] = []
        for row in derived_from:
            if not isinstance(row, dict):
                continue
            pack_id = _optional_str(row.get("pack_id"))
            claim_id = _optional_str(row.get("claim_id"))
            steps.append(
                {
                    "subject": None,
                    "relation": None,
                    "object": None,
                    "pack_id": pack_id,
                    "claim_id": claim_id,
                    "message": f"derived from {pack_id or 'unknown'}:{claim_id or 'unknown'}",
                }
            )
        return steps

    proof_trace = result.get("proof_trace")
    if isinstance(proof_trace, list) and proof_trace:
        steps = []
        for value in proof_trace:
            text = str(value).strip()
            if not text:
                continue
            parts = text.split()
            subject = parts[0] if len(parts) >= 3 else None
            relation = parts[1] if len(parts) >= 3 else None
            object_value = " ".join(parts[2:]) if len(parts) >= 3 else None
            steps.append(
                {
                    "subject": subject,
                    "relation": relation,
                    "object": object_value,
                    "pack_id": None,
                    "claim_id": None,
                    "message": text,
                }
            )
        return steps
    return []


def _proof_message_from_dict(row: dict[str, Any]) -> str:
    subject = _optional_str(row.get("subject"))
    relation = _optional_str(row.get("relation"))
    object_value = _optional_str(row.get("object"))
    if subject and relation and object_value:
        return f"{subject} {relation} {object_value}"
    pack_id = _optional_str(row.get("pack_id"))
    claim_id = _optional_str(row.get("claim_id"))
    return f"derived from {pack_id or 'unknown'}:{claim_id or 'unknown'}"


def _trace_id(
    subject: str,
    relation: str,
    object_value: str,
    pack_id: str | None,
    claim_id: str | None,
    verification_status: str,
) -> str:
    payload = {
        "subject": subject,
        "relation": relation,
        "object": object_value,
        "pack_id": pack_id or "",
        "claim_id": claim_id or "",
        "verification_status": verification_status,
    }
    return _stable_hash(payload)


def _node(
    *,
    trace_id: str,
    node_type: str,
    sequence_index: int,
    message: str,
    subject: str | None = None,
    relation: str | None = None,
    object: str | None = None,
    pack_id: str | None = None,
    claim_id: str | None = None,
    trust_tier: int | None = None,
    lifecycle_status: str | None = None,
    provenance: str | None = None,
    verification_status: str | None = None,
    policy_id: str | None = None,
    policy_decision: str | None = None,
    conflict_status: str | None = None,
) -> ExplanationNode:
    payload = {
        "trace_id": trace_id,
        "node_type": node_type,
        "sequence_index": sequence_index,
        "claim_id": claim_id or "",
        "provenance": provenance or "",
        "message": message,
    }
    node_id = _stable_hash(payload)
    return ExplanationNode(
        node_id=node_id,
        node_type=node_type,
        message=message,
        subject=subject,
        relation=relation,
        object=object,
        pack_id=pack_id,
        claim_id=claim_id,
        trust_tier=trust_tier,
        lifecycle_status=lifecycle_status,
        provenance=provenance,
        verification_status=verification_status,
        policy_id=policy_id,
        policy_decision=policy_decision,
        conflict_status=conflict_status,
    )


def _stable_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if text.upper().startswith("T"):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return int(digits)
    return None


def _provenance_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)
