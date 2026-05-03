"""HTML table source adapter."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from vcse.adapters.base import SourceAdapter
from vcse.adapters.json_adapter import _normalize_value


class _FirstTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.done = False
        self.in_tr = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        t = tag.lower()
        if t == "table" and not self.in_table:
            self.in_table = True
            return
        if not self.in_table:
            return
        if t == "tr":
            self.in_tr = True
            self.current_row = []
        elif t in {"th", "td"} and self.in_tr:
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_table and self.in_tr and self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.done:
            return
        t = tag.lower()
        if t in {"th", "td"} and self.in_cell:
            self.in_cell = False
            self.current_row.append("".join(self.current_cell).strip())
        elif t == "tr" and self.in_tr:
            self.in_tr = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif t == "table" and self.in_table:
            self.in_table = False
            self.done = True


class HTMLTableAdapter(SourceAdapter):
    adapter_id = "html_table_adapter"
    supported_formats = ("html_table",)

    def load(self, path: Path) -> list[dict]:
        parser = _FirstTableParser()
        parser.feed(Path(path).read_text(errors="ignore"))
        if not parser.rows:
            return []
        header = parser.rows[0]
        if not header:
            return []
        rows: list[dict] = []
        for values in parser.rows[1:]:
            row = {header[idx]: values[idx] if idx < len(values) else "" for idx in range(len(header))}
            rows.append(row)
        return rows

    def normalize(self, raw_records: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for idx, record in enumerate(raw_records, start=1):
            row = {str(key): _normalize_value(value) for key, value in record.items()}
            row["id"] = f"row_{idx}"
            normalized.append(row)
        return normalized
