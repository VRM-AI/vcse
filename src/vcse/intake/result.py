from __future__ import annotations

from dataclasses import dataclass, field

from vcse.cmcf.model import CMCFRecord
from vcse.intake.source import SourceRef


@dataclass(frozen=True)
class IntakeResult:
    status: str
    source: SourceRef
    detected_format: str
    adapter_id: str | None
    profile_id: str | None
    row_count: int
    cmcf_record_count: int
    validation_issue_count: int
    records: tuple[CMCFRecord, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
