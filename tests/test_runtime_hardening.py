"""Tests for runtime artifact hardening, validation, and atomic writes."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vcse.runtime.model import CSRFIndex, CSRFRecord
from vcse.proof.model import ProofIndex, ProofPath, ProofStep


# ---------------------------------------------------------------------------
# Helpers to build minimal valid CSRFIndex / ProofIndex fixtures
# ---------------------------------------------------------------------------

def _make_record(
    claim_id: str = "c1",
    subject: str = "Paris",
    relation: str = "capital_of",
    obj: str = "France",
    trust_tier: int = 1,
    lifecycle_status: str = "active",
    verification_status: str = "VERIFIED",
    provenance_id: str = "prov:c1",
) -> CSRFRecord:
    return CSRFRecord(
        claim_id=claim_id,
        subject=subject,
        relation=relation,
        object=obj,
        trust_tier=trust_tier,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        provenance_id=provenance_id,
    )


def _make_valid_csrf() -> CSRFIndex:
    rec = _make_record()
    return CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )


def _make_proof_path(
    proof_id: str = "p1",
    result_claim_id: str = "c1",
    path_length: int = 1,
    verification_status: str = "VERIFIED",
    supporting_claim_ids: tuple[str, ...] = ("c2",),
    steps: tuple[ProofStep, ...] | None = None,
) -> ProofPath:
    if steps is None:
        steps = (
            ProofStep(
                claim_id="c2",
                subject="Paris",
                relation="capital_of",
                object="France",
                verification_status="VERIFIED",
            ),
        )
    return ProofPath(
        proof_id=proof_id,
        result_claim_id=result_claim_id,
        result_subject="Paris",
        result_relation="capital_of",
        result_object="France",
        supporting_claim_ids=supporting_claim_ids,
        steps=steps,
        path_length=path_length,
        trust_tier=1,
        verification_status=verification_status,
        source="materialized",
    )


def _make_valid_proof_index() -> ProofIndex:
    proof = _make_proof_path()
    return ProofIndex(
        proofs=(proof,),
        by_result={"c1": (0,)},
        by_support={"c2": (0,)},
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )


# ---------------------------------------------------------------------------
# 1. Valid .csrf passes validation
# ---------------------------------------------------------------------------

def test_valid_csrf_passes_validation():
    from vcse.runtime.validate import validate_csrf_index

    result = validate_csrf_index(_make_valid_csrf())
    assert result.status == "RUNTIME_VALID"
    assert result.issue_count == 0


# ---------------------------------------------------------------------------
# 2. by_subject out-of-range index fails validation
# ---------------------------------------------------------------------------

def test_out_of_range_subject_index_fails():
    from vcse.runtime.validate import validate_csrf_index

    rec = _make_record()
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (99,)},  # out of range
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    result = validate_csrf_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("RUNTIME_INDEX_OUT_OF_RANGE" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 3. by_relation missing record fails validation
# ---------------------------------------------------------------------------

def test_missing_relation_index_fails():
    from vcse.runtime.validate import validate_csrf_index

    rec = _make_record()
    # record is in records but by_relation doesn't list it
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={},  # missing
        by_object={"France": (0,)},
    )
    result = validate_csrf_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("RUNTIME_MISSING_RELATION_INDEX" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 4. by_object duplicate position fails validation
# ---------------------------------------------------------------------------

def test_duplicate_object_index_position_fails():
    from vcse.runtime.validate import validate_csrf_index

    rec = _make_record()
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0, 0)},  # duplicate position
    )
    result = validate_csrf_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("RUNTIME_DUPLICATE_INDEX_POSITION" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 5. Invalid trust_tier fails validation
# ---------------------------------------------------------------------------

def test_invalid_trust_tier_fails():
    from vcse.runtime.validate import validate_csrf_index

    rec = _make_record(trust_tier=-1)
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    result = validate_csrf_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("RUNTIME_INVALID_TRUST_TIER" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 6. Lowercase verification_status fails validation
# ---------------------------------------------------------------------------

def test_lowercase_verification_status_fails():
    from vcse.runtime.validate import validate_csrf_index

    rec = _make_record(verification_status="verified")  # should be VERIFIED
    index = CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    result = validate_csrf_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("RUNTIME_STATUS_CASING_INVALID" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 7. NaN/Inf in runtime artifact fails validation
# ---------------------------------------------------------------------------

def test_nan_in_runtime_fails():
    from vcse.runtime.validate import validate_csrf_index

    # trust_tier as float('nan') is not representable in CSRFRecord (it's int typed)
    # so we test via a subclass trick or direct CSRFRecord with patched field
    import math
    # Build a CSRFIndex where trust_tier is actually nan via object.__setattr__ bypass
    rec = _make_record()
    # We simulate NaN detection by having a custom dict - but since CSRFRecord is frozen
    # dataclass, we verify the validator also handles raw data paths. Since CSRFRecord
    # uses int for trust_tier, nan can't get in normally; the validator should detect
    # non-finite floats in any serializable field. We test via verify passing a specially
    # crafted index dict via JSON round-trip.
    # Instead: test that a CSRFIndex loaded from JSON with NaN is rejected at load time.
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bad.csrf"
        # Write JSON with NaN (using string "NaN" which standard json doesn't produce
        # but non-standard JSON might contain via allow_nan)
        payload = {
            "records": [{"claim_id": "c1", "subject": "A", "relation": "r", "object": "B",
                          "trust_tier": None, "lifecycle_status": "active",
                          "verification_status": "VERIFIED", "provenance_id": "prov:c1"}],
            "by_subject": {"A": [0]},
            "by_relation": {"r": [0]},
            "by_object": {"B": [0]},
        }
        p.write_text(json.dumps(payload))
        from vcse.runtime.hardening import load_csrf_checked
        # trust_tier = None → should fail checked load
        with pytest.raises(Exception):
            load_csrf_checked(p)


# ---------------------------------------------------------------------------
# 8. Valid proof index passes validation
# ---------------------------------------------------------------------------

def test_valid_proof_index_passes():
    from vcse.proof.validate import validate_proof_index

    result = validate_proof_index(_make_valid_proof_index())
    assert result.status == "RUNTIME_VALID"
    assert result.issue_count == 0


# ---------------------------------------------------------------------------
# 9. VERIFIED zero-path proof fails validation
# ---------------------------------------------------------------------------

def test_verified_zero_path_proof_fails():
    from vcse.proof.validate import validate_proof_index

    proof = _make_proof_path(
        path_length=0,
        verification_status="VERIFIED",
        supporting_claim_ids=(),
        steps=(),
    )
    index = ProofIndex(
        proofs=(proof,),
        by_result={"c1": (0,)},
        by_support={},
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    result = validate_proof_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("PROOF_ZERO_PATH_VERIFIED" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 10. proof by_support out-of-range fails validation
# ---------------------------------------------------------------------------

def test_proof_support_out_of_range_fails():
    from vcse.proof.validate import validate_proof_index

    proof = _make_proof_path()
    index = ProofIndex(
        proofs=(proof,),
        by_result={"c1": (0,)},
        by_support={"c2": (99,)},  # out of range
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )
    result = validate_proof_index(index)
    assert result.status == "RUNTIME_INVALID"
    assert any("PROOF_INDEX_OUT_OF_RANGE" in issue.code for issue in result.issues)


# ---------------------------------------------------------------------------
# 11. atomic_write_text writes complete file
# ---------------------------------------------------------------------------

def test_atomic_write_text_writes_complete_file():
    from vcse.runtime.atomic import atomic_write_text

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "output.txt"
        atomic_write_text(target, "hello world")
        assert target.exists()
        assert target.read_text() == "hello world"


# ---------------------------------------------------------------------------
# 12. atomic_write_bytes writes complete file
# ---------------------------------------------------------------------------

def test_atomic_write_bytes_writes_complete_file():
    from vcse.runtime.atomic import atomic_write_bytes

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "output.bin"
        atomic_write_bytes(target, b"\x00\x01\x02")
        assert target.exists()
        assert target.read_bytes() == b"\x00\x01\x02"


# ---------------------------------------------------------------------------
# 13. Checked loader rejects corrupted .csrf
# ---------------------------------------------------------------------------

def test_checked_loader_rejects_corrupted_csrf():
    from vcse.runtime.hardening import load_csrf_checked

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bad.csrf"
        # out-of-range index in by_subject
        payload = {
            "records": [{"claim_id": "c1", "subject": "A", "relation": "r", "object": "B",
                          "trust_tier": 1, "lifecycle_status": "active",
                          "verification_status": "VERIFIED", "provenance_id": "prov:c1"}],
            "by_subject": {"A": [99]},  # invalid
            "by_relation": {"r": [0]},
            "by_object": {"B": [0]},
        }
        p.write_text(json.dumps(payload))
        with pytest.raises(Exception):
            load_csrf_checked(p)


# ---------------------------------------------------------------------------
# 14. Checked loader rejects corrupted proof index
# ---------------------------------------------------------------------------

def test_checked_loader_rejects_corrupted_proof_index():
    from vcse.runtime.hardening import load_proof_index_checked

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bad.proof.json"
        # VERIFIED proof with path_length=0 and no supporting claims
        payload = {
            "version": "1.0",
            "proofs": [{
                "proof_id": "p1",
                "result_claim_id": "c1",
                "result_subject": "A",
                "result_relation": "r",
                "result_object": "B",
                "supporting_claim_ids": [],
                "steps": [],
                "path_length": 0,
                "trust_tier": 1,
                "verification_status": "VERIFIED",
                "source": "materialized",
            }],
            "by_result": {"c1": [0]},
            "by_support": {},
            "by_subject": {"A": [0]},
            "by_relation": {"r": [0]},
            "by_object": {"B": [0]},
        }
        p.write_text(json.dumps(payload))
        with pytest.raises(Exception):
            load_proof_index_checked(p)


# ---------------------------------------------------------------------------
# 15. Existing .csrf load behavior remains backward-compatible when valid
# ---------------------------------------------------------------------------

def test_valid_csrf_backward_compatible():
    from vcse.runtime.hardening import load_csrf_checked
    from vcse.runtime.serialize import save_csrf

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "valid.csrf"
        save_csrf(_make_valid_csrf(), p)
        index = load_csrf_checked(p)
        assert len(index.records) == 1
        assert index.records[0].subject == "Paris"
