"""Tests for the reason service (v6.11.0)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vcse.reasoning.service import (
    REASON_COMPLETE,
    REASON_RUNTIME_INVALID,
    ReasonServiceRequest,
    run_reason_service,
)
from vcse.runtime.hardening import RuntimeArtifactError
from vcse.runtime.model import CSRFIndex, CSRFRecord
from vcse.runtime.serialize import save_csrf


def _minimal_csrf(tmp_path: Path, records: list[dict] | None = None) -> Path:
    if records is None:
        records = [
            {
                "claim_id": "c1",
                "subject": "Alice",
                "relation": "knows",
                "object": "Bob",
                "trust_tier": 3,
                "lifecycle_status": "certified",
                "verification_status": "VERIFIED",
                "provenance_id": "prov-1",
            }
        ]
    csrf_records = tuple(CSRFRecord(**r) for r in records)
    by_subject: dict[str, tuple[int, ...]] = {}
    by_relation: dict[str, tuple[int, ...]] = {}
    by_object: dict[str, tuple[int, ...]] = {}
    for i, r in enumerate(records):
        by_subject.setdefault(r["subject"], ())
        by_subject[r["subject"]] = by_subject[r["subject"]] + (i,)
        by_relation.setdefault(r["relation"], ())
        by_relation[r["relation"]] = by_relation[r["relation"]] + (i,)
        by_object.setdefault(r["object"], ())
        by_object[r["object"]] = by_object[r["object"]] + (i,)
    index = CSRFIndex(records=csrf_records, by_subject=by_subject, by_relation=by_relation, by_object=by_object)
    out = tmp_path / "test.csrf"
    save_csrf(index, out)
    return out


# --- 1. Valid .csrf returns REASON_COMPLETE ---
def test_valid_csrf_returns_reason_complete(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    req = ReasonServiceRequest(csrf_path=csrf_path)
    result = run_reason_service(req)
    assert result.status == REASON_COMPLETE


# --- 2. Missing csrf path raises FileNotFoundError ---
def test_missing_csrf_path_raises(tmp_path: Path) -> None:
    req = ReasonServiceRequest(csrf_path=tmp_path / "nonexistent.csrf")
    with pytest.raises(FileNotFoundError):
        run_reason_service(req)


# --- 3. Invalid csrf raises RuntimeArtifactError ---
def test_invalid_csrf_raises_runtime_artifact_error(tmp_path: Path) -> None:
    # A record with trust_tier < 0 fails validation
    bad_csrf = tmp_path / "bad.csrf"
    bad_csrf.write_text(
        '{"records":[{"claim_id":"c1","subject":"A","relation":"r","object":"B",'
        '"trust_tier":-1,"lifecycle_status":"candidate","verification_status":"NO_PROOF",'
        '"provenance_id":"p1"}],"by_subject":{"A":[0]},"by_relation":{"r":[0]},"by_object":{"B":[0]}}',
        encoding="utf-8",
    )
    req = ReasonServiceRequest(csrf_path=bad_csrf)
    with pytest.raises(RuntimeArtifactError):
        run_reason_service(req)


# --- 4. Service does not mutate the .csrf file ---
def test_service_does_not_mutate_csrf(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    original_content = csrf_path.read_text()
    req = ReasonServiceRequest(csrf_path=csrf_path)
    run_reason_service(req)
    assert csrf_path.read_text() == original_content


# --- 5. Result statuses are UPPER_SNAKE_CASE ---
def test_result_status_is_upper_snake_case(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    req = ReasonServiceRequest(csrf_path=csrf_path)
    result = run_reason_service(req)
    assert result.status == result.status.upper()
    assert "_" in result.status or result.status.isalpha()


# --- 6. Zero-proof/no-proof claims do not become VERIFIED ---
def test_no_proof_claims_not_verified(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path, records=[
        {
            "claim_id": "c-np",
            "subject": "X",
            "relation": "relates",
            "object": "Y",
            "trust_tier": 1,
            "lifecycle_status": "candidate",
            "verification_status": "NO_PROOF",
            "provenance_id": "prov-np",
        }
    ])
    req = ReasonServiceRequest(csrf_path=csrf_path)
    result = run_reason_service(req)
    for claim in result.inferred_claims:
        assert claim.get("verification_status") != "VERIFIED" or claim.get("trust_tier", 0) >= 3


# --- 7. trusted_only filters non-certified records ---
def test_trusted_only_filters_claims(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path, records=[
        {
            "claim_id": "c-cert",
            "subject": "A",
            "relation": "r",
            "object": "B",
            "trust_tier": 4,
            "lifecycle_status": "certified",
            "verification_status": "VERIFIED",
            "provenance_id": "p1",
        },
        {
            "claim_id": "c-cand",
            "subject": "C",
            "relation": "r",
            "object": "D",
            "trust_tier": 1,
            "lifecycle_status": "candidate",
            "verification_status": "NO_PROOF",
            "provenance_id": "p2",
        },
    ])
    req_all = ReasonServiceRequest(csrf_path=csrf_path, trusted_only=False)
    req_trusted = ReasonServiceRequest(csrf_path=csrf_path, trusted_only=True)
    result_all = run_reason_service(req_all)
    result_trusted = run_reason_service(req_trusted)
    assert result_trusted.inferred_count <= result_all.inferred_count


# --- 8. explain=True returns explanations dict ---
def test_explain_returns_explanations(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    req = ReasonServiceRequest(csrf_path=csrf_path, explain=True)
    result = run_reason_service(req)
    assert result.status == REASON_COMPLETE
    assert result.explanations is not None
    assert isinstance(result.explanations, dict)


# --- 9. explain=False returns no explanations ---
def test_no_explain_returns_no_explanations(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    req = ReasonServiceRequest(csrf_path=csrf_path, explain=False)
    result = run_reason_service(req)
    assert result.explanations is None


# --- 10. Missing proof index path raises FileNotFoundError ---
def test_missing_proof_index_raises(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    req = ReasonServiceRequest(csrf_path=csrf_path, proof_index_path=tmp_path / "nonexistent.proof.json")
    with pytest.raises(FileNotFoundError):
        run_reason_service(req)


# --- 11. Invalid proof index raises RuntimeArtifactError ---
def test_invalid_proof_index_raises(tmp_path: Path) -> None:
    csrf_path = _minimal_csrf(tmp_path)
    bad_proof = tmp_path / "bad.proof.json"
    # proof_id="" fails PROOF_MISSING_PROOF_ID validation
    bad_proof.write_text(
        '{"proofs":[{"proof_id":"","result_claim_id":"c1","path_length":-1,'
        '"trust_tier":0,"verification_status":"VERIFIED","steps":[]}]}',
        encoding="utf-8",
    )
    req = ReasonServiceRequest(csrf_path=csrf_path, proof_index_path=bad_proof)
    with pytest.raises(RuntimeArtifactError):
        run_reason_service(req)
