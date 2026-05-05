"""JSONL writer for ledger taxonomy events."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from vcse.ledger.model import LEDGER_EVENT_VALID
from vcse.ledger.serialize import ledger_event_to_json
from vcse.ledger.validate import validate_ledger_event

try:
    from vcse.ledger.model import LedgerEvent
except ImportError:
    raise


def write_ledger_events_jsonl(
    events: Iterable[LedgerEvent],
    path: Path,
    *,
    validate: bool = True,
) -> int:
    """Write validated ledger events to a JSONL file. Returns count written."""
    lines: list[str] = []
    for event in events:
        if validate:
            result = validate_ledger_event(event)
            if result.status != LEDGER_EVENT_VALID:
                raise ValueError(
                    f"Invalid ledger event {event.event_id!r}: {result.issues}"
                )
        lines.append(ledger_event_to_json(event))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)
