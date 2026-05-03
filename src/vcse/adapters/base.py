"""Base source adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from vcse.intake.source import SourceRef


@dataclass(frozen=True)
class ExtractedRow:
    row_id: str
    data: dict
    locator: str
    raw_value: str


class SourceAdapter(ABC):
    adapter_id: str = "base"
    supported_formats: tuple[str, ...] = tuple()

    @abstractmethod
    def load(self, path: Path) -> list[dict]:
        """Parse source input into raw records."""

    @abstractmethod
    def normalize(self, raw_records: list[dict]) -> list[dict]:
        """Shape raw records into normalized records."""

    def run(self, path: Path) -> list[dict]:
        raw = self.load(path)
        return self.normalize(raw)

    def extract(self, source: SourceRef) -> tuple[ExtractedRow, ...]:
        if not source.local_path:
            raise ValueError("SOURCE_NOT_LOCAL: adapter requires local path")
        rows = self.run(Path(source.local_path))
        extracted: list[ExtractedRow] = []
        for idx, row in enumerate(rows, start=1):
            extracted.append(
                ExtractedRow(
                    row_id=str(row.get("id", f"row_{idx}")),
                    data=dict(row),
                    locator=f"row:{idx}",
                    raw_value=str(row),
                )
            )
        return tuple(extracted)
