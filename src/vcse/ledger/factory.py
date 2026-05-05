"""Ledger Event Taxonomy factory helpers — create event objects only, no side effects."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from vcse.ledger.model import LedgerEvent
from vcse.ledger.taxonomy import (
    CLAIM_SOURCE_SUPPORT_BLOCKED,
    CLAIM_SOURCE_SUPPORTED,
    ONTOLOGY_RELATION_VALIDATED,
    PROPOSAL_REJECTED,
    PROPOSAL_VALIDATED,
)

_DEFAULT_EVENT_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_event_id(event_type: str, timestamp: str) -> str:
    raw = f"{event_type}:{timestamp}"
    return "ev-" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def make_ledger_event(
    *,
    event_type: str,
    final_status: str,
    reason_code: str,
    actor_type: str = "SYSTEM",
    source_system: str = "VCSE",
    subject_kind: str = "UNKNOWN",
    severity: str = "INFO",
    subject_id: str | None = None,
    claim_id: str | None = None,
    source_id: str | None = None,
    source_span_ids: tuple[str, ...] = (),
    relation_id: str | None = None,
    ontology_version: str | None = None,
    proposal_id: str | None = None,
    request_id: str | None = None,
    content_hash: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> LedgerEvent:
    timestamp = _utc_now()
    event_id = _make_event_id(event_type, timestamp)
    return LedgerEvent(
        event_id=event_id,
        event_type=event_type,
        event_version=_DEFAULT_EVENT_VERSION,
        timestamp=timestamp,
        actor_type=actor_type,
        source_system=source_system,
        subject_kind=subject_kind,
        final_status=final_status,
        reason_code=reason_code,
        severity=severity,
        subject_id=subject_id,
        claim_id=claim_id,
        source_id=source_id,
        source_span_ids=source_span_ids,
        relation_id=relation_id,
        ontology_version=ontology_version,
        proposal_id=proposal_id,
        request_id=request_id,
        content_hash=content_hash,
        details=dict(details) if details is not None else {},
    )


def event_from_proposal_validation(
    result: Any,
    *,
    proposal_id: str | None = None,
    actor_type: str = "SYSTEM",
    source_system: str = "VCSE",
) -> LedgerEvent:
    """Adapt a proposal validation result to a ledger event. Does not mutate result."""
    accepted = getattr(result, "accepted", False)
    event_type = PROPOSAL_VALIDATED if accepted else PROPOSAL_REJECTED
    final_status = "PROPOSAL_ACCEPTED" if accepted else "PROPOSAL_REJECTED"
    reason_code = "PROPOSAL_ACCEPTED_AS_CANDIDATE" if accepted else "PROPOSAL_VALIDATION_FAILED"
    return make_ledger_event(
        event_type=event_type,
        final_status=final_status,
        reason_code=reason_code,
        actor_type=actor_type,
        source_system=source_system,
        subject_kind="PROPOSAL",
        proposal_id=proposal_id,
        details={"claim_count": getattr(result, "claim_count", 0)},
    )


def event_from_source_support_decision(
    decision: Any,
    *,
    claim_id: str | None = None,
    actor_type: str = "SYSTEM",
    source_system: str = "VCSE",
) -> LedgerEvent:
    """Adapt a source support decision to a ledger event. Does not mutate decision."""
    supported = getattr(decision, "supported", False)
    event_type = CLAIM_SOURCE_SUPPORTED if supported else CLAIM_SOURCE_SUPPORT_BLOCKED
    return make_ledger_event(
        event_type=event_type,
        final_status=getattr(decision, "final_status", "UNKNOWN"),
        reason_code=getattr(decision, "reason_code", "UNKNOWN"),
        actor_type=actor_type,
        source_system=source_system,
        subject_kind="CLAIM",
        claim_id=claim_id,
    )


def event_from_ontology_validation(
    result: Any,
    *,
    relation_id: str | None = None,
    ontology_version: str | None = None,
    actor_type: str = "SYSTEM",
    source_system: str = "VCSE",
) -> LedgerEvent:
    """Adapt an ontology validation result to a ledger event. Does not mutate result."""
    return make_ledger_event(
        event_type=ONTOLOGY_RELATION_VALIDATED,
        final_status="ONTOLOGY_VALIDATED",
        reason_code="ONTOLOGY_RELATION_VALID",
        actor_type=actor_type,
        source_system=source_system,
        subject_kind="ONTOLOGY_RELATION",
        relation_id=relation_id,
        ontology_version=ontology_version,
    )
