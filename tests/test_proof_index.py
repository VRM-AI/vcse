from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vcse.pipeline.runner import cross_pack_reason
from vcse.proof import (
    compile_proofs_from_csrf,
    compile_proofs_from_records,
    load_proof_index,
    proof_index_from_dict,
    proof_index_to_dict,
    proof_path_to_explanation_trace,
    save_proof_index,
    select_best_proof,
)
from vcse.runtime.model import CSRFIndex, CSRFRecord


def _csrf(records: list[CSRFRecord]) -> CSRFIndex:
    by_subject: dict = {}
    by_relation: dict = {}
    by_object: dict = {}
    for idx, rec in enumerate(records):
        by_subject.setdefault(rec.subject, []).append(idx)
        by_relation.setdefault(rec.relation, []).append(idx)
        by_object.setdefault(rec.object, []).append(idx)
    return CSRFIndex(
        records=tuple(records),
        by_subject={k: tuple(v) for k, v in by_subject.items()},
        by_relation={k: tuple(v) for k, v in by_relation.items()},
        by_object={k: tuple(v) for k, v in by_object.items()},
    )


def _records() -> list[CSRFRecord]:
    return [
        CSRFRecord("c1", "Socrates", "has_type", "Human", 5, "certified", "VERIFIED", "p1"),
        CSRFRecord("c2", "Human", "implies", "Mortal", 4, "certified", "VERIFIED", "p2"),
        CSRFRecord("c3", "France", "has_capital", "Paris", 4, "certified", "VERIFIED", "p3"),
        CSRFRecord("c4", "Foo", "wat", "Bar", 1, "candidate", "UNVERIFIED", "p4"),
    ]


def _inferred_dicts() -> list[dict]:
    base = [
        {
            "subject": "Socrates",
            "relation": "has_type",
            "object": "Human",
            "pack_id": "p",
            "claim_id": "c1",
            "trust_tier": 5,
        },
        {
            "subject": "Human",
            "relation": "implies",
            "object": "Mortal",
            "pack_id": "p",
            "claim_id": "c2",
            "trust_tier": 4,
        },
    ]
    return cross_pack_reason(base)


def test_proof_compilation_deterministic() -> None:
    a = compile_proofs_from_csrf(_csrf(_records()))
    b = compile_proofs_from_csrf(_csrf(list(reversed(_records()))))
    assert a == b


def test_modified_csrf_changes_proof_index() -> None:
    base = compile_proofs_from_csrf(_csrf(_records()))
    altered = _records()
    altered[0] = CSRFRecord("c1", "Socrates", "has_type", "Person", 5, "certified", "VERIFIED", "p1")
    other = compile_proofs_from_csrf(_csrf(altered))
    assert base != other


def test_zero_proof_unverified_record_not_promoted() -> None:
    record = CSRFRecord("u1", "Foo", "is", "Bar", 1, "candidate", "UNVERIFIED", "p")
    index = compile_proofs_from_csrf(_csrf([record]))
    assert len(index.proofs) == 1
    assert index.proofs[0].verification_status == "UNVERIFIED"
    # No fabricated VERIFIED path.
    assert all(p.verification_status != "VERIFIED" for p in index.proofs)


def test_proof_ordering_verified_first_then_shortest() -> None:
    inferred = _inferred_dicts()
    target_id = inferred[0]["claim_id"]
    direct = [
        {
            "claim_id": target_id,
            "subject": inferred[0]["subject"],
            "relation": inferred[0]["relation"],
            "object": inferred[0]["object"],
            "trust_tier": 5,
            "verification_status": "VERIFIED",
        }
    ]
    index = compile_proofs_from_records([*direct, *inferred])
    paths = [p for p in index.proofs if p.result_claim_id == target_id]
    assert len(paths) >= 2
    assert paths[0].verification_status == "VERIFIED"
    assert paths[0].path_length == 1


def test_reverse_dependency_by_support() -> None:
    inferred = _inferred_dicts()
    index = compile_proofs_from_records(inferred)
    assert any("c1" in p.supporting_claim_ids for p in index.proofs)
    dependents = index.proofs_supporting("c1")
    assert dependents
    for path in dependents:
        assert path.result_claim_id != "c1"


