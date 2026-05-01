import json
import os
import subprocess
import sys
from pathlib import Path

from vcse.query import StructuredQuery, StructuredQueryEngine


def _write_pack(base: Path, name: str, lifecycle_status: str, claims: list[dict]) -> Path:
    pack_dir = base / name
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text(
        json.dumps(
            {
                "id": name,
                "version": "1.0.0",
                "domain": "test",
                "lifecycle_status": lifecycle_status,
            }
        )
    )
    (pack_dir / "claims.jsonl").write_text("\n".join(json.dumps(item) for item in claims) + "\n")
    return pack_dir


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, text=True, env=env)


def _build_fixture(tmp_path: Path) -> Path:
    packs_dir = tmp_path / "packs"
    _write_pack(
        packs_dir,
        "alpha",
        "candidate",
        [
            {
                "claim_id": "a1",
                "subject": "France",
                "relation": "has_capital",
                "object": "Paris",
                "trust_tier": 3,
                "provenance": {"source": "alpha"},
            },
            {
                "claim_id": "a2",
                "subject": "France",
                "relation": "uses_currency",
                "object": "Euro",
                "trust_tier": 3,
                "provenance": {"source": "alpha"},
            },
            {
                "claim_id": "a3",
                "subject": "Paris",
                "relation": "located_in_country",
                "object": "France",
                "trust_tier": 3,
                "provenance": {"source": "alpha"},
            },
            {
                "claim_id": "a4",
                "subject": "Paris",
                "relation": "capital_of",
                "object": "France",
                "trust_tier": 3,
                "qualifiers": {"inference_type": "inverse"},
                "provenance": {"source": "alpha"},
            },
        ],
    )
    _write_pack(
        packs_dir,
        "beta",
        "certified",
        [
            {
                "claim_id": "b1",
                "subject": "Germany",
                "relation": "has_capital",
                "object": "Berlin",
                "trust_tier": 5,
                "provenance": {"source": "beta"},
            },
            {
                "claim_id": "b2",
                "subject": "France",
                "relation": "has_capital",
                "object": "Paris",
                "trust_tier": 5,
                "provenance": {"source": "beta"},
            },
        ],
    )
    return packs_dir


def test_subject_only_lookup_returns_all_subject_claims(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(packs_dir, StructuredQuery(subject="France", include_inferred=True))
    assert result.status == "QUERY_COMPLETE"
    assert [(row["subject"], row["relation"], row["object"]) for row in result.results] == [
        ("France", "has_capital", "Paris"),
        ("France", "has_capital", "Paris"),
        ("France", "uses_currency", "Euro"),
    ]


def test_subject_relation_lookup_returns_correct_object(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(subject="France", relation="uses_currency"),
    )
    assert result.result_count == 1
    assert result.results[0]["object"] == "Euro"


def test_relation_only_lookup_returns_sorted_results(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(packs_dir, StructuredQuery(relation="has_capital"))
    assert [(row["subject"], row["relation"], row["object"], row["pack_id"], row["claim_id"]) for row in result.results] == [
        ("France", "has_capital", "Paris", "alpha", "a1"),
        ("France", "has_capital", "Paris", "beta", "b2"),
        ("Germany", "has_capital", "Berlin", "beta", "b1"),
    ]


def test_object_only_reverse_lookup_works(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(packs_dir, StructuredQuery(object="Paris"))
    assert [(row["subject"], row["relation"]) for row in result.results] == [
        ("France", "has_capital"),
        ("France", "has_capital"),
    ]


def test_relation_object_reverse_lookup_works(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(relation="has_capital", object="Paris"),
    )
    assert [row["subject"] for row in result.results] == ["France", "France"]


def test_exact_triple_lookup_works(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(subject="Germany", relation="has_capital", object="Berlin"),
    )
    assert result.result_count == 1
    assert result.results[0]["claim_id"] == "b1"


def test_query_across_multiple_packs_aggregates_deterministically(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(packs_dir, StructuredQuery(subject="France"))
    assert result.packs_searched == ("alpha", "beta")
    assert result.packs_skipped == ()
    assert result.rows_examined == 6


def test_trusted_only_skips_candidate_packs(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(subject="France", trusted_only=True),
    )
    assert result.packs_searched == ("beta",)
    assert result.packs_skipped == ("alpha",)
    assert result.result_count == 1


def test_policy_filter_excludes_blocked_relation(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(
        json.dumps(
            {
                "policy_id": "test-policy",
                "description": "block has_capital",
                "default_effect": "allow",
                "rules": [
                    {
                        "rule_id": "block-capital",
                        "effect": "block",
                        "target_type": "relation",
                        "target": "has_capital",
                        "reason": "blocked",
                    }
                ],
            }
        )
    )
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(relation="has_capital", policy_file=str(policy_file)),
    )
    assert result.status == "QUERY_NO_RESULTS"
    assert "policy:test-policy" in result.filters_applied
    assert any(item.startswith("blocked_claims:") for item in result.filters_applied)


def test_limit_applies_after_deterministic_sorting(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = StructuredQueryEngine().query_packs(
        packs_dir,
        StructuredQuery(relation="has_capital", limit=2),
    )
    assert result.result_count == 2
    assert [(row["pack_id"], row["claim_id"]) for row in result.results] == [("alpha", "a1"), ("beta", "b2")]


def test_json_cli_output_works(tmp_path: Path) -> None:
    packs_dir = _build_fixture(tmp_path)
    result = _run_cli("query", "--packs", str(packs_dir), "--subject", "France", "--relation", "has_capital", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "QUERY_COMPLETE"
    assert payload["result_count"] == 2
    assert payload["rows_examined"] == 6


def test_default_ask_behavior_unchanged_if_touched() -> None:
    result = _run_cli("ask", "All men are mortal. Socrates is a man. Can Socrates die?", "--mode", "simple")
    assert result.returncode == 0
    assert "Yes" in result.stdout
