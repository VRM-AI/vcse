from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vcse.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_ingest_detects_multiple_supported_files(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "a.json").write_text(json.dumps([{"subject": "France", "relation": "has_capital", "object": "Paris"}]))
    (dataset / "b.jsonl").write_text(json.dumps({"subject": "Spain", "relation": "has_capital", "object": "Madrid"}) + "\n")
    (dataset / "c.csv").write_text("subject,relation,object\nItaly,has_capital,Rome\n")
    (dataset / "ignore.txt").write_text("ignored")

    result = run_cli("ingest", str(dataset), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    assert payload["files_processed"] == 3
    assert len(payload["packs_created"]) == 3
    assert payload["total_claims"] == 3
    assert payload["total_conflicts"] == 0
    assert payload["false_verified_count"] == 0


def test_ingest_routes_adapters_and_creates_candidate_pack(tmp_path: Path) -> None:
    source = tmp_path / "claims.jsonl"
    source.write_text(json.dumps({"subject": "A", "relation": "r", "object": "B"}) + "\n")

    result = run_cli("ingest", str(source), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    file_result = payload["file_results"][0]
    assert file_result["adapter_type"] == "jsonl"
    assert file_result["error"] is None

    pack_id = payload["packs_created"][0]
    pack_path = REPO_ROOT / "examples" / "packs" / pack_id
    assert (pack_path / "pack.json").exists()
    manifest = json.loads((pack_path / "pack.json").read_text())
    assert manifest["lifecycle_status"] == "candidate"


def test_ingest_surfaces_conflict_and_entity_metrics(tmp_path: Path) -> None:
    source = tmp_path / "conflict.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps({"subject": "France", "relation": "has_capital", "object": "Paris"}),
                json.dumps({"subject": "France", "relation": "has_capital", "object": "Lyon"}),
            ]
        )
        + "\n"
    )

    result = run_cli("ingest", str(source), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    assert payload["total_conflicts"] == 1
    item = payload["file_results"][0]
    assert item["conflict_count"] == 1
    assert item["canonical_entity_count"] >= 1
    assert item["duplicate_entity_count"] >= 0


def test_ingest_file_level_error_does_not_stop_run(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "good.json").write_text(json.dumps([{"subject": "A", "relation": "r", "object": "B"}]))
    (dataset / "bad.jsonl").write_text(json.dumps({"subject": "X", "relation": "r"}) + "\n")

    result = run_cli("ingest", str(dataset), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    assert payload["files_processed"] == 2
    assert len(payload["packs_created"]) == 1
    assert len(payload["errors"]) == 1
    errored = [row for row in payload["file_results"] if row["error"]]
    assert len(errored) == 1


def test_ingest_persists_report_correctly(tmp_path: Path) -> None:
    source = tmp_path / "claims.json"
    source.write_text(json.dumps([{"subject": "A", "relation": "r", "object": "B"}]))

    result = run_cli("ingest", str(source), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    report_path = REPO_ROOT / ".vcse" / "ingest_runs" / f"{payload['run_id']}.json"
    assert report_path.exists()
    report_payload = json.loads(report_path.read_text())
    assert report_payload["run_id"] == payload["run_id"]
    assert report_payload["total_claims"] == 1
