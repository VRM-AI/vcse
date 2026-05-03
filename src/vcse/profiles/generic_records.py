from __future__ import annotations

import hashlib
import json

from vcse.cmcf import claim_dict_to_cmcf
from vcse.cmcf.model import CMCFRecord
from vcse.intake.source import SourceRef
from vcse.profiles.base import SourceProfile


class GenericRecordsProfile(SourceProfile):
    profile_id = "generic_records"

    def can_handle(self, rows: tuple[dict, ...]) -> bool:
        return True

    def to_cmcf(self, rows: tuple[dict, ...], source: SourceRef) -> tuple[CMCFRecord, ...]:
        records: list[CMCFRecord] = []
        for idx, row in enumerate(rows, start=1):
            subject = self._subject_for_row(row)
            for key, value in row.items():
                if value is None:
                    continue
                relation = f"has_{key}"
                if isinstance(value, dict):
                    for child_key, child_value in value.items():
                        if child_value is None:
                            continue
                        records.append(
                            self._build_record(
                                subject,
                                f"{relation}_{child_key}",
                                str(child_value),
                                source,
                                f"row:{idx}:{key}.{child_key}",
                                row,
                            )
                        )
                elif isinstance(value, list):
                    for pos, item in enumerate(value, start=1):
                        if item is None:
                            continue
                        records.append(
                            self._build_record(subject, relation, str(item), source, f"row:{idx}:{key}[{pos}]", row)
                        )
                else:
                    records.append(self._build_record(subject, relation, str(value), source, f"row:{idx}:{key}", row))
        return tuple(records)

    def _build_record(
        self,
        subject: str,
        relation: str,
        object_value: str,
        source: SourceRef,
        locator: str,
        row: dict,
    ) -> CMCFRecord:
        return claim_dict_to_cmcf(
            {"subject": subject, "relation": relation, "object": object_value},
            source_type=source.source_type,
            source_uri=source.uri,
            locator=locator,
            raw_value=json.dumps(row, sort_keys=True, ensure_ascii=False),
        )

    def _subject_for_row(self, row: dict) -> str:
        for key in ("id", "name", "title"):
            value = row.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        blob = json.dumps(row, sort_keys=True, ensure_ascii=False)
        return f"row:{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]}"
