from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vcse.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_first_incremental_ingest_creates_pack_and_state(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    result = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "INGEST_INCREMENTAL_COMPLETE"
    assert payload["incremental"] is True
    assert payload["delta"]["status"] == "DELTA_NEW"
    assert payload["pack_created"]
    state_dir = tmp_path / ".vcse" / "ingest_state"
    assert state_dir.exists()
    assert len(list(state_dir.glob("*.json"))) == 1


def test_second_incremental_ingest_same_file_returns_no_changes(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    second = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    payload = json.loads(second.stdout)
    assert payload["status"] == "INGEST_NO_CHANGES"
    assert payload["delta"]["status"] == "DELTA_NO_CHANGES"
    assert payload["pack_created"] is None
    assert payload["previous_pack_id"]


def test_changed_file_returns_delta_changed(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Lyon"}])
    changed = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    payload = json.loads(changed.stdout)
    assert payload["status"] == "INGEST_INCREMENTAL_COMPLETE"
    assert payload["delta"]["status"] == "DELTA_CHANGED"


def test_added_and_removed_row_counts_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(
        source,
        [
            {"subject": "France", "relation": "has_capital", "object": "Paris"},
            {"subject": "Italy", "relation": "has_capital", "object": "Rome"},
        ],
    )
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    _write_jsonl(
        source,
        [
            {"subject": "France", "relation": "has_capital", "object": "Paris"},
            {"subject": "Spain", "relation": "has_capital", "object": "Madrid"},
        ],
    )
    changed = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    payload = json.loads(changed.stdout)
    assert payload["delta"]["added_count"] == 1
    assert payload["delta"]["removed_count"] == 1
    assert payload["delta"]["unchanged_count"] == 1


def test_removed_row_increments_removed_count(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(
        source,
        [
            {"subject": "France", "relation": "has_capital", "object": "Paris"},
            {"subject": "Spain", "relation": "has_capital", "object": "Madrid"},
        ],
    )
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    changed = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    payload = json.loads(changed.stdout)
    assert payload["delta"]["removed_count"] == 1


def test_force_regenerates_despite_no_changes(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    forced = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental", "--force")
    payload = json.loads(forced.stdout)
    assert payload["status"] == "INGEST_INCREMENTAL_COMPLETE"
    assert payload["pack_created"]
    assert payload["delta"]["status"] == "DELTA_NO_CHANGES"


def test_state_file_is_deterministic_except_timestamps_and_run_id(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    state_path = next((tmp_path / ".vcse" / "ingest_state").glob("*.json"))
    first = json.loads(state_path.read_text(encoding="utf-8"))
    _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    second = json.loads(state_path.read_text(encoding="utf-8"))
    first.pop("updated_at", None)
    second.pop("updated_at", None)
    first.pop("last_run_id", None)
    second.pop("last_run_id", None)
    assert first == second


def test_default_ingest_without_incremental_is_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"subject": "France", "relation": "has_capital", "object": "Paris"}])
    result = _run_cli(tmp_path, "ingest", str(source), "--json")
    payload = json.loads(result.stdout)
    assert payload["status"] == "INGEST_COMPLETE"
    assert payload["false_verified_count"] == 0
    assert payload.get("incremental", False) is False


def test_unsupported_incremental_source_type_reports_clean_error(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(json.dumps([{"subject": "France", "relation": "has_capital", "object": "Paris"}]))
    result = _run_cli(tmp_path, "ingest", str(source), "--json", "--incremental")
    payload = json.loads(result.stdout)
    assert payload["errors"]
    assert "INCREMENTAL_UNSUPPORTED_SOURCE" in payload["errors"][0]


def test_generated_artifact_ignore_entries_present() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tests/**/pack.json" in gitignore
    assert "benchmarks/compiled_*.jsonl" in gitignore
    assert "examples/packs/compiled_*/" in gitignore
