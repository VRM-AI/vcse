from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from vcse.cmcf.normalize import normalize_source_to_cmcf


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, env=env, text=True)


def test_json_ingestion(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France", "capital": "Paris"}]))
    result = normalize_source_to_cmcf(str(source))
    assert result.status == "INTAKE_COMPLETE"
    assert result.detected_format == "json"
    assert result.row_count == 1


def test_jsonl_ingestion(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text('{"id":"a1","name":"France"}\n{"id":"a2","name":"Spain"}\n')
    result = normalize_source_to_cmcf(str(source))
    assert result.status == "INTAKE_COMPLETE"
    assert result.detected_format == "jsonl"
    assert result.row_count == 2


def test_csv_ingestion(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("id,name\na1,France\na2,Spain\n")
    result = normalize_source_to_cmcf(str(source))
    assert result.status == "INTAKE_COMPLETE"
    assert result.detected_format == "csv"
    assert result.row_count == 2


def test_html_table_ingestion(tmp_path: Path) -> None:
    source = tmp_path / "rows.html"
    source.write_text("<html><body><table><tr><th>id</th><th>name</th></tr><tr><td>a1</td><td>France</td></tr></table></body></html>")
    result = normalize_source_to_cmcf(str(source))
    assert result.status == "INTAKE_COMPLETE"
    assert result.detected_format == "html_table"
    assert result.row_count == 1


def test_generic_mapping_works(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France", "langs": ["fr", "en"]}]))
    result = normalize_source_to_cmcf(str(source), profile="generic_records")
    triples = {(r.claim.subject, r.claim.relation, r.claim.object) for r in result.records}
    assert ("a1", "has_name", "France") in triples
    assert ("a1", "has_langs", "fr") in triples
    assert ("a1", "has_langs", "en") in triples


def test_historical_profile_works(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    source.write_text(json.dumps([{"date": "1969-07-20", "description": "Moon landing", "category": "space", "language": "en"}]))
    result = normalize_source_to_cmcf(str(source))
    assert result.profile_id == "historical_events"
    assert any(r.claim.relation == "occurred_on" for r in result.records)
    assert any(r.claim.relation == "has_description" for r in result.records)


def test_url_ingestion_mock(monkeypatch, tmp_path: Path) -> None:
    class _Resp:
        def __init__(self, body: bytes) -> None:
            self._body = body
            self.headers = {"Content-Type": "application/json"}

        def read(self, _size: int = -1) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(req, timeout=20):  # noqa: ARG001
        return _Resp(b'[{"id":"u1","name":"Web Row"}]')

    monkeypatch.chdir(tmp_path)
    import vcse.intake.fetch as fetch_mod

    monkeypatch.setattr(fetch_mod, "urlopen", _fake_urlopen)
    result = normalize_source_to_cmcf("https://example.com/data")
    assert result.status == "INTAKE_COMPLETE"
    assert result.source.source_type == "url"
    assert result.detected_format == "json"


def test_provenance_attached(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France"}]))
    result = normalize_source_to_cmcf(str(source))
    assert result.records
    first = result.records[0]
    assert first.provenance.source_uri.startswith("file://")
    assert first.provenance.provenance_id.startswith("sha256:")


def test_limit_works(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France"}, {"id": "a2", "name": "Spain"}]))
    result = normalize_source_to_cmcf(str(source), limit=1)
    assert result.row_count == 1


def test_validation_passes(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France"}]))
    result = normalize_source_to_cmcf(str(source))
    assert result.validation_issue_count == 0


def test_unverified_enforced(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"id": "a1", "name": "France"}]))
    result = normalize_source_to_cmcf(str(source))
    assert result.records
    assert all(r.status.verification_status == "UNVERIFIED" for r in result.records)
    assert all(r.status.certification_status == "NOT_CERTIFIED" for r in result.records)
    assert all(r.status.lifecycle_status == "candidate" for r in result.records)


def test_unknown_format_handled(tmp_path: Path) -> None:
    source = tmp_path / "rows.txt"
    source.write_text("not parseable")
    result = normalize_source_to_cmcf(str(source))
    assert result.status == "INTAKE_UNSUPPORTED_FORMAT"


def test_existing_ingest_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(json.dumps([{"subject": "France", "relation": "has_capital", "object": "Paris"}]))
    cli = run_cli("ingest", str(source), "--json")
    assert cli.returncode == 0
    payload = json.loads(cli.stdout)
    assert "files_processed" in payload
    assert "cmcf_record_count" not in payload


def test_dry_run_safe(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("id,name\na1,France\n")
    before = {item.name for item in (Path("examples") / "packs").glob("*")}
    cli = run_cli("ingest", str(source), "--cmcf", "--dry-run", "--json")
    assert cli.returncode == 0
    payload = json.loads(cli.stdout)
    assert payload["dry_run"] is True
    assert payload["pack_created"] is None
    after = {item.name for item in (Path("examples") / "packs").glob("*")}
    assert before == after
