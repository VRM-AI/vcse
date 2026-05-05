"""Ledger Event Taxonomy validation service."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from vcse.ledger.model import (
    FORBIDDEN_DETAIL_KEYS,
    KNOWN_ACTOR_TYPES,
    KNOWN_SEVERITIES,
    KNOWN_SUBJECT_KINDS,
    LEDGER_EVENT_INVALID,
    LEDGER_EVENT_VALID,
    LedgerEvent,
    LedgerEventValidationResult,
)
from vcse.ledger.taxonomy import is_known_event_type

_UPPER_SNAKE_RE = re.compile(r'^[A-Z][A-Z0-9_]*$')
_ISO_TIMESTAMP_RE = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$'
)

# Issue codes
MISSING_EVENT_ID = "MISSING_EVENT_ID"
MISSING_EVENT_TYPE = "MISSING_EVENT_TYPE"
UNKNOWN_EVENT_TYPE = "UNKNOWN_EVENT_TYPE"
MISSING_EVENT_VERSION = "MISSING_EVENT_VERSION"
MISSING_TIMESTAMP = "MISSING_TIMESTAMP"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
MISSING_ACTOR_TYPE = "MISSING_ACTOR_TYPE"
UNKNOWN_ACTOR_TYPE = "UNKNOWN_ACTOR_TYPE"
MISSING_SOURCE_SYSTEM = "MISSING_SOURCE_SYSTEM"
MISSING_SUBJECT_KIND = "MISSING_SUBJECT_KIND"
UNKNOWN_SUBJECT_KIND = "UNKNOWN_SUBJECT_KIND"
MISSING_FINAL_STATUS = "MISSING_FINAL_STATUS"
MISSING_REASON_CODE = "MISSING_REASON_CODE"
MISSING_SEVERITY = "MISSING_SEVERITY"
UNKNOWN_SEVERITY = "UNKNOWN_SEVERITY"
STATUS_CASING_INVALID = "STATUS_CASING_INVALID"
REASON_CODE_CASING_INVALID = "REASON_CODE_CASING_INVALID"
EVENT_TYPE_CASING_INVALID = "EVENT_TYPE_CASING_INVALID"
NON_FINITE_VALUE = "NON_FINITE_VALUE"
DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN = "DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN"


def _is_upper_snake(value: str) -> bool:
    return bool(_UPPER_SNAKE_RE.match(value))


def _is_valid_timestamp(value: str) -> bool:
    return bool(_ISO_TIMESTAMP_RE.match(value))


def _has_non_finite(value: Any) -> bool:
    if isinstance(value, float) and not math.isfinite(value):
        return True
    if isinstance(value, dict):
        return any(_has_non_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_non_finite(v) for v in value)
    return False


def validate_ledger_event(event: LedgerEvent) -> LedgerEventValidationResult:
    issues: list[str] = []

    if not event.event_id:
        issues.append(MISSING_EVENT_ID)

    resolved_event_type: str | None = None
    if not event.event_type:
        issues.append(MISSING_EVENT_TYPE)
    else:
        resolved_event_type = event.event_type
        if event.event_type != event.event_type.upper() or not _is_upper_snake(event.event_type):
            issues.append(EVENT_TYPE_CASING_INVALID)
            resolved_event_type = None
        elif not is_known_event_type(event.event_type):
            issues.append(UNKNOWN_EVENT_TYPE)
            resolved_event_type = None

    if not event.event_version:
        issues.append(MISSING_EVENT_VERSION)

    if not event.timestamp:
        issues.append(MISSING_TIMESTAMP)
    elif not _is_valid_timestamp(event.timestamp):
        issues.append(INVALID_TIMESTAMP)

    if not event.actor_type:
        issues.append(MISSING_ACTOR_TYPE)
    elif event.actor_type not in KNOWN_ACTOR_TYPES:
        issues.append(UNKNOWN_ACTOR_TYPE)

    if not event.source_system:
        issues.append(MISSING_SOURCE_SYSTEM)

    if not event.subject_kind:
        issues.append(MISSING_SUBJECT_KIND)
    elif event.subject_kind not in KNOWN_SUBJECT_KINDS:
        issues.append(UNKNOWN_SUBJECT_KIND)

    if not event.final_status:
        issues.append(MISSING_FINAL_STATUS)
    elif not _is_upper_snake(event.final_status):
        issues.append(STATUS_CASING_INVALID)

    if not event.reason_code:
        issues.append(MISSING_REASON_CODE)
    elif not _is_upper_snake(event.reason_code):
        issues.append(REASON_CODE_CASING_INVALID)

    if not event.severity:
        issues.append(MISSING_SEVERITY)
    elif event.severity not in KNOWN_SEVERITIES:
        issues.append(UNKNOWN_SEVERITY)

    if event.details:
        if _has_non_finite(event.details):
            issues.append(NON_FINITE_VALUE)
        for forbidden_key in FORBIDDEN_DETAIL_KEYS:
            if forbidden_key in event.details:
                issues.append(DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN)
                break

    valid = len(issues) == 0
    return LedgerEventValidationResult(
        status=LEDGER_EVENT_VALID if valid else LEDGER_EVENT_INVALID,
        valid=valid,
        event_type=resolved_event_type if valid else None,
        issue_count=len(issues),
        issues=tuple(issues),
    )


def validate_ledger_event_dict(payload: Mapping[str, Any]) -> LedgerEventValidationResult:
    issues: list[str] = []

    event_id = str(payload.get("event_id") or "")
    event_type = str(payload.get("event_type") or "")
    event_version = str(payload.get("event_version") or "")
    timestamp = str(payload.get("timestamp") or "")
    actor_type = str(payload.get("actor_type") or "")
    source_system = str(payload.get("source_system") or "")
    subject_kind = str(payload.get("subject_kind") or "")
    final_status = str(payload.get("final_status") or "")
    reason_code = str(payload.get("reason_code") or "")
    severity = str(payload.get("severity") or "")
    details = payload.get("details") or {}

    raw_source_span_ids = payload.get("source_span_ids") or []
    source_span_ids: tuple[str, ...] = tuple(str(s) for s in raw_source_span_ids)

    try:
        event = LedgerEvent(
            event_id=event_id,
            event_type=event_type,
            event_version=event_version,
            timestamp=timestamp,
            actor_type=actor_type,
            source_system=source_system,
            subject_kind=subject_kind,
            final_status=final_status,
            reason_code=reason_code,
            severity=severity,
            subject_id=payload.get("subject_id"),
            claim_id=payload.get("claim_id"),
            source_id=payload.get("source_id"),
            source_span_ids=source_span_ids,
            relation_id=payload.get("relation_id"),
            ontology_version=payload.get("ontology_version"),
            proposal_id=payload.get("proposal_id"),
            request_id=payload.get("request_id"),
            content_hash=payload.get("content_hash"),
            details=dict(details) if isinstance(details, dict) else {},
        )
    except Exception:
        issues.append(MISSING_EVENT_ID)
        return LedgerEventValidationResult(
            status=LEDGER_EVENT_INVALID,
            valid=False,
            event_type=None,
            issue_count=len(issues),
            issues=tuple(issues),
        )

    return validate_ledger_event(event)