def test_serialization_roundtrip(tmp_path: Path) -> None:
    index = compile_proofs_from_csrf(_csrf(_records()))
    path = tmp_path / "x.proof.json"
    save_proof_index(index, path)
    payload = json.loads(path.read_text())
    rebuilt = proof_index_from_dict(payload)
    # serialise back: stable
    assert proof_index_to_dict(index) == proof_index_to_dict(rebuilt)
    again = load_proof_index(path)
    assert proof_index_to_dict(again) == proof_index_to_dict(index)


def test_select_best_proof_and_explanation_trace() -> None:
    inferred = _inferred_dicts()
    index = compile_proofs_from_records(inferred)
    inferred_id = inferred[0]["claim_id"]
    best = select_best_proof(index, inferred_id)
    assert best is not None
    trace = proof_path_to_explanation_trace(best)
    assert trace["result_claim_id"] == inferred_id
    assert trace["path_length"] == best.path_length
    assert trace["trace"]


def test_empty_proof_index() -> None:
    index = compile_proofs_from_records([])
    assert index.proofs == ()
    assert index.by_result == {}


def test_trust_tier_and_status_preserved() -> None:
    record = CSRFRecord("c5", "X", "y", "Z", 2, "candidate", "VERIFIED", "p")
    index = compile_proofs_from_csrf(_csrf([record]))
    assert index.proofs[0].trust_tier == 2
    assert index.proofs[0].verification_status == "VERIFIED"


def test_cli_proof_build_why_supports(tmp_path: Path) -> None:
    inferred = _inferred_dicts()
    # Build proof index from inferred via direct save (CLI builds from CSRF; here we
    # exercise the CLI by first persisting a CSRF then proof build over it).
    from vcse.cmcf import claim_dict_to_cmcf, record_from_dict, record_to_dict
    from vcse.cmcf.hash import compute_content_hash
    from vcse.runtime import compile_cmcf_to_csrf, save_csrf

    cmcf_records = []
    for entry in [
        {"subject": "Socrates", "relation": "has_type", "object": "Human"},
        {"subject": "Human", "relation": "implies", "object": "Mortal"},
    ]:
        rec = claim_dict_to_cmcf(
            entry,
            source_type="manual",
            source_uri="file://x",
            locator="row:1",
            raw_value=json.dumps(entry),
        )
        payload = record_to_dict(rec)
        payload["trust"]["trust_tier"] = 4
        payload["status"]["lifecycle_status"] = "certified"
        payload["status"]["verification_status"] = "VERIFIED"
        payload["integrity"]["content_hash"] = compute_content_hash(
            {
                "cmcf_version": payload["cmcf_version"],
                "claim": payload["claim"],
                "provenance": payload["provenance"],
                "status": payload["status"],
                "trust": payload["trust"],
                "metadata": payload["metadata"],
            }
        )
        cmcf_records.append(record_from_dict(payload))

    csrf = compile_cmcf_to_csrf(cmcf_records)
    csrf_path = tmp_path / "x.csrf"
    save_csrf(csrf, csrf_path)
    proof_path = tmp_path / "x.proof.json"

    cmd_build = [
        sys.executable, "-m", "vcse", "proof", "build",
        "--csrf", str(csrf_path), "--output", str(proof_path), "--json",
    ]
    out = subprocess.run(cmd_build, capture_output=True, text=True, check=True).stdout
    payload = json.loads(out)
    assert payload["status"] == "PROOF_INDEX_BUILT"
    assert proof_path.exists()
    assert payload["proof_count"] == len(csrf.records)

    target_cid = csrf.records[0].claim_id
    cmd_why = [
        sys.executable, "-m", "vcse", "proof", "why", target_cid,
        "--proof-index", str(proof_path), "--json",
    ]
    why = json.loads(subprocess.run(cmd_why, capture_output=True, text=True, check=True).stdout)
    assert why["claim_id"] == target_cid
    assert why["proof_count"] >= 1
    assert why["selected_proof"]["result_claim_id"] == target_cid

    cmd_supports = [
        sys.executable, "-m", "vcse", "proof", "supports", target_cid,
        "--proof-index", str(proof_path), "--json",
    ]
    supports = json.loads(
        subprocess.run(cmd_supports, capture_output=True, text=True, check=True).stdout
    )
    assert supports["claim_id"] == target_cid
    assert "dependent_proof_count" in supports


