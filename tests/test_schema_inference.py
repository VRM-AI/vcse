from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from vcse.schema import MappingProposer, SchemaDetector, convert_rows_with_mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWN_MAPPING_PATH = REPO_ROOT / "examples" / "converters" / "countries_mapping.json"
SAMPLE_DATASET = REPO_ROOT / "examples" / "datasets" / "countries_sample.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vcse.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_countries_dataset_proposes_expected_mapping() -> None:
    rows = json.loads(SAMPLE_DATASET.read_text(encoding="utf-8"))
    schema = SchemaDetector().detect_records(rows)
    proposal = MappingProposer().propose(schema, source_type="json").to_dict()

    known = json.loads(KNOWN_MAPPING_PATH.read_text(encoding="utf-8"))
    assert proposal["fields"]["subject"] == known["fields"]["subject"]
    observed = {(item["relation"], item["path"], item["type"]) for item in proposal["relations"]}
    expected = {(item["relation"], item["path"], item["type"]) for item in known["relations"]}
    assert observed == expected


def test_mapping_proposal_is_deterministic_across_runs() -> None:
    rows = json.loads(SAMPLE_DATASET.read_text(encoding="utf-8"))
    detector = SchemaDetector()
    proposer = MappingProposer()

    mapping_one = proposer.propose(detector.detect_records(rows), source_type="json").to_dict()
    mapping_two = proposer.propose(detector.detect_records(rows), source_type="json").to_dict()
    assert mapping_one == mapping_two


def test_missing_fields_are_handled_safely() -> None:
    rows = [
        {"name": {"common": "X"}, "capital": [], "languages": {"eng": "English"}},
        {"name": {"common": "Y"}, "languages": {}},
    ]
    schema = SchemaDetector().detect_records(rows)
    mapping = MappingProposer().propose(schema, source_type="json").to_dict()
    explicit = convert_rows_with_mapping(rows, mapping)
    assert explicit == [{"subject": "X", "relation": "language_of", "object": "English"}]


def test_partial_dataset_still_produces_valid_mapping() -> None:
    rows = [{"title": "Doc A", "region": "Europe"}]
    schema = SchemaDetector().detect_records(rows)
    mapping = MappingProposer().propose(schema, source_type="json").to_dict()
    assert mapping["fields"]["subject"] == "title"
    assert any(item["relation"] == "located_in_region" for item in mapping["relations"])


def test_mapping_correctness_matches_known_conversion() -> None:
    rows = json.loads(SAMPLE_DATASET.read_text(encoding="utf-8"))
    inferred = MappingProposer().propose(SchemaDetector().detect_records(rows), source_type="json").to_dict()
    known = json.loads(KNOWN_MAPPING_PATH.read_text(encoding="utf-8"))
    out_inferred = convert_rows_with_mapping(rows, inferred)
    out_known = convert_rows_with_mapping(rows, known)
    assert out_inferred == out_known


def test_ingest_with_inference_requires_auto_approve(tmp_path: Path) -> None:
    source = tmp_path / "raw_countries.json"
    source.write_text(SAMPLE_DATASET.read_text(encoding="utf-8"), encoding="utf-8")
    denied = _run_cli("ingest", str(source), "--json")
    assert denied.returncode == 0
    payload = json.loads(denied.stdout)
    assert payload["errors"]
    assert "MAPPING_APPROVAL_REQUIRED" in payload["errors"][0]

    approved = _run_cli("ingest", str(source), "--json", "--auto-approve")
    assert approved.returncode == 0
    approved_payload = json.loads(approved.stdout)
    assert approved_payload["total_claims"] > 0
    assert approved_payload["false_verified_count"] == 0
    assert approved_payload["file_results"][0]["mapping_path"]
