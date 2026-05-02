from __future__ import annotations

import json
import math

from vcse.cmcf import (
    CMCFIntegrity,
    CMCFRecord,
    claim_dict_to_cmcf,
    compute_claim_id,
    record_from_dict,
    record_from_json,
    record_to_dict,
    record_to_json,
    validate_record,
)
from vcse.cmcf.hash import compute_content_hash


def _valid_record() -> CMCFRecord:
    return claim_dict_to_cmcf(
        {"subject": "France", "relation": "has_capital", "object": "Paris"},
        source_type="manual",
        source_uri="file://fixture",
        locator="row:1",
        raw_value='{"subject":"France","relation":"has_capital","object":"Paris"}',
    )


def test_cmcf_record_serializes_deterministically() -> None:
    record = _valid_record()
    assert record_to_json(record) == record_to_json(record)


def test_same_claim_provenance_produces_same_claim_id() -> None:
    record_a = _valid_record()
    record_b = _valid_record()
    assert record_a.claim.claim_id == record_b.claim.claim_id


def test_changed_object_produces_different_claim_id() -> None:
    first = compute_claim_id("France", "has_capital", "Paris")
    second = compute_claim_id("France", "has_capital", "Lyon")
    assert first != second


def test_missing_provenance_fails_validation() -> None:
    record = _valid_record()
    broken = CMCFRecord(
        cmcf_version=record.cmcf_version,
        claim=record.claim,
        provenance=type(record.provenance)(
            provenance_id="",
            source_type="",
            source_uri=None,
            retrieved_at=None,
            content_hash=None,
            locator=None,
            raw_value=None,
            method=record.provenance.method,
            mapping_id=None,
        ),
        status=record.status,
        trust=record.trust,
        integrity=record.integrity,
        metadata=record.metadata,
    )
    issues = validate_record(broken)
    codes = {item.code for item in issues}
    assert "PROVENANCE_REQUIRED" in codes
    assert "PROVENANCE_ID_REQUIRED" in codes


def test_invalid_lifecycle_status_fails_validation() -> None:
    record = _valid_record()
    broken = CMCFRecord(
        cmcf_version=record.cmcf_version,
        claim=record.claim,
        provenance=record.provenance,
        status=type(record.status)(
            lifecycle_status="invalid",
            verification_status=record.status.verification_status,
            certification_status=record.status.certification_status,
            provenance_status=record.status.provenance_status,
            policy_status=record.status.policy_status,
        ),
        trust=record.trust,
        integrity=record.integrity,
        metadata=record.metadata,
    )
    assert any(issue.code == "LIFECYCLE_STATUS_INVALID" for issue in validate_record(broken))


def test_invalid_verification_status_fails_validation() -> None:
    record = _valid_record()
    broken = CMCFRecord(
        cmcf_version=record.cmcf_version,
        claim=record.claim,
        provenance=record.provenance,
        status=type(record.status)(
            lifecycle_status=record.status.lifecycle_status,
            verification_status="MAYBE",
            certification_status=record.status.certification_status,
            provenance_status=record.status.provenance_status,
            policy_status=record.status.policy_status,
        ),
        trust=record.trust,
        integrity=record.integrity,
        metadata=record.metadata,
    )
    assert any(issue.code == "VERIFICATION_STATUS_INVALID" for issue in validate_record(broken))


def test_nan_inf_rejected_by_serialization_or_validation() -> None:
    record = _valid_record()
    payload = record_to_dict(record)
    payload["trust"]["trust_tier"] = math.inf
    try:
        record_from_dict(payload)
    except ValueError:
        assert True
    else:
        assert False


def test_claim_dict_to_cmcf_supports_subject_relation_object() -> None:
    record = claim_dict_to_cmcf(
        {"subject": "France", "relation": "has_capital", "object": "Paris"},
        source_type="manual",
    )
    assert record.claim.subject == "France"
    assert record.claim.relation == "has_capital"
    assert record.claim.object == "Paris"


def test_claim_dict_to_cmcf_supports_entity_relation_value() -> None:
    record = claim_dict_to_cmcf(
        {"entity": "France", "relation": "has_capital", "value": "Paris"},
        source_type="manual",
    )
    assert record.claim.subject == "France"
    assert record.claim.object == "Paris"


def test_content_hash_recomputation_is_stable() -> None:
    record = _valid_record()
    payload = record_to_dict(record)
    expected = compute_content_hash(
        {
            "cmcf_version": payload["cmcf_version"],
            "claim": payload["claim"],
            "provenance": payload["provenance"],
            "status": payload["status"],
            "trust": payload["trust"],
            "metadata": payload["metadata"],
        }
    )
    assert expected == record.integrity.content_hash


def test_cmcf_json_roundtrip_preserves_record() -> None:
    record = _valid_record()
    encoded = record_to_json(record)
    decoded = record_from_json(encoded)
    assert decoded == record


def test_candidate_record_defaults_are_usable() -> None:
    record = _valid_record()
    assert record.status.lifecycle_status == "candidate"
    assert record.status.verification_status == "UNVERIFIED"
    assert record.status.certification_status == "NOT_CERTIFIED"


def test_signed_fields_may_be_null_in_candidate() -> None:
    record = _valid_record()
    assert record.integrity.signature is None
    assert record.integrity.signing_key_id is None


def test_validation_issues_are_deterministic() -> None:
    record = _valid_record()
    payload = record_to_dict(record)
    payload["status"]["policy_status"] = "NOT_A_STATUS"
    broken = record_from_dict(payload)
    first = [issue.code for issue in validate_record(broken)]
    second = [issue.code for issue in validate_record(broken)]
    assert first == second
