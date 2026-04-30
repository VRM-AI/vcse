#!/usr/bin/env python3
"""Convert structured records to explicit VCSE triples using a mapping definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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
        return value.strip() or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _records_from_source(source: Any, record_path: str) -> list[dict[str, Any]]:
    if record_path != "$":
        raise ValueError(f"Unsupported record_path: {record_path}")
    if not isinstance(source, list):
        raise ValueError("Expected a JSON array at record_path '$'.")
    return [item for item in source if isinstance(item, dict)]


def convert(input_path: Path, mapping_path: Path, output_path: Path) -> tuple[int, int]:
    source = _load_json(input_path)
    mapping = _load_json(mapping_path)

    if mapping.get("source_type") != "json":
        raise ValueError("Only mapping source_type 'json' is supported.")

    records = _records_from_source(source, mapping.get("record_path", "$"))
    subject_path = mapping["fields"]["subject"]
    relations = mapping.get("relations", [])

    triples: set[tuple[str, str, str]] = set()
    for record in records:
        subject_values = _resolve_many(record, subject_path)
        subject = _as_text(subject_values[0]) if subject_values else None
        if not subject:
            continue
        for relation_spec in relations:
            relation = relation_spec["relation"]
            relation_type = relation_spec["type"]
            resolved = _resolve_many(record, relation_spec["path"])
            if relation_type == "single":
                candidate = _as_text(resolved[0]) if resolved else None
                if candidate:
                    triples.add((subject, relation, candidate))
                continue
            if relation_type == "multi":
                for candidate_value in resolved:
                    candidate = _as_text(candidate_value)
                    if candidate:
                        triples.add((subject, relation, candidate))
                continue
            raise ValueError(f"Unsupported relation type: {relation_type}")

    sorted_triples = sorted(triples, key=lambda item: (item[0], item[1], item[2]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for subject, relation, obj in sorted_triples:
            handle.write(
                json.dumps(
                    {"subject": subject, "relation": relation, "object": obj},
                    ensure_ascii=False,
                )
                + "\n"
            )
    return len(sorted_triples), len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="examples/datasets/countries_sample.json",
        help="Path to source dataset JSON file.",
    )
    parser.add_argument(
        "--mapping",
        default="examples/converters/countries_mapping.json",
        help="Path to mapping definition JSON file.",
    )
    parser.add_argument(
        "--output",
        default="datasets/processed/countries_explicit.jsonl",
        help="Path to output JSONL file.",
    )
    args = parser.parse_args()

    rows_generated, input_records_processed = convert(
        Path(args.input),
        Path(args.mapping),
        Path(args.output),
    )
    print(f"rows_generated={rows_generated}")
    print(f"input_records_processed={input_records_processed}")


if __name__ == "__main__":
    main()
