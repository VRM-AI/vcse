from __future__ import annotations

from pathlib import Path
from typing import Any

from vcse.adapters import get_adapter
from vcse.schema.model import FieldSpec, SchemaModel


def _classify_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "unknown"


def _merge_types(existing: str, incoming: str) -> str:
    if existing == incoming:
        return existing
    if existing == "unknown":
        return incoming
    if incoming == "unknown":
        return existing
    return "dict" if "dict" in {existing, incoming} else "string"


def _collect(record: Any, prefix: str, sink: dict[str, dict[str, Any]]) -> None:
    if isinstance(record, dict):
        for key in sorted(record.keys()):
            path = f"{prefix}.{key}" if prefix else str(key)
            value = record[key]
            kind = _classify_scalar(value)
            slot = sink.setdefault(path, {"type": "unknown", "max_list_len": 0})
            slot["type"] = _merge_types(slot["type"], kind)
            if isinstance(value, list):
                slot["max_list_len"] = max(slot["max_list_len"], len(value))
                for item in value:
                    if isinstance(item, (dict, list)):
                        _collect(item, f"{path}[*]", sink)
            elif isinstance(value, dict):
                _collect(value, path, sink)
    elif isinstance(record, list):
        for item in record:
            _collect(item, f"{prefix}[*]" if prefix else "[*]", sink)


def _field_type(raw_type: str, path: str, sink_item: dict[str, Any]) -> tuple[str, str]:
    if raw_type == "number":
        return "number", "single"
    if raw_type == "dict":
        return "dict", "single"
    if raw_type == "list":
        return "dict", "multi"
    if raw_type == "string":
        if path.endswith("[*]"):
            return "list[string]", "multi"
        if sink_item.get("max_list_len", 0) > 0:
            return "list[string]", "multi"
        return "string", "single"
    return "string", "single"


class SchemaDetector:
    def detect_records(self, rows: list[dict[str, Any]]) -> SchemaModel:
        fields: dict[str, dict[str, Any]] = {}
        for row in rows:
            _collect(row, "", fields)
        field_specs: list[FieldSpec] = []
        for path in sorted(fields.keys()):
            ftype, cardinality = _field_type(fields[path]["type"], path, fields[path])
            field_specs.append(FieldSpec(path=path, type=ftype, cardinality=cardinality))
        return SchemaModel(record_type="list", fields=field_specs)

    def detect_file(self, source_file: Path) -> tuple[SchemaModel, list[dict[str, Any]], str]:
        adapter_type = source_file.suffix.lower().lstrip(".")
        adapter = get_adapter(adapter_type)
        rows = adapter.run(source_file)
        return self.detect_records(rows), rows, adapter_type
