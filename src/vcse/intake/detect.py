from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vcse.intake.source import SourceRef


@dataclass(frozen=True)
class FormatDetection:
    detected_format: str
    confidence: str


class FormatDetector:
    def detect(self, source: SourceRef) -> FormatDetection:
        if source.source_type == "directory":
            return FormatDetection(detected_format="directory", confidence="exact")

        ext = Path(source.original).suffix.lower()
        if ext == ".json":
            return FormatDetection("json", "exact")
        if ext == ".jsonl":
            return FormatDetection("jsonl", "exact")
        if ext == ".csv":
            return FormatDetection("csv", "exact")
        if ext in {".html", ".htm"}:
            return FormatDetection("html_table", "exact")

        content_type = (source.content_type or "").lower()
        if "jsonl" in content_type or "x-ndjson" in content_type:
            return FormatDetection("jsonl", "inferred")
        if "json" in content_type:
            return FormatDetection("json", "inferred")
        if "csv" in content_type:
            return FormatDetection("csv", "inferred")
        if "html" in content_type:
            return FormatDetection("html_table", "inferred")

        if source.local_path:
            raw = Path(source.local_path).read_text(errors="ignore")[:4096].lstrip()
            if raw.startswith("{") or raw.startswith("["):
                return FormatDetection("json", "inferred")
            if "<table" in raw.lower() and "</table>" in raw.lower():
                return FormatDetection("html_table", "inferred")
            if "\n" in raw:
                first_lines = [line for line in raw.splitlines() if line.strip()][:3]
                if first_lines and all(line.startswith("{") for line in first_lines):
                    return FormatDetection("jsonl", "inferred")
                if first_lines and "," in first_lines[0]:
                    return FormatDetection("csv", "inferred")

        return FormatDetection("unknown", "unknown")
