"""Deterministic explanation layer models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationNode:
    node_id: str
    node_type: str
    message: str
    subject: str | None = None
    relation: str | None = None
    object: str | None = None
    pack_id: str | None = None
    claim_id: str | None = None
    trust_tier: int | None = None
    lifecycle_status: str | None = None
    provenance: str | None = None
    verification_status: str | None = None
    policy_id: str | None = None
    policy_decision: str | None = None
    conflict_status: str | None = None


@dataclass(frozen=True)
class ProofTrace:
    trace_id: str
    result_subject: str
    result_relation: str
    result_object: str
    verification_status: str
    proof_count: int
    nodes: tuple[ExplanationNode, ...]
    summary: str


@dataclass(frozen=True)
class ExplanationResult:
    status: str
    traces: tuple[ProofTrace, ...]
    trace_count: int
