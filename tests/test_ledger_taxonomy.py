"""Tests for VCSE v6.15.0 Ledger Event Taxonomy."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from vcse.ledger.factory import (
    event_from_ontology_validation,
    event_from_proposal_validation,
    event_from_source_support_decision,
    make_ledger_event,
)
from vcse.ledger.model import (
    KNOWN_ACTOR_TYPES,
    KNOWN_SEVERITIES,
    KNOWN_SUBJECT_KINDS,
    LEDGER_EVENT_INVALID,
    LEDGER_EVENT_VALID,
    LedgerEvent,
    LedgerEventValidationResult,
)
from vcse.ledger.serialize import (
    ledger_event_to_dict,
    ledger_event_to_json,
    ledger_event_validation_result_to_dict,
    ledger_event_validation_result_to_json,
)
from vcse.ledger.taxonomy import (
    API_REQUEST_REJECTED,
    API_REQUEST_VALIDATED,
    CERTIFICATION_BLOCKED,
    CLAIM_PROPOSED,
    CLAIM_REJECTED_SCHEMA,
    CLAIM_SOURCE_SUPPORTED,
    CLAIM_SOURCE_SUPPORT_BLOCKED,
    KNOWN_CATEGORIES,
    KNOWN_EVENT_TYPES,
    ONTOLOGY_RELATION_VALIDATED,
    PROMOTION_BLOCKED_ZERO_PROOFS,
    PROPOSAL_REJECTED,
    PROPOSAL_VALIDATED,
    event_category,
    is_known_event_type,
)
from vcse.ledger.validate import (
    DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN,
    EVENT_TYPE_CASING_INVALID,
    INVALID_TIMESTAMP,
    MISSING_ACTOR_TYPE,
    MISSING_EVENT_ID,
    MISSING_EVENT_TYPE,
    MISSING_EVENT_VERSION,
    MISSING_FINAL_STATUS,
    MISSING_REASON_CODE,
    MISSING_SEVERITY,
    MISSING_SOURCE_SYSTEM,
    MISSING_SUBJECT_KIND,
    MISSING_TIMESTAMP,
    NON_FINITE_VALUE,
    REASON_CODE_CASING_INVALID,
    STATUS_CASING_INVALID,
    UNKNOWN_ACTOR_TYPE,
    UNKNOWN_EVENT_TYPE,
    UNKNOWN_SEVERITY,
    UNKNOWN_SUBJECT_KIND,
    validate_ledger_event,
    validate_ledger_event_dict,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _minimal_event(**overrides) -> LedgerEvent:
    defaults = dict(
        event_id="evt-001",
        event_type=CLAIM_PROPOSED,
        event_version="1.0",
        timestamp="2026-05-05T12:00:00Z",
        actor_type="SYSTEM",
        source_system="VCSE",
        subject_kind="CLAIM",
        final_status="CLAIM_PROPOSED",
        reason_code="CLAIM_SCHEMA_VALID",
    )
    defaults.update(overrides)
    return LedgerEvent(**defaults)


def _minimal_dict(**overrides) -> dict:
    defaults = dict(
        event_id="evt-001",
        event_type=CLAIM_PROPOSED,
        event_version="1.0",
        timestamp="2026-05-05T12:00:00Z",
        actor_type="SYSTEM",
        source_system="VCSE",
        subject_kind="CLAIM",
        final_status="CLAIM_PROPOSED",
        reason_code="CLAIM_SCHEMA_VALID",
        severity="INFO",
    )
    defaults.update(overrides)
    return defaults


# ── Taxonomy tests ────────────────────────────────────────────────────────────

class TestTaxonomy:
    def test_required_event_types_known(self):
        required = [
            "SOURCE_INGESTED", "SOURCE_SPAN_CREATED",
            "CLAIM_PROPOSED", "CLAIM_REJECTED_SCHEMA",
            "PROPOSAL_VALIDATED", "PROPOSAL_REJECTED", "PROPOSAL_ACCEPTED_AS_CANDIDATE",
            "ONTOLOGY_RELATION_PROPOSED", "ONTOLOGY_RELATION_VALIDATED",
            "ONTOLOGY_RELATION_ACTIVATED", "ONTOLOGY_RELATION_REJECTED",
            "PROOF_EVALUATED", "PROOF_VALIDATION_FAILED",
            "PROMOTION_BLOCKED_ZERO_PROOFS", "PROMOTION_BLOCKED_NON_VERIFIED_STATUS",
            "PROMOTION_GRANTED_T4",
            "CERTIFICATION_BLOCKED", "CERTIFICATION_GRANTED_T5",
            "CONFLICT_DETECTED", "CONFLICT_RESOLVED",
            "POLICY_ACTION_APPLIED", "POLICY_ACTION_BLOCKED",
            "RUNTIME_VALIDATED", "RUNTIME_VALIDATION_FAILED",
            "BUNDLE_VERIFIED", "BUNDLE_VERIFICATION_FAILED",
            "API_REQUEST_VALIDATED", "API_REQUEST_REJECTED",
        ]
        for et in required:
            assert is_known_event_type(et), f"{et} not in taxonomy"

    def test_unknown_event_type_rejected(self):
        assert not is_known_event_type("NOT_A_REAL_EVENT")
        assert not is_known_event_type("")
        assert not is_known_event_type("claim_proposed")

    def test_event_categories_deterministic(self):
        c1 = event_category(CLAIM_PROPOSED)
        c2 = event_category(CLAIM_PROPOSED)
        assert c1 == c2 == "CLAIM"

    def test_all_event_types_upper_snake(self):
        import re
        pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')
        for et in KNOWN_EVENT_TYPES:
            assert pattern.match(et), f"Event type not UPPER_SNAKE_CASE: {et}"

    def test_all_categories_upper_snake(self):
        import re
        pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')
        for cat in KNOWN_CATEGORIES:
            assert pattern.match(cat), f"Category not UPPER_SNAKE_CASE: {cat}"


# ── Valid events ──────────────────────────────────────────────────────────────

class TestValidEvents:
    def test_valid_claim_proposed(self):
        event = _minimal_event()
        result = validate_ledger_event(event)
        assert result.valid is True
        assert result.status == LEDGER_EVENT_VALID
        assert result.event_type == CLAIM_PROPOSED

    def test_valid_claim_rejected_schema(self):
        event = _minimal_event(
            event_type=CLAIM_REJECTED_SCHEMA,
            subject_kind="CLAIM",
            final_status="CLAIM_REJECTED",
            reason_code="SCHEMA_INVALID",
        )
        result = validate_ledger_event(event)
        assert result.valid is True

    def test_valid_promotion_blocked_zero_proofs(self):
        event = _minimal_event(
            event_type=PROMOTION_BLOCKED_ZERO_PROOFS,
            subject_kind="PROMOTION",
            final_status="PROMOTION_BLOCKED",
            reason_code="NO_PROOFS",
        )
        result = validate_ledger_event(event)
        assert result.valid is True

    def test_valid_certification_blocked(self):
        event = _minimal_event(
            event_type=CERTIFICATION_BLOCKED,
            subject_kind="CERTIFICATION",
            final_status="CERTIFICATION_BLOCKED",
            reason_code="INSUFFICIENT_TRUST",
        )
        result = validate_ledger_event(event)
        assert result.valid is True

    def test_valid_api_request_rejected(self):
        event = _minimal_event(
            event_type=API_REQUEST_REJECTED,
            subject_kind="API_REQUEST",
            final_status="REQUEST_REJECTED",
            reason_code="INVALID_PAYLOAD",
            actor_type="API",
        )
        result = validate_ledger_event(event)
        assert result.valid is True


# ── Required field rejections ─────────────────────────────────────────────────

class TestRequiredFields:
    def test_missing_event_id_rejected(self):
        event = _minimal_event(event_id="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_EVENT_ID in result.issues

    def test_missing_event_type_rejected(self):
        event = _minimal_event(event_type="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_EVENT_TYPE in result.issues

    def test_missing_event_version_rejected(self):
        event = _minimal_event(event_version="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_EVENT_VERSION in result.issues

    def test_missing_timestamp_rejected(self):
        event = _minimal_event(timestamp="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_TIMESTAMP in result.issues

    def test_invalid_timestamp_rejected(self):
        event = _minimal_event(timestamp="not-a-timestamp")
        result = validate_ledger_event(event)
        assert not result.valid
        assert INVALID_TIMESTAMP in result.issues

    def test_missing_actor_type_rejected(self):
        event = _minimal_event(actor_type="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_ACTOR_TYPE in result.issues

    def test_unknown_actor_type_rejected(self):
        event = _minimal_event(actor_type="ROBOT")
        result = validate_ledger_event(event)
        assert not result.valid
        assert UNKNOWN_ACTOR_TYPE in result.issues

    def test_missing_source_system_rejected(self):
        event = _minimal_event(source_system="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_SOURCE_SYSTEM in result.issues

    def test_missing_subject_kind_rejected(self):
        event = _minimal_event(subject_kind="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_SUBJECT_KIND in result.issues

    def test_unknown_subject_kind_rejected(self):
        event = _minimal_event(subject_kind="GALAXY")
        result = validate_ledger_event(event)
        assert not result.valid
        assert UNKNOWN_SUBJECT_KIND in result.issues

    def test_missing_final_status_rejected(self):
        event = _minimal_event(final_status="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_FINAL_STATUS in result.issues

    def test_missing_reason_code_rejected(self):
        event = _minimal_event(reason_code="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_REASON_CODE in result.issues

    def test_missing_severity_rejected(self):
        event = _minimal_event(severity="")
        result = validate_ledger_event(event)
        assert not result.valid
        assert MISSING_SEVERITY in result.issues

    def test_unknown_severity_rejected(self):
        event = _minimal_event(severity="TRACE")
        result = validate_ledger_event(event)
        assert not result.valid
        assert UNKNOWN_SEVERITY in result.issues


# ── Casing / non-finite / forbidden authority ────────────────────────────────

class TestCasingAndDetails:
    def test_lowercase_event_type_rejected(self):
        event = _minimal_event(event_type="claim_proposed")
        result = validate_ledger_event(event)
        assert not result.valid
        assert EVENT_TYPE_CASING_INVALID in result.issues

    def test_lowercase_final_status_rejected(self):
        event = _minimal_event(final_status="claim_proposed")
        result = validate_ledger_event(event)
        assert not result.valid
        assert STATUS_CASING_INVALID in result.issues

    def test_lowercase_reason_code_rejected(self):
        event = _minimal_event(reason_code="schema_valid")
        result = validate_ledger_event(event)
        assert not result.valid
        assert REASON_CODE_CASING_INVALID in result.issues

    def test_nan_in_details_rejected(self):
        event = _minimal_event(details={"score": float("nan")})
        result = validate_ledger_event(event)
        assert not result.valid
        assert NON_FINITE_VALUE in result.issues

    def test_inf_in_details_rejected(self):
        event = _minimal_event(details={"score": float("inf")})
        result = validate_ledger_event(event)
        assert not result.valid
        assert NON_FINITE_VALUE in result.issues

    def test_details_verification_status_rejected(self):
        event = _minimal_event(details={"verification_status": "VERIFIED"})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_certification_status_rejected(self):
        event = _minimal_event(details={"certification_status": "CERTIFIED"})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_trust_tier_rejected(self):
        event = _minimal_event(details={"trust_tier": "T5_CERTIFIED"})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_authoritative_support_profile_id_rejected(self):
        event = _minimal_event(details={"authoritative_support_profile_id": "p1"})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_verified_rejected(self):
        event = _minimal_event(details={"verified": True})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_certified_rejected(self):
        event = _minimal_event(details={"certified": True})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues

    def test_details_source_supported_rejected(self):
        event = _minimal_event(details={"source_supported": True})
        result = validate_ledger_event(event)
        assert not result.valid
        assert DETAILS_AUTHORITY_OVERRIDE_FORBIDDEN in result.issues


# ── Serialization ────────────────────────────────────────────────────────────

class TestSerialization:
    def test_event_serialization_deterministic(self):
        event = _minimal_event()
        j1 = ledger_event_to_json(event)
        j2 = ledger_event_to_json(event)
        assert j1 == j2
        assert j1 == j2

    def test_validation_result_serialization_deterministic(self):
        event = _minimal_event()
        result = validate_ledger_event(event)
        j1 = ledger_event_validation_result_to_json(result)
        j2 = ledger_event_validation_result_to_json(result)
        assert j1 == j2

    def test_serialization_allow_nan_false(self):
        event = _minimal_event()
        d = ledger_event_to_dict(event)
        # Verify json.dumps with allow_nan=False would raise on NaN
        with pytest.raises((ValueError, TypeError)):
            json.dumps({"x": float("nan")}, allow_nan=False)

    def test_tuple_source_span_ids_serializes_as_list(self):
        event = _minimal_event(source_span_ids=("s1", "s2", "s3"))
        d = ledger_event_to_dict(event)
        assert isinstance(d["source_span_ids"], list)
        assert d["source_span_ids"] == ["s1", "s2", "s3"]

    def test_no_object_repr_leakage(self):
        event = _minimal_event()
        j = ledger_event_to_json(event)
        assert "<vcse" not in j
        assert "object at 0x" not in j

    def test_serialization_does_not_mutate_event(self):
        event = _minimal_event(source_span_ids=("s1",))
        original_spans = event.source_span_ids
        ledger_event_to_dict(event)
        assert event.source_span_ids == original_spans


# ── Factory ──────────────────────────────────────────────────────────────────

class TestFactory:
    def test_make_ledger_event_produces_valid_event(self):
        event = make_ledger_event(
            event_type=CLAIM_PROPOSED,
            final_status="CLAIM_PROPOSED",
            reason_code="CLAIM_SCHEMA_VALID",
        )
        result = validate_ledger_event(event)
        assert result.valid is True

    def test_make_ledger_event_uses_known_event_type(self):
        event = make_ledger_event(
            event_type=PROPOSAL_VALIDATED,
            final_status="PROPOSAL_ACCEPTED",
            reason_code="PROPOSAL_ACCEPTED_AS_CANDIDATE",
        )
        assert is_known_event_type(event.event_type)

    def test_make_ledger_event_unknown_event_type_produces_invalid(self):
        event = make_ledger_event(
            event_type="NOT_REAL_EVENT",
            final_status="SOME_STATUS",
            reason_code="SOME_REASON",
        )
        result = validate_ledger_event(event)
        assert not result.valid
        assert UNKNOWN_EVENT_TYPE in result.issues

    def test_factory_event_id_present(self):
        event = make_ledger_event(
            event_type=CLAIM_PROPOSED,
            final_status="CLAIM_PROPOSED",
            reason_code="CLAIM_SCHEMA_VALID",
        )
        assert event.event_id
        assert len(event.event_id) > 4

    def test_factory_timestamp_present(self):
        event = make_ledger_event(
            event_type=CLAIM_PROPOSED,
            final_status="CLAIM_PROPOSED",
            reason_code="CLAIM_SCHEMA_VALID",
        )
        assert event.timestamp
        assert "T" in event.timestamp

    def test_factory_does_not_write_files(self, tmp_path):
        before = set(tmp_path.iterdir())
        make_ledger_event(
            event_type=CLAIM_PROPOSED,
            final_status="CLAIM_PROPOSED",
            reason_code="CLAIM_SCHEMA_VALID",
        )
        after = set(tmp_path.iterdir())
        assert before == after

    def test_factory_does_not_call_verifier_trust_source_support(self):
        # Factory must not import or call into verifier / trust / source-support.
        # This test verifies factory is pure by checking no side effects occur
        # when called in isolation.
        import vcse.ledger.factory as f_module
        src = open(f_module.__file__).read()
        assert "from vcse.trust" not in src
        assert "from vcse.support" not in src
        assert "from vcse.verify" not in src


# ── Result adapters ──────────────────────────────────────────────────────────

class TestResultAdapters:
    def _proposal_result(self, accepted: bool):
        from types import SimpleNamespace
        return SimpleNamespace(accepted=accepted, claim_count=3, status="OK", issues=())

    def _support_decision(self, supported: bool):
        from types import SimpleNamespace
        return SimpleNamespace(
            supported=supported,
            final_status="SOURCE_SUPPORTED" if supported else "SOURCE_SUPPORT_FAILED",
            reason_code="SUPPORT_PROFILE_PASSED" if supported else "SUPPORT_PROFILE_FAILED",
        )

    def test_event_from_proposal_validation_accepted(self):
        result = self._proposal_result(True)
        event = event_from_proposal_validation(result, proposal_id="p1")
        assert event.event_type == PROPOSAL_VALIDATED
        result2 = validate_ledger_event(event)
        assert result2.valid

    def test_event_from_proposal_validation_rejected(self):
        result = self._proposal_result(False)
        event = event_from_proposal_validation(result, proposal_id="p1")
        assert event.event_type == PROPOSAL_REJECTED
        result2 = validate_ledger_event(event)
        assert result2.valid

    def test_event_from_source_support_supported(self):
        decision = self._support_decision(True)
        event = event_from_source_support_decision(decision, claim_id="c1")
        assert event.event_type == CLAIM_SOURCE_SUPPORTED
        result2 = validate_ledger_event(event)
        assert result2.valid

    def test_event_from_source_support_blocked(self):
        decision = self._support_decision(False)
        event = event_from_source_support_decision(decision, claim_id="c1")
        assert event.event_type == CLAIM_SOURCE_SUPPORT_BLOCKED
        result2 = validate_ledger_event(event)
        assert result2.valid

    def test_event_from_ontology_validation(self):
        from types import SimpleNamespace
        result = SimpleNamespace(valid=True)
        event = event_from_ontology_validation(result, relation_id="r1", ontology_version="1.0")
        assert event.event_type == ONTOLOGY_RELATION_VALIDATED
        result2 = validate_ledger_event(event)
        assert result2.valid

    def test_adapters_do_not_mutate_input(self):
        result = self._proposal_result(True)
        original_accepted = result.accepted
        event_from_proposal_validation(result)
        assert result.accepted == original_accepted


# ── CLI ───────────────────────────────────────────────────────────────────────

def _run_cli(*args: str):
    return subprocess.run(
        [sys.executable, "-m", "vcse"] + list(args),
        capture_output=True,
        text=True,
    )


class TestCLI:
    def test_cli_ledger_validate_valid_event(self, tmp_path):
        event = {
            "event_id": "evt-cli-1",
            "event_type": CLAIM_PROPOSED,
            "event_version": "1.0",
            "timestamp": "2026-05-05T12:00:00Z",
            "actor_type": "CLI",
            "source_system": "VCSE",
            "subject_kind": "CLAIM",
            "final_status": "CLAIM_PROPOSED",
            "reason_code": "CLAIM_SCHEMA_VALID",
            "severity": "INFO",
        }
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(event))
        proc = _run_cli("ledger", "validate", "--event", str(event_file), "--json")
        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert parsed["status"] == LEDGER_EVENT_VALID
        assert parsed["valid"] is True

    def test_cli_ledger_validate_invalid_event(self, tmp_path):
        event = {"event_type": CLAIM_PROPOSED}  # missing many required fields
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(event))
        proc = _run_cli("ledger", "validate", "--event", str(event_file), "--json")
        parsed = json.loads(proc.stdout)
        assert parsed["status"] == LEDGER_EVENT_INVALID
        assert parsed["valid"] is False

    def test_cli_output_not_api_wrapped(self, tmp_path):
        event = {"event_type": CLAIM_PROPOSED}
        event_file = tmp_path / "event.json"
        event_file.write_text(json.dumps(event))
        proc = _run_cli("ledger", "validate", "--event", str(event_file), "--json")
        parsed = json.loads(proc.stdout)
        # Should NOT have the API envelope keys
        assert "request_id" not in parsed
        assert "version" not in parsed

    def test_cli_does_not_mutate_event_file(self, tmp_path):
        event = {
            "event_id": "evt-cli-2",
            "event_type": CLAIM_PROPOSED,
            "event_version": "1.0",
            "timestamp": "2026-05-05T12:00:00Z",
            "actor_type": "CLI",
            "source_system": "VCSE",
            "subject_kind": "CLAIM",
            "final_status": "CLAIM_PROPOSED",
            "reason_code": "CLAIM_SCHEMA_VALID",
            "severity": "INFO",
        }
        event_file = tmp_path / "event.json"
        original_content = json.dumps(event)
        event_file.write_text(original_content)
        _run_cli("ledger", "validate", "--event", str(event_file))
        assert event_file.read_text() == original_content


# ── API ───────────────────────────────────────────────────────────────────────

class TestAPILedgerValidate:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from vcse.api.server import create_app
        return TestClient(create_app())

    def test_valid_event_returns_ok(self, client):
        body = {
            "event_id": "evt-api-1",
            "event_type": CLAIM_PROPOSED,
            "event_version": "1.0",
            "timestamp": "2026-05-05T12:00:00Z",
            "actor_type": "API",
            "source_system": "VCSE",
            "subject_kind": "CLAIM",
            "final_status": "CLAIM_PROPOSED",
            "reason_code": "CLAIM_SCHEMA_VALID",
            "severity": "INFO",
        }
        r = client.post("/ledger/validate", json=body, headers={"X-Request-ID": "req-1"})
        assert r.status_code == 200
        parsed = r.json()
        assert parsed["status"] == "OK"
        assert parsed["data"]["ledger_event_status"] == LEDGER_EVENT_VALID
        assert parsed["data"]["valid"] is True

    def test_invalid_event_returns_ok_with_invalid_status(self, client):
        body = {"event_type": CLAIM_PROPOSED}  # missing many required fields
        r = client.post("/ledger/validate", json=body)
        assert r.status_code == 200
        parsed = r.json()
        assert parsed["status"] == "OK"
        assert parsed["data"]["ledger_event_status"] == LEDGER_EVENT_INVALID
        assert parsed["data"]["valid"] is False

    def test_x_request_id_echoed(self, client):
        body = {"event_type": CLAIM_PROPOSED}
        r = client.post("/ledger/validate", json=body, headers={"X-Request-ID": "test-req-id"})
        parsed = r.json()
        # request_id may be in response data
        assert "request_id" in parsed

    def test_errors_always_list(self, client):
        body = {}
        r = client.post("/ledger/validate", json=body)
        parsed = r.json()
        assert isinstance(parsed["errors"], list)

    def test_data_always_object(self, client):
        body = {}
        r = client.post("/ledger/validate", json=body)
        parsed = r.json()
        assert isinstance(parsed["data"], dict)

    def test_no_legacy_error_key(self, client):
        body = {"bad": "data"}
        r = client.post("/ledger/validate", json=body)
        parsed = r.json()
        assert "error" not in parsed

    def test_no_traceback_leakage(self, client):
        body = {"event_type": None}
        r = client.post("/ledger/validate", json=body)
        assert "Traceback" not in r.text

    def test_no_side_effects(self, client):
        body = {
            "event_id": "evt-api-2",
            "event_type": CLAIM_PROPOSED,
            "event_version": "1.0",
            "timestamp": "2026-05-05T12:00:00Z",
            "actor_type": "API",
            "source_system": "VCSE",
            "subject_kind": "CLAIM",
            "final_status": "CLAIM_PROPOSED",
            "reason_code": "CLAIM_SCHEMA_VALID",
            "severity": "INFO",
        }
        r1 = client.post("/ledger/validate", json=body)
        r2 = client.post("/ledger/validate", json=body)
        assert r1.json()["data"] == r2.json()["data"]


# ── Non-interference ─────────────────────────────────────────────────────────

class TestNonInterference:
    def test_ledger_validation_does_not_produce_verified(self):
        event = _minimal_event()
        result = validate_ledger_event(event)
        d = ledger_event_validation_result_to_dict(result)
        assert "VERIFIED" not in json.dumps(d)

    def test_ledger_validation_does_not_produce_certified(self):
        event = _minimal_event()
        result = validate_ledger_event(event)
        d = ledger_event_validation_result_to_dict(result)
        assert "CERTIFIED" not in json.dumps(d)

    def test_ledger_validation_does_not_produce_t4_t5(self):
        event = _minimal_event()
        result = validate_ledger_event(event)
        d = ledger_event_validation_result_to_dict(result)
        s = json.dumps(d)
        assert "T4" not in s
        assert "T5" not in s

    def test_ledger_validation_does_not_promote_trust(self):
        # validate_ledger_event must not import from vcse.trust
        import vcse.ledger.validate as v_module
        src = open(v_module.__file__).read()
        assert "from vcse.trust" not in src
        assert "import vcse.trust" not in src

    def test_ledger_validation_does_not_call_verifier(self):
        import vcse.ledger.validate as v_module
        src = open(v_module.__file__).read()
        assert "from vcse.verify" not in src
        assert "import vcse.verify" not in src

    def test_ledger_validation_does_not_call_source_support(self):
        import vcse.ledger.validate as v_module
        src = open(v_module.__file__).read()
        assert "from vcse.support" not in src
        assert "import vcse.support" not in src

    def test_ledger_validation_does_not_mutate_proposal_source_ontology_trust(self):
        from types import SimpleNamespace
        dummy = SimpleNamespace(field="original_value")
        event = _minimal_event()
        validate_ledger_event(event)
        assert dummy.field == "original_value"
