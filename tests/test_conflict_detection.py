import json
import os
import subprocess
import sys
from pathlib import Path

from vcse.conflict.detector import ConflictDetector


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, text=True, env=env)


def test_conflict_detection_identifies_multi_object_conflict() -> None:
    claims = [
        {
            "subject": "Kazakhstan",
            "relation": "capital_of",
            "object": "Astana",
            "normalized_subject": "kazakhstan",
            "normalized_object": "astana",
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "Kazakhstan",
            "relation": "capital_of",
            "object": "Nur-Sultan",
            "normalized_subject": "kazakhstan",
            "normalized_object": "nursultan",
            "provenance": {"source_id": "s2"},
        },
    ]
    conflicts = ConflictDetector().detect(claims)
    assert len(conflicts) == 1
    assert conflicts[0].subject == "kazakhstan"


def test_no_false_conflict_for_identical_claims() -> None:
    claims = [
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Paris",
            "normalized_subject": "france",
            "normalized_object": "paris",
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Paris",
            "normalized_subject": "france",
            "normalized_object": "paris",
            "provenance": {"source_id": "s2"},
        },
    ]
    assert ConflictDetector().detect(claims) == []


def test_entity_normalize_cli() -> None:
    result = _run_cli("entity", "normalize", "United", "States", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["normalized"] == "united_states"
    assert payload["canonical_id"] == "entity:united_states"


def test_conflict_detect_cli(tmp_path: Path) -> None:
    pack_dir = tmp_path / "examples" / "packs" / "conflict_pack"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text(json.dumps({"id": "conflict_pack", "version": "1.0.0"}, sort_keys=True))
    claims = [
        {
            "claim_key": "kazakhstan|capital_of|astana",
            "subject": "Kazakhstan",
            "relation": "capital_of",
            "object": "Astana",
            "normalized_subject": "kazakhstan",
            "normalized_object": "astana",
            "provenance": {"source_id": "s1"},
        },
        {
            "claim_key": "kazakhstan|capital_of|nursultan",
            "subject": "Kazakhstan",
            "relation": "capital_of",
            "object": "Nur-Sultan",
            "normalized_subject": "kazakhstan",
            "normalized_object": "nursultan",
            "provenance": {"source_id": "s2"},
        },
    ]
    (pack_dir / "claims.jsonl").write_text("\n".join(json.dumps(item, sort_keys=True) for item in claims) + "\n")
    (pack_dir / "provenance.jsonl").write_text("\n")

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "vcse.cli", "conflict", "detect", "--pack", str(pack_dir), "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["conflict_count"] == 1
