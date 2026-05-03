from __future__ import annotations

import hashlib
import json

from vcse.cmcf import claim_dict_to_cmcf
from vcse.cmcf.model import CMCFRecord
from vcse.intake.source import SourceRef
from vcse.profiles.base import SourceProfile


class HistoricalEventsProfile(SourceProfile):
    profile_id = "historical_events"

    def can_handle(self, rows: tuple[dict, ...]) -> bool:
        if not rows:
            return False
        for row in rows:
            keys = {str(key).lower() for key in row.keys()}
            has_date = "date" in keys or "event_date" in keys
            has_description = "description" in keys or "event" in keys
            if has_date and has_description:
                return True
        return False

    def to_cmcf(self, rows: tuple[dict, ...], source: SourceRef) -> tuple[CMCFRecord, ...]:
        records: list[CMCFRecord] = []
        for idx, row in enumerate(rows, start=1):
            date = self._pick(row, "date", "event_date")
            description = self._pick(row, "description", "event")
            if date is None or description is None:
                continue
            event_id = self._event_id(row)
            raw_value = json.dumps(row, sort_keys=True, ensure_ascii=False)
            records.append(self._record(event_id, "occurred_on", date, source, f"row:{idx}:date", raw_value))
            records.append(self._record(event_id, "has_description", description, source, f"row:{idx}:description", raw_value))
            category = self._pick(row, "category")
            language = self._pick(row, "lang", "language")
            if category is not None:
                records.append(self._record(event_id, "has_category", category, source, f"row:{idx}:category", raw_value))
            if language is not None:
                records.append(self._record(event_id, "has_language", language, source, f"row:{idx}:language", raw_value))
            records.append(self._record(event_id, "has_source_uri", source.uri, source, f"row:{idx}:source_uri", raw_value))
        return tuple(records)

    def _record(self, subject: str, relation: str, object_value: str, source: SourceRef, locator: str, raw_value: str) -> CMCFRecord:
        return claim_dict_to_cmcf(
            {"subject": subject, "relation": relation, "object": object_value},
            source_type=source.source_type,
            source_uri=source.uri,
            locator=locator,
            raw_value=raw_value,
        )

    def _pick(self, row: dict, *keys: str) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _event_id(self, row: dict) -> str:
        blob = json.dumps(row, sort_keys=True, ensure_ascii=False)
        return f"event:{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]}"
