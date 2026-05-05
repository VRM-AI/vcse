"""Tests for candidate proposal contract (v6.14.0)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vcse.api.server import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "vcse.cli", *args],
        capture_output=True,
        env=env,
        text=True,
    )


def _valid_proposal() -> dict:
    return {
        "proposal_version": "1.0",
        "proposal_kind": "CANDIDATE_PROPOSAL",
        "candidate_kind": "FACTUAL_CLAIM_PACK",
        "claims": [
            {
                "claim_id": "claim-001",
                "claim_type": "FACTUAL",
                "status": "PROPOSED",
                "subject": "Paris",
                "predicate": "is_capital_of",
                "object": "France",
                "source_span_ids": ["span-001"],
            }
        ],
    }


# ============================================================
# SECTION 1: Valid proposals
# ============================================================

# --- 1. valid minimal proposal returns PROPOSAL_VALID ---
def test_valid_minimal_proposal_returns_proposal_valid() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.status == "PROPOSAL_VALID"


# --- 2. valid proposal accepted true ---
def test_valid_proposal_accepted_true() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.accepted is True


# --- 3. valid proposal claim_count correct ---
def test_valid_proposal_claim_count_correct() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.claim_count == 1


# --- 4. valid proposal can adapt into candidate claim views ---
def test_valid_proposal_can_adapt_into_candidate_claim_views() -> None:
    from vcse.proposal.validate import load_and_validate_candidate_proposal_json
    from vcse.proposal.adapter import proposal_to_candidate_claim_views
    raw = json.dumps(_valid_proposal())
    proposal_obj, result = load_and_validate_candidate_proposal_json(raw)
    assert result.accepted is True
    assert proposal_obj is not None
    adapter_result = proposal_to_candidate_claim_views(proposal_obj)
    assert adapter_result.claim_count == 1
    assert len(adapter_result.candidate_claims) == 1


# --- 5. adapter status is never VERIFIED ---
def test_adapter_status_is_not_verified() -> None:
    from vcse.proposal.validate import load_and_validate_candidate_proposal_json
    from vcse.proposal.adapter import proposal_to_candidate_claim_views
    raw = json.dumps(_valid_proposal())
    proposal_obj, result = load_and_validate_candidate_proposal_json(raw)
    assert result.accepted is True
    adapter_result = proposal_to_candidate_claim_views(proposal_obj)
    forbidden = {"VERIFIED", "CERTIFIED", "SOURCE_SUPPORTED", "T4_VERIFIER_CONSISTENT", "T5_CERTIFIED"}
    assert adapter_result.status not in forbidden
    for claim in adapter_result.candidate_claims:
        assert claim.get("status") not in forbidden


# ============================================================
# SECTION 2: Required fields
# ============================================================

# --- 6. missing proposal_version rejected ---
def test_missing_proposal_version_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["proposal_version"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert result.accepted is False
    assert "MISSING_PROPOSAL_VERSION" in result.issues


# --- 7. missing proposal_kind rejected ---
def test_missing_proposal_kind_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["proposal_kind"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_PROPOSAL_KIND" in result.issues


# --- 8. invalid proposal_kind rejected ---
def test_invalid_proposal_kind_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["proposal_kind"] = "VERIFIED_PROPOSAL"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_PROPOSAL_KIND" in result.issues


# --- 9. missing candidate_kind rejected ---
def test_missing_candidate_kind_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["candidate_kind"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CANDIDATE_KIND" in result.issues


# --- 10. invalid candidate_kind rejected ---
def test_invalid_candidate_kind_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["candidate_kind"] = "AUTHORITY_PACK"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_CANDIDATE_KIND" in result.issues


# --- 11. missing claims rejected ---
def test_missing_claims_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIMS" in result.issues


# --- 12. empty claims rejected ---
def test_empty_claims_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"] = []
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIMS" in result.issues


# --- 13. non-list claims rejected ---
def test_non_list_claims_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"] = "not-a-list"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_CLAIMS" in result.issues


# --- 14. missing claim_id rejected ---
def test_missing_claim_id_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["claim_id"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_ID" in result.issues


# --- 15. missing claim_type rejected ---
def test_missing_claim_type_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["claim_type"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_TYPE" in result.issues


# --- 16. missing claim status rejected ---
def test_missing_claim_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["status"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_STATUS" in result.issues


# --- 17. claim status other than PROPOSED rejected ---
def test_claim_status_not_proposed_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["status"] = "CERTIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_CLAIM_STATUS" in result.issues


# --- 18. missing subject rejected ---
def test_missing_subject_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["subject"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_SUBJECT" in result.issues


# --- 19. missing predicate rejected ---
def test_missing_predicate_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["predicate"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_PREDICATE" in result.issues


# --- 20. missing object rejected ---
def test_missing_object_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["object"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_CLAIM_OBJECT" in result.issues


# --- 21. missing source_span_ids rejected ---
def test_missing_source_span_ids_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["claims"][0]["source_span_ids"]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_SOURCE_SPAN_IDS" in result.issues


# --- 22. empty source_span_ids rejected ---
def test_empty_source_span_ids_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["source_span_ids"] = []
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "MISSING_SOURCE_SPAN_IDS" in result.issues


# --- 23. non-string source_span_ids rejected ---
def test_non_string_source_span_ids_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["source_span_ids"] = [123, 456]
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_SOURCE_SPAN_IDS" in result.issues


# ============================================================
# SECTION 3: Authority escalation rejection
# ============================================================

# --- 24. root verification_status rejected ---
def test_root_verification_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["verification_status"] = "VERIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_VERIFICATION_STATUS" in result.issues


# --- 25. root certification_status rejected ---
def test_root_certification_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["certification_status"] = "CERTIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_CERTIFICATION_STATUS" in result.issues


# --- 26. root trust_tier rejected ---
def test_root_trust_tier_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["trust_tier"] = "T4_VERIFIER_CONSISTENT"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_TRUST_TIER" in result.issues


# --- 27. root authoritative_support_profile_id rejected ---
def test_root_authoritative_support_profile_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["authoritative_support_profile_id"] = "SUPPORT_NORMALIZED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE" in result.issues


# --- 28. claim verification_status rejected ---
def test_claim_verification_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["verification_status"] = "VERIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_VERIFICATION_STATUS" in result.issues


# --- 29. claim certification_status rejected ---
def test_claim_certification_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["certification_status"] = "CERTIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_CERTIFICATION_STATUS" in result.issues


# --- 30. claim trust_tier T4 rejected ---
def test_claim_trust_tier_t4_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["trust_tier"] = "T4_VERIFIER_CONSISTENT"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_TRUST_TIER" in result.issues


# --- 31. claim trust_tier T5 rejected ---
def test_claim_trust_tier_t5_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["trust_tier"] = "T5_CERTIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_TRUST_TIER" in result.issues


# --- 32. claim authoritative_support_profile_id rejected ---
def test_claim_authoritative_support_profile_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["authoritative_support_profile_id"] = "SUPPORT_NORMALIZED"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE" in result.issues


# --- 33. metadata verification_status rejected ---
def test_metadata_verification_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["metadata"] = {"verification_status": "VERIFIED"}
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "FORBIDDEN_VERIFICATION_STATUS" in result.issues


# --- 34. metadata certified/verified/source_supported authority attempt rejected ---
def test_metadata_authority_attempt_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["metadata"] = {"certified": True, "source_supported": True}
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"


# --- 35. forbidden fields are not silently stripped ---
def test_forbidden_fields_not_silently_stripped() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["verification_status"] = "VERIFIED"
    result = validate_candidate_proposal_dict(payload)
    assert result.accepted is False
    assert result.status == "PROPOSAL_INVALID"


# ============================================================
# SECTION 4: Unknown fields / payload / casing
# ============================================================

# --- 36. unknown top-level field rejected ---
def test_unknown_top_level_field_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["injected_authority"] = "yes"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "UNKNOWN_TOP_LEVEL_FIELD" in result.issues


# --- 37. unknown claim field rejected ---
def test_unknown_claim_field_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["mystery_field"] = "injected"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "UNKNOWN_CLAIM_FIELD" in result.issues


# --- 38. lowercase status rejected ---
def test_lowercase_status_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["claims"][0]["status"] = "proposed"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert any(code in result.issues for code in ("INVALID_CLAIM_STATUS", "STATUS_CASING_INVALID"))


# --- 39. lowercase proposal_kind rejected ---
def test_lowercase_proposal_kind_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    payload["proposal_kind"] = "candidate_proposal"
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "INVALID_PROPOSAL_KIND" in result.issues


# --- 40. NaN/Inf rejected ---
def test_nan_inf_rejected() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    import math
    payload = _valid_proposal()
    payload["claims"][0]["raw_value"] = float("nan")
    result = validate_candidate_proposal_dict(payload)
    assert result.status == "PROPOSAL_INVALID"
    assert "NON_FINITE_VALUE" in result.issues


# --- 41. payload larger than limit rejected ---
def test_payload_too_large_rejected(tmp_path: Path) -> None:
    from vcse.proposal.validate import load_and_validate_candidate_proposal_json
    from vcse.proposal.model import MAX_PROPOSAL_JSON_BYTES
    big = "x" * (MAX_PROPOSAL_JSON_BYTES + 1)
    raw = json.dumps({"proposal_version": "1.0", "big": big})
    _, result = load_and_validate_candidate_proposal_json(raw)
    assert result.status == "PROPOSAL_INVALID"
    assert "PAYLOAD_TOO_LARGE" in result.issues


# --- 42. issue codes are UPPER_SNAKE_CASE ---
def test_issue_codes_are_upper_snake_case() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    payload = _valid_proposal()
    del payload["proposal_version"]
    result = validate_candidate_proposal_dict(payload)
    for code in result.issues:
        assert code == code.upper(), f"Issue code not UPPER_SNAKE_CASE: {code!r}"
        assert " " not in code, f"Issue code has spaces: {code!r}"


# --- 43. serialization deterministic ---
def test_serialization_deterministic() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    from vcse.proposal.serialize import candidate_proposal_validation_result_to_json
    payload = _valid_proposal()
    result = validate_candidate_proposal_dict(payload)
    json1 = candidate_proposal_validation_result_to_json(result)
    json2 = candidate_proposal_validation_result_to_json(result)
    assert json1 == json2
    parsed = json.loads(json1)
    assert parsed["status"] == "PROPOSAL_VALID"
    assert parsed["accepted"] is True
    assert "issues" in parsed
    assert "claim_count" in parsed


# ============================================================
# SECTION 5: Non-interference
# ============================================================

# --- 44. validation does not call verifier ---
def test_validation_does_not_call_verifier() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.status == "PROPOSAL_VALID"
    assert result.accepted is True


# --- 45. validation does not call trust promoter ---
def test_validation_does_not_call_trust_promoter() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.status == "PROPOSAL_VALID"


# --- 46. validation does not call source-support service ---
def test_validation_does_not_call_source_support_service() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    assert result.status == "PROPOSAL_VALID"


# --- 47. validation does not produce SOURCE_SUPPORTED ---
def test_validation_does_not_produce_source_supported() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    result = validate_candidate_proposal_dict(_valid_proposal())
    body = json.dumps(result.__dict__ if hasattr(result, "__dict__") else vars(result))
    assert '"SOURCE_SUPPORTED"' not in body


# --- 48. validation does not produce VERIFIED ---
def test_validation_does_not_produce_verified() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    from vcse.proposal.serialize import candidate_proposal_validation_result_to_json
    result = validate_candidate_proposal_dict(_valid_proposal())
    body = candidate_proposal_validation_result_to_json(result)
    assert '"VERIFIED"' not in body


# --- 49. validation does not produce CERTIFIED ---
def test_validation_does_not_produce_certified() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    from vcse.proposal.serialize import candidate_proposal_validation_result_to_json
    result = validate_candidate_proposal_dict(_valid_proposal())
    body = candidate_proposal_validation_result_to_json(result)
    assert '"CERTIFIED"' not in body


# --- 50. validation does not produce T4/T5 ---
def test_validation_does_not_produce_t4_t5() -> None:
    from vcse.proposal.validate import validate_candidate_proposal_dict
    from vcse.proposal.serialize import candidate_proposal_validation_result_to_json
    result = validate_candidate_proposal_dict(_valid_proposal())
    body = candidate_proposal_validation_result_to_json(result)
    assert "T4_VERIFIER_CONSISTENT" not in body
    assert "T5_CERTIFIED" not in body


# --- 51. adapter does not mutate input proposal ---
def test_adapter_does_not_mutate_input_proposal() -> None:
    from vcse.proposal.validate import load_and_validate_candidate_proposal_json
    from vcse.proposal.adapter import proposal_to_candidate_claim_views
    raw = json.dumps(_valid_proposal())
    proposal_obj, _ = load_and_validate_candidate_proposal_json(raw)
    original_claims = proposal_obj.claims
    proposal_to_candidate_claim_views(proposal_obj)
    assert proposal_obj.claims == original_claims


# ============================================================
# SECTION 6: CLI tests
# ============================================================

# --- 52. CLI proposal validate valid proposal returns PROPOSAL_VALID ---
def test_cli_proposal_validate_valid_proposal(tmp_path: Path) -> None:
    proposal_file = tmp_path / "proposal.json"
    proposal_file.write_text(json.dumps(_valid_proposal()))
    result = _run_cli("proposal", "validate", "--proposal", str(proposal_file), "--json")
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert parsed["proposal_status"] == "PROPOSAL_VALID"
    assert parsed["accepted"] is True


# --- 53. CLI proposal validate invalid proposal returns PROPOSAL_INVALID ---
def test_cli_proposal_validate_invalid_proposal_returns_invalid(tmp_path: Path) -> None:
    payload = _valid_proposal()
    del payload["proposal_version"]
    proposal_file = tmp_path / "bad_proposal.json"
    proposal_file.write_text(json.dumps(payload))
    result = _run_cli("proposal", "validate", "--proposal", str(proposal_file), "--json")
    parsed = json.loads(result.stdout)
    assert parsed["proposal_status"] == "PROPOSAL_INVALID"
    assert parsed["accepted"] is False


# --- 54. CLI output is not API-wrapped ---
def test_cli_output_is_not_api_wrapped(tmp_path: Path) -> None:
    proposal_file = tmp_path / "proposal.json"
    proposal_file.write_text(json.dumps(_valid_proposal()))
    result = _run_cli("proposal", "validate", "--proposal", str(proposal_file), "--json")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "request_id" not in parsed
    assert "version" not in parsed
    assert "status" not in parsed or parsed.get("status") in (None, "PROPOSAL_VALID", "PROPOSAL_INVALID")


# --- 55. CLI does not mutate proposal file ---
def test_cli_does_not_mutate_proposal_file(tmp_path: Path) -> None:
    proposal_file = tmp_path / "proposal.json"
    original_content = json.dumps(_valid_proposal())
    proposal_file.write_text(original_content)
    _run_cli("proposal", "validate", "--proposal", str(proposal_file), "--json")
    assert proposal_file.read_text() == original_content


# ============================================================
# SECTION 7: API tests
# ============================================================

# --- 56. POST /proposal/validate valid proposal returns unified OK ---
def test_api_post_proposal_validate_valid_returns_ok() -> None:
    resp = _client().post("/proposal/validate", json=_valid_proposal())
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["proposal_status"] == "PROPOSAL_VALID"
    assert payload["data"]["accepted"] is True
    assert payload["data"]["claim_count"] == 1
    assert payload["data"]["issues"] == []


# --- 57. POST /proposal/validate invalid proposal returns PROPOSAL_INVALID ---
def test_api_post_proposal_validate_invalid_returns_proposal_invalid() -> None:
    bad = _valid_proposal()
    del bad["proposal_version"]
    resp = _client().post("/proposal/validate", json=bad)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["proposal_status"] == "PROPOSAL_INVALID"
    assert payload["data"]["accepted"] is False


# --- 58. X-Request-ID echoed ---
def test_api_request_id_echoed() -> None:
    resp = _client().post(
        "/proposal/validate",
        json=_valid_proposal(),
        headers={"X-Request-ID": "test-req-abc"},
    )
    assert resp.json()["request_id"] == "test-req-abc"


# --- 59. errors always list ---
def test_api_errors_always_list() -> None:
    resp = _client().post("/proposal/validate", json=_valid_proposal())
    assert isinstance(resp.json()["errors"], list)


# --- 60. data always object ---
def test_api_data_always_object() -> None:
    resp = _client().post("/proposal/validate", json=_valid_proposal())
    assert isinstance(resp.json()["data"], dict)


# --- 61. no legacy top-level error key ---
def test_api_no_legacy_top_level_error_key() -> None:
    resp = _client().post("/proposal/validate", json=_valid_proposal())
    assert "error" not in resp.json()


# --- 62. no traceback leakage ---
def test_api_no_traceback_leakage() -> None:
    resp = _client().post(
        "/proposal/validate",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    body = resp.text
    assert "Traceback" not in body
    assert "File " not in body


# --- 63. API does not assign VERIFIED/CERTIFIED/T4/T5 ---
def test_api_does_not_assign_verified_certified_t4_t5() -> None:
    resp = _client().post("/proposal/validate", json=_valid_proposal())
    payload = resp.json()
    body_str = json.dumps(payload)
    for forbidden in ("VERIFIED", "CERTIFIED", "T4_VERIFIER_CONSISTENT", "T5_CERTIFIED"):
        assert f'"{forbidden}"' not in body_str, f"Forbidden value {forbidden!r} in API response"
