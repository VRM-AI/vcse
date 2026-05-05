"""Deterministic serialization for ledger taxonomy events."""

from __future__ import annotations

import json
from typing import Any

from vcse.ledger.model import LedgerEvent, LedgerEventValidationResult


def ledger_event_to_dict(event: LedgerEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "timestamp": event.timestamp,
        "actor_type": event.actor_type,
        "source_system": event.source_system,
        "subject_kind": event.subject_kind,
        "final_status": event.final_status,
        "reason_code": event.reason_code,
        "severity": event.severity,
        "subject_id": event.subject_id,
        "claim_id": event.claim_id,
        "source_id": event.source_id,
        "source_span_ids": list(event.source_span_ids),
        "relation_id": event.relation_id,
        "ontology_version": event.ontology_version,
        "proposal_id": event.proposal_id,
        "request_id": event.request_id,
        "content_hash": event.content_hash,
        "details": dict(event.details),
    }


def ledger_event_to_json(event: LedgerEvent) -> str:
    return json.dumps(ledger_event_to_dict(event), sort_keys=True, allow_nan=False)


def ledger_event_validation_result_to_dict(result: LedgerEventValidationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "valid": result.valid,
        "event_type": result.event_type,
        "issue_count": result.issue_count,
        "issues": list(result.issues),
    }


def ledger_event_validation_result_to_json(result: LedgerEventValidationResult) -> str:
    return json.dumps(
        ledger_event_validation_result_to_dict(result),
        sort_keys=True,
        allow_nan=False,
    )