def test_query_explain_with_proof_index_does_not_change_result_count(tmp_path: Path) -> None:
    from vcse.cli import run_query
    from vcse.cmcf import claim_dict_to_cmcf, record_from_dict, record_to_dict
    from vcse.cmcf.hash import compute_content_hash
    from vcse.runtime import compile_cmcf_to_csrf, save_csrf

    rec = claim_dict_to_cmcf(
        {"subject": "Socrates", "relation": "has_type", "object": "Human"},
        source_type="manual",
        source_uri="file://x",
        locator="row:1",
        raw_value="{}",
    )
    payload = record_to_dict(rec)
    payload["trust"]["trust_tier"] = 4
    payload["status"]["lifecycle_status"] = "certified"
    payload["status"]["verification_status"] = "VERIFIED"
    payload["integrity"]["content_hash"] = compute_content_hash(
        {
            "cmcf_version": payload["cmcf_version"],
            "claim": payload["claim"],
            "provenance": payload["provenance"],
            "status": payload["status"],
            "trust": payload["trust"],
            "metadata": payload["metadata"],
        }
    )
    cmcf = record_from_dict(payload)
    csrf_path = tmp_path / "x.csrf"
    save_csrf(compile_cmcf_to_csrf([cmcf]), csrf_path)
    proof_path = tmp_path / "x.proof.json"
    save_proof_index(compile_proofs_from_csrf(__import__("vcse.runtime.serialize", fromlist=["load_csrf"]).load_csrf(csrf_path)), proof_path)

    base = json.loads(
        run_query(
            csrf_file=csrf_path,
            subject="Socrates",
            json_output=True,
            explain=True,
        )
    )
    with_proof = json.loads(
        run_query(
            csrf_file=csrf_path,
            subject="Socrates",
            json_output=True,
            explain=True,
            proof_index_file=proof_path,
        )
    )
    assert base["result_count"] == with_proof["result_count"]
    assert base["explanations"] == with_proof["explanations"]


def test_reason_explain_with_proof_index_inferred_count_unchanged(tmp_path: Path) -> None:
    from vcse.cli import run_reason
    from vcse.cmcf import claim_dict_to_cmcf, record_from_dict, record_to_dict
    from vcse.cmcf.hash import compute_content_hash
    from vcse.runtime import compile_cmcf_to_csrf, save_csrf

    cmcf_records = []
    for entry in [
        {"subject": "Socrates", "relation": "has_type", "object": "Human"},
        {"subject": "Human", "relation": "implies", "object": "Mortal"},
    ]:
        rec = claim_dict_to_cmcf(
            entry,
            source_type="manual",
            source_uri="file://x",
            locator="row:1",
            raw_value=json.dumps(entry),
        )
        payload = record_to_dict(rec)
        payload["trust"]["trust_tier"] = 4
        payload["status"]["lifecycle_status"] = "certified"
        payload["status"]["verification_status"] = "VERIFIED"
        payload["integrity"]["content_hash"] = compute_content_hash(
            {
                "cmcf_version": payload["cmcf_version"],
                "claim": payload["claim"],
                "provenance": payload["provenance"],
                "status": payload["status"],
                "trust": payload["trust"],
                "metadata": payload["metadata"],
            }
        )
        cmcf_records.append(record_from_dict(payload))
    csrf_path = tmp_path / "x.csrf"
    save_csrf(compile_cmcf_to_csrf(cmcf_records), csrf_path)
    proof_path = tmp_path / "x.proof.json"
    from vcse.runtime.serialize import load_csrf
    save_proof_index(compile_proofs_from_csrf(load_csrf(csrf_path)), proof_path)

    base = json.loads(run_reason(csrf_file=csrf_path, json_output=True, explain=True))
    enriched = json.loads(
        run_reason(csrf_file=csrf_path, json_output=True, explain=True, proof_index_file=proof_path)
    )
    assert len(base["inferred_claims"]) == len(enriched["inferred_claims"])
    assert base["explanations"] == enriched["explanations"]
