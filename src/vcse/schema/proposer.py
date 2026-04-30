from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from vcse.schema.model import MappingProposal, SchemaModel


RELATION_BY_FIELD: dict[str, str] = {
    "capital": "has_capital",
    "region": "located_in_region",
    "subregion": "located_in_subregion",
    "currencies": "uses_currency",
    "currency": "uses_currency",
    "languages": "language_of",
    "language": "language_of",
    "cca2": "has_country_code",
    "code": "has_country_code",
    "borders": "shares_border_with",
}

SUBJECT_PRIORITIES = ("name", "title", "label", "name.common")


def _parse_path(path: str) -> list[tuple[str, str | int | None]]:
    tokens: list[tuple[str, str | int | None]] = []
    parts = [p for p in path.split(".") if p]
    for part in parts:
        if part == "*":
            tokens.append(("wildcard_obj", None))
            continue
        if part.endswith("[*]"):
            name = part[:-3]
            if name:
                tokens.append(("field", name))
            tokens.append(("wildcard_list", None))
            continue
        if "[" in part and part.endswith("]"):
            left = part.index("[")
            name = part[:left]
            idx_text = part[left + 1 : -1]
            if not idx_text.isdigit():
                raise ValueError(f"Unsupported path token: {part}")
            if name:
                tokens.append(("field", name))
            tokens.append(("index", int(idx_text)))
            continue
        tokens.append(("field", part))
    return tokens


def _resolve_many(record: Any, path: str) -> list[Any]:
    values: list[Any] = [record]
    for token, token_value in _parse_path(path):
        next_values: list[Any] = []
        for value in values:
            if token == "field":
                if isinstance(value, dict) and token_value in value:
                    next_values.append(value[token_value])
            elif token == "index":
                if isinstance(value, list) and 0 <= int(token_value) < len(value):
                    next_values.append(value[int(token_value)])
            elif token == "wildcard_obj":
                if isinstance(value, dict):
                    next_values.extend(value.values())
            elif token == "wildcard_list":
                if isinstance(value, list):
                    next_values.extend(value)
        values = next_values
        if not values:
            break
    return values


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def convert_rows_with_mapping(rows: list[dict[str, Any]], mapping: dict[str, Any]) -> list[dict[str, str]]:
    subject_path = mapping["fields"]["subject"]
    relations = mapping.get("relations", [])
    triples: set[tuple[str, str, str]] = set()
    for record in rows:
        subject_values = _resolve_many(record, subject_path)
        subject = _as_text(subject_values[0]) if subject_values else None
        if not subject:
            continue
        for relation_spec in relations:
            relation = relation_spec["relation"]
            relation_type = relation_spec["type"]
            resolved = _resolve_many(record, relation_spec["path"])
            if relation_type == "single":
                obj = _as_text(resolved[0]) if resolved else None
                if obj:
                    triples.add((subject, relation, obj))
                continue
            if relation_type == "multi":
                for item in resolved:
                    obj = _as_text(item)
                    if obj:
                        triples.add((subject, relation, obj))
                continue
            raise ValueError(f"Unsupported relation type: {relation_type}")
    ordered = sorted(triples, key=lambda item: (item[0], item[1], item[2]))
    return [{"subject": s, "relation": r, "object": o} for s, r, o in ordered]


def write_mapping_artifact(source_file: Path, mapping: dict[str, Any]) -> Path:
    digest = sha256(source_file.read_bytes()).hexdigest()
    target = Path(".vcse") / "mappings" / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _best_subject(schema: SchemaModel) -> str | None:
    string_paths = [f.path for f in schema.fields if f.type in {"string", "number"}]
    string_set = set(string_paths)
    for preferred in SUBJECT_PRIORITIES:
        if preferred in string_set:
            return preferred
    for candidate in sorted(string_paths):
        return candidate
    return None


def _relation_entries(schema: SchemaModel, subject_path: str) -> tuple[list[dict[str, str]], list[str]]:
    relations: list[dict[str, str]] = []
    mapped_paths: set[str] = {subject_path}
    for field in sorted(schema.fields, key=lambda item: item.path):
        if field.path == subject_path:
            continue
        base = field.path.split(".")[0]
        relation = RELATION_BY_FIELD.get(base)
        if relation is None:
            continue
        mapping_path = field.path
        relation_type = "multi" if field.cardinality == "multi" else "single"
        if base in {"currencies", "currency"}:
            if mapping_path == "currencies":
                mapping_path = "currencies.*.name"
                relation_type = "multi"
            elif mapping_path.startswith("currencies."):
                mapping_path = "currencies.*.name"
                relation_type = "multi"
        elif base in {"languages", "language"}:
            if mapping_path == "languages":
                mapping_path = "languages.*"
                relation_type = "multi"
            elif mapping_path.startswith("languages."):
                mapping_path = "languages.*"
                relation_type = "multi"
        elif base == "capital" and mapping_path == "capital":
            mapping_path = "capital[0]"
            relation_type = "single"
        elif base == "borders" and mapping_path == "borders":
            mapping_path = "borders[*]"
            relation_type = "multi"
        if any(item["relation"] == relation and item["path"] == mapping_path for item in relations):
            continue
        relations.append({"relation": relation, "path": mapping_path, "type": relation_type})
        mapped_paths.add(field.path)
    ignored = sorted(path for path in (f.path for f in schema.fields) if path not in mapped_paths)
    relations.sort(key=lambda item: (item["relation"], item["path"]))
    return relations, ignored


class MappingProposer:
    def propose(self, schema: SchemaModel, source_type: str = "json") -> MappingProposal:
        subject = _best_subject(schema)
        if subject is None:
            raise ValueError("Unable to infer subject field from schema.")
        relations, ignored = _relation_entries(schema, subject)
        return MappingProposal(
            source_type=source_type,
            record_path="$",
            fields={"subject": subject},
            relations=relations,
            ignored_fields=ignored,
        )
