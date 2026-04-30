from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "convert_to_explicit.py"
MAPPING = ROOT / "examples" / "converters" / "countries_mapping.json"
SAMPLE = ROOT / "examples" / "datasets" / "countries_sample.json"


def _run_convert(input_path: Path, output_path: Path, mapping_path: Path = MAPPING) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_path),
            "--mapping",
            str(mapping_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rows.append(json.loads(line))
    return rows


def test_conversion_script_runs_and_output_exists(tmp_path: Path) -> None:
    output = tmp_path / "countries_explicit.jsonl"
    completed = _run_convert(SAMPLE, output)
    assert output.exists()
    rows = _read_jsonl(output)
    assert len(rows) > 0
    assert "rows_generated=" in completed.stdout
    assert "input_records_processed=" in completed.stdout


def test_conversion_is_deterministic(tmp_path: Path) -> None:
    output_one = tmp_path / "first.jsonl"
    output_two = tmp_path / "second.jsonl"
    _run_convert(SAMPLE, output_one)
    _run_convert(SAMPLE, output_two)
    assert output_one.read_text(encoding="utf-8") == output_two.read_text(encoding="utf-8")


def test_mapping_paths_resolve_expected_values(tmp_path: Path) -> None:
    output = tmp_path / "countries_explicit.jsonl"
    _run_convert(SAMPLE, output)
    rows = _read_jsonl(output)
    row_set = {(row["subject"], row["relation"], row["object"]) for row in rows}
    assert ("France", "has_capital", "Paris") in row_set
    assert ("France", "uses_currency", "Euro") in row_set
    assert ("France", "language_of", "French") in row_set
    assert ("France", "shares_border_with", "DEU") in row_set


def test_missing_fields_are_skipped_safely(tmp_path: Path) -> None:
    broken_input = tmp_path / "broken.json"
    broken_input.write_text(
        json.dumps(
            [
                {
                    "name": {"common": "Nowhere"},
                    "capital": [],
                    "region": None,
                    "subregion": "",
                    "currencies": {},
                    "languages": {"eng": "English"},
                    "cca2": "NW",
                    "borders": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "broken_out.jsonl"
    _run_convert(broken_input, output)
    rows = _read_jsonl(output)
    assert rows == [
        {"subject": "Nowhere", "relation": "has_country_code", "object": "NW"},
        {"subject": "Nowhere", "relation": "language_of", "object": "English"},
    ]
