from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vcse.conflict import (
    CONFLICT_WORKFLOW_COMPLETE,
    CONFLICT_WORKFLOW_NO_CONFLICTS,
    Conflict,
    ConflictDetector,
    ConflictRef,
    analyze_conflict_impact,
    build_conflict_workflow_report,
    compute_conflict_id,
    conflict_workflow_report_to_dict,
    derive_refs_from_claims,
    generate_resolution_options,
)
from vcse.proof import compile_proofs_from_records


def _claims() -> list[dict]:
    return [
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Paris",
            "pack_id": "p1",
            "claim_id": "c-paris",
            "trust_tier": 4,
            "provenance": {"source_id": "s1"},
        },
        {
            "subject": "France",
            "relation": "has_capital",
            "object": "Lyon",
            "pack_id": "p2",
            "claim_id": "c-lyon",
            "trust_tier": 1,
            "provenance": {"source_id": "s2"},
        },
    ]


def test_conflict_id_object_order_independent() -> None:
    a = compute_conflict_id("X", "rel", "alpha", "beta", ["c1", "c2"])
    b = compute_conflict_id("X", "rel", "beta", "alpha", ["c2", "c1"])
    assert a == b
    assert a.startswith("sha256:")


def test_no_conflicts_returns_no_conflicts_status() -> None:
    report = build_conflict_workflow_report((), proof_index=None)
    assert report.status == CONFLICT_WORKFLOW_NO_CONFLICTS
    assert report.conflict_count == 0


def test_workflow_report_deterministic() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    a = build_conflict_workflow_report(refs, None)
    b = build_conflict_workflow_report(refs, None)
    assert a == b


def test_impact_without_proof_index_direct_only() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    impacts = analyze_conflict_impact(refs, None)
    assert impacts
    assert impacts[0].affected_proof_ids == ()
    assert impacts[0].affected_result_claim_ids == ()
    assert set(impacts[0].affected_claim_ids) == {"c-paris", "c-lyon"}


def test_impact_with_proof_index_includes_dependents() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    inferred = [
        {
            "claim_id": "d1",
            "subject": "France",
            "relation": "is",
            "object": "European",
            "trust_tier": 4,
            "verification_status": "UNVERIFIED",
            "derived_from": [{"pack_id": "p1", "claim_id": "c-paris"}],
            "proofs": [
                {"claim_id": "c-paris", "subject": "France", "relation": "has_capital", "object": "Paris"}
            ],
            "proof_count": 1,
        }
    ]
    proof_index = compile_proofs_from_records(inferred)
    impacts = analyze_conflict_impact(refs, proof_index)
    assert "d1" in impacts[0].affected_result_claim_ids
    assert impacts[0].affected_proof_ids


def test_resolution_options_include_required_actions() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    options = generate_resolution_options(refs[0])
    actions = sorted(option.action for option in options)
    assert actions == ["KEEP_A", "KEEP_B", "MARK_DISPUTED", "REQUIRE_REVIEW"]


def test_resolution_options_do_not_mutate(monkeypatch) -> None:
    claims = _claims()
    snapshot = json.dumps(claims, sort_keys=True)
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(claims)
    refs = derive_refs_from_claims(conflicts, claims)
    generate_resolution_options(refs[0])
    build_conflict_workflow_report(refs, None)
    assert json.dumps(claims, sort_keys=True) == snapshot


def test_trust_aware_rationale_present() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    options = generate_resolution_options(refs[0])
    keep_a = next(o for o in options if o.action == "KEEP_A")
    assert "trust_tier" in keep_a.rationale.lower()


def test_existing_detector_unchanged() -> None:
    base = ConflictDetector().detect_global_conflicts(_claims())
    again = ConflictDetector().detect_global_conflicts(_claims())
    assert base == again
    assert isinstance(base[0], Conflict)


def _write_pack(tmp_path: Path, name: str, claims: list[dict]) -> Path:
    pack_dir = tmp_path / name
    pack_dir.mkdir()
    (pack_dir / "pack.json").write_text(json.dumps({"id": name, "lifecycle_status": "candidate"}))
    (pack_dir / "claims.jsonl").write_text("\n".join(json.dumps(item) for item in claims))
    return pack_dir


def test_cli_conflict_workflow_for_pack(tmp_path: Path) -> None:
    pack = _write_pack(tmp_path, "alpha", _claims())
    out = subprocess.run(
        [sys.executable, "-m", "vcse", "conflict", "workflow", "--pack", str(pack), "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    payload = json.loads(out)
    assert payload["status"] == CONFLICT_WORKFLOW_COMPLETE
    assert payload["conflict_count"] >= 1
    assert payload["options"]


def test_cli_conflict_workflow_for_packs_directory(tmp_path: Path) -> None:
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    _write_pack(packs_dir, "p1", [_claims()[0]])
    _write_pack(packs_dir, "p2", [_claims()[1]])
    out = subprocess.run(
        [sys.executable, "-m", "vcse", "conflict", "workflow", "--packs", str(packs_dir), "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    payload = json.loads(out)
    assert payload["status"] == CONFLICT_WORKFLOW_COMPLETE
    assert payload["conflict_count"] >= 1


def test_cli_conflict_impact_from_report(tmp_path: Path) -> None:
    pack = _write_pack(tmp_path, "alpha", _claims())
    out_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable, "-m", "vcse", "conflict", "export-report",
            "--pack", str(pack), "--output", str(out_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(out_path.read_text())
    cid = payload["conflicts"][0]["conflict_id"]
    impact_out = subprocess.run(
        [
            sys.executable, "-m", "vcse", "conflict", "impact", cid,
            "--report", str(out_path), "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    impact_payload = json.loads(impact_out)
    assert impact_payload["conflict_id"] == cid
    assert impact_payload["impacts"]


def test_workflow_json_stable() -> None:
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(_claims())
    refs = derive_refs_from_claims(conflicts, _claims())
    a = json.dumps(conflict_workflow_report_to_dict(build_conflict_workflow_report(refs, None)), sort_keys=True)
    b = json.dumps(conflict_workflow_report_to_dict(build_conflict_workflow_report(refs, None)), sort_keys=True)
    assert a == b


def test_no_automatic_resolution_applied() -> None:
    claims = _claims()
    snapshot = json.dumps(claims, sort_keys=True)
    detector = ConflictDetector()
    conflicts = detector.detect_global_conflicts(claims)
    refs = derive_refs_from_claims(conflicts, claims)
    report = build_conflict_workflow_report(refs, None)
    # All options must be reversible and non-mutating
    assert all(option.reversible for option in report.options)
    assert json.dumps(claims, sort_keys=True) == snapshot


def test_existing_conflict_detect_cli_unchanged(tmp_path: Path) -> None:
    pack = _write_pack(tmp_path, "alpha", _claims())
    out = subprocess.run(
        [sys.executable, "-m", "vcse", "conflict", "detect", "--pack", str(pack), "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    payload = json.loads(out)
    assert payload["conflict_count"] >= 1
    assert "conflicts" in payload
