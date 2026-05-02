from __future__ import annotations

import json
from pathlib import Path

from vcse.cli import run_query, run_reason
from vcse.explain import ExplanationBuilder, ExplanationRenderer


def _write_pack(pack_dir: Path, pack_id: str, claims: list[dict]) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text(
        json.dumps({"id": pack_id, "version": "1.0.0", "domain": "test", "lifecycle_status": "candidate"}, sort_keys=True)
    )
    (pack_dir / "claims.jsonl").write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in claims) + ("\n" if claims else "")
    )


def test_explicit_claim_explanation_includes_subject_relation_object() -> None:
    trace = ExplanationBuilder().explain_claim(
        {"subject": "France", "relation": "has_capital", "object": "Paris", "pack_id": "p1", "claim_id": "c1"}
    )
    text = ExplanationRenderer().render_text(trace)
    assert "France has_capital Paris." in text


def test_explicit_claim_explanation_includes_provenance_when_present() -> None:
    trace = ExplanationBuilder().explain_claim(
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Paris",
            "pack_id": "p1",
            "claim_id": "c1",
            "provenance": {"source_id": "src-1"},
        }
    )
    payload = ExplanationRenderer().render_json(trace)
    assert any(node["node_type"] == "provenance" for node in payload["nodes"])


def test_inferred_claim_explanation_includes_derived_from_chain() -> None:
    trace = ExplanationBuilder().explain_inferred_claim(
        {
            "subject": "Socrates",
            "relation": "is",
            "object": "mortal",
            "claim_id": "derived-1",
            "derived_from": [
                {"pack_id": "pack.a", "claim_id": "a1"},
                {"pack_id": "pack.b", "claim_id": "b1"},
            ],
            "verification_status": "VERIFIED",
        }
    )
    payload = ExplanationRenderer().render_json(trace)
    proof_steps = [node for node in payload["nodes"] if node["node_type"] == "proof_step"]
    assert len(proof_steps) == 2
    assert trace.verification_status == "VERIFIED"


def test_missing_derived_from_returns_unverified_no_trace_explanation() -> None:
    trace = ExplanationBuilder().explain_inferred_claim(
        {"subject": "Socrates", "relation": "is", "object": "mortal", "claim_id": "derived-2"}
    )
    text = ExplanationRenderer().render_text(trace)
    assert trace.verification_status == "UNVERIFIED"
    assert "no proof trace is available" in text


def test_zero_proof_result_is_never_rendered_as_verified() -> None:
    trace = ExplanationBuilder().explain_inferred_claim(
        {
            "subject": "Socrates",
            "relation": "is",
            "object": "mortal",
            "claim_id": "derived-3",
            "proof_count": 0,
            "proofs": [],
            "verification_status": "VERIFIED",
        }
    )
    assert trace.verification_status == "UNVERIFIED"


def test_query_explain_json_includes_explanations(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        "p1",
        [
            {
                "subject": "France",
                "relation": "has_capital",
                "object": "Paris",
                "claim_id": "c1",
                "trust_tier": 4,
                "provenance": {"source_id": "src-1"},
            }
        ],
    )
    payload = json.loads(
        run_query(
            packs_dir=packs,
            subject="France",
            relation="has_capital",
            json_output=True,
            explain=True,
        )
    )
    assert "explanations" in payload
    assert payload["explanations"]["status"] == "EXPLANATION_COMPLETE"
    assert payload["explanations"]["trace_count"] == 1


def test_reason_explain_json_includes_proof_trace(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        "pack.a",
        [{"subject": "Socrates", "relation": "has_type", "object": "human", "claim_id": "a1", "trust_tier": 3}],
    )
    _write_pack(
        packs / "p2",
        "pack.b",
        [{"subject": "human", "relation": "implies", "object": "mortal", "claim_id": "b1", "trust_tier": 2}],
    )
    payload = json.loads(run_reason(packs, json_output=True, explain=True))
    assert payload["inferred_claims"]
    assert payload["explanations"]["trace_count"] == len(payload["inferred_claims"])
    assert payload["explanations"]["traces"][0]["proof_count"] >= 1


def test_renderer_output_is_deterministic_across_runs() -> None:
    builder = ExplanationBuilder()
    row = {
        "subject": "Socrates",
        "relation": "is",
        "object": "mortal",
        "claim_id": "d1",
        "derived_from": [{"pack_id": "pack.a", "claim_id": "a1"}, {"pack_id": "pack.b", "claim_id": "b1"}],
        "verification_status": "VERIFIED",
    }
    first = ExplanationRenderer().render_json(builder.explain_inferred_claim(row))
    second = ExplanationRenderer().render_json(builder.explain_inferred_claim(row))
    assert first == second


def test_explanations_do_not_change_query_result_count(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        "p1",
        [
            {"subject": "France", "relation": "has_capital", "object": "Paris", "claim_id": "c1"},
            {"subject": "France", "relation": "uses_currency", "object": "Euro", "claim_id": "c2"},
        ],
    )
    base = json.loads(run_query(packs_dir=packs, subject="France", json_output=True))
    explained = json.loads(run_query(packs_dir=packs, subject="France", json_output=True, explain=True))
    assert base["result_count"] == explained["result_count"]


def test_no_explanation_fabricates_unsupported_claims() -> None:
    trace = ExplanationBuilder().explain_inferred_claim(
        {
            "subject": "Socrates",
            "relation": "is",
            "object": "mortal",
            "claim_id": "d2",
            "derived_from": [{"pack_id": "pack.a", "claim_id": "a1"}],
            "verification_status": "UNVERIFIED",
        }
    )
    text = ExplanationRenderer().render_text(trace)
    assert "Therefore:" not in text
    assert "verification_status: UNVERIFIED" in text


def test_default_query_behavior_unchanged_without_explain(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(packs / "p1", "p1", [{"subject": "A", "relation": "r", "object": "B", "claim_id": "c1"}])
    payload = json.loads(run_query(packs_dir=packs, subject="A", json_output=True))
    assert "explanations" not in payload


def test_default_reason_behavior_unchanged_without_explain(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        "pack.a",
        [{"subject": "Socrates", "relation": "has_type", "object": "human", "claim_id": "a1"}],
    )
    _write_pack(
        packs / "p2",
        "pack.b",
        [{"subject": "human", "relation": "implies", "object": "mortal", "claim_id": "b1"}],
    )
    payload = json.loads(run_reason(packs, json_output=True))
    assert "explanations" not in payload
