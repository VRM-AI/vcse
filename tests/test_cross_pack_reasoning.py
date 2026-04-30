from __future__ import annotations

import json
from pathlib import Path

from vcse.conflict.detector import ConflictDetector
from vcse.pipeline.runner import cross_pack_reason
from vcse.reasoning.global_graph import build_global_claim_graph


def _write_pack(pack_dir: Path, pack_id: str, claims: list[dict]) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text(json.dumps({"id": pack_id, "version": "1.0.0"}, sort_keys=True))
    lines = [json.dumps(item, sort_keys=True) for item in claims]
    (pack_dir / "claims.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""))


def test_cross_pack_inference_two_packs(tmp_path: Path) -> None:
    root = tmp_path / "packs"
    _write_pack(
        root / "pack_a",
        "pack.a",
        [
            {
                "subject": "Socrates",
                "relation": "has_type",
                "object": "human",
                "trust_tier": 4,
                "claim_id": "a1",
                "provenance": {"source_id": "src_a"},
            }
        ],
    )
    _write_pack(
        root / "pack_b",
        "pack.b",
        [
            {
                "subject": "human",
                "relation": "implies",
                "object": "mortal",
                "trust_tier": 2,
                "claim_id": "b1",
                "provenance": {"source_id": "src_b"},
            }
        ],
    )

    graph = build_global_claim_graph([root / "pack_a", root / "pack_b"])
    inferred = cross_pack_reason(graph.to_dicts(), rules=None)

    assert len(inferred) == 1
    assert inferred[0]["subject"] == "Socrates"
    assert inferred[0]["relation"] == "is"
    assert inferred[0]["object"] == "mortal"


def test_cross_pack_conflict_detection() -> None:
    claims = [
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Paris",
            "pack_id": "pack.a",
            "claim_id": "a1",
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Lyon",
            "pack_id": "pack.b",
            "claim_id": "b1",
            "provenance": {"source_id": "s2"},
        },
    ]
    conflicts = ConflictDetector().detect_global_conflicts(claims)
    assert len(conflicts) == 1
    assert conflicts[0].pack_ids == ("pack.a", "pack.b")
    assert conflicts[0].provenance_refs == ("s1", "s2")


def test_provenance_chain_validation() -> None:
    claims = [
        {
            "subject": "Socrates",
            "relation": "has_type",
            "object": "human",
            "pack_id": "pack.a",
            "claim_id": "a1",
            "trust_tier": 3,
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "human",
            "relation": "implies",
            "object": "mortal",
            "pack_id": "pack.b",
            "claim_id": "b1",
            "trust_tier": 2,
            "provenance": {"source_id": "s2"},
        },
    ]
    inferred = cross_pack_reason(claims, rules=None)
    assert inferred[0]["derived_from"] == [
        {"pack_id": "pack.a", "claim_id": "a1"},
        {"pack_id": "pack.b", "claim_id": "b1"},
    ]


def test_trust_propagation_validation() -> None:
    claims = [
        {
            "subject": "Socrates",
            "relation": "has_type",
            "object": "human",
            "pack_id": "pack.a",
            "claim_id": "a1",
            "trust_tier": 5,
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "human",
            "relation": "implies",
            "object": "mortal",
            "pack_id": "pack.b",
            "claim_id": "b1",
            "trust_tier": 1,
            "provenance": {"source_id": "s2"},
        },
    ]
    inferred = cross_pack_reason(claims, rules=None)
    assert inferred[0]["trust_tier"] == 1


def test_deterministic_repeatability() -> None:
    claims = [
        {
            "subject": "Socrates",
            "relation": "has_type",
            "object": "human",
            "pack_id": "pack.a",
            "claim_id": "a1",
            "trust_tier": 4,
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "human",
            "relation": "implies",
            "object": "mortal",
            "pack_id": "pack.b",
            "claim_id": "b1",
            "trust_tier": 3,
            "provenance": {"source_id": "s2"},
        },
    ]
    first = cross_pack_reason(claims, rules=None)
    second = cross_pack_reason(claims, rules=None)
    assert first == second
