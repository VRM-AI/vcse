#!/usr/bin/env python3
"""Convert structured records to explicit VCSE triples using a mapping definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from vcse.schema.proposer import convert_rows_with_mapping


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
    explicit_rows = convert_rows_with_mapping(records, mapping)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in explicit_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(explicit_rows), len(records)


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
