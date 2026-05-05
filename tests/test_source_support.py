"""Tests for deterministic source support contracts (v6.12.0)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vcse.api.server import create_app
from vcse.support import (
    EXPLORATORY_SUPPORT_PROFILE,
    FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE,
    FINAL_STATUS_INVALID_ONTOLOGY_RELATION,
    FINAL_STATUS_NEEDS_ONTOLOGY,
    FINAL_STATUS_NEEDS_SOURCE,
    FINAL_STATUS_SOURCE_SUPPORTED,
    FINAL_STATUS_SOURCE_SUPPORT_FAILED,
    FINAL_STATUS_UNKNOWN_SOURCE_SPAN,
    SUPPORT_AGENT_PROPOSED,
    SUPPORT_EXACT,
    SUPPORT_NORMALIZED,
    SUPPORT_RULE_DERIVED,
    ActiveRelationView,
    CandidateClaimView,
    SourceSpan,
    evaluate_source_support,
    source_support_decision_to_dict,
    source_support_decision_to_json,
)
from vcse.support.validate import (
    validate_active_relation_view,
    validate_candidate_claim_view,
    validate_source_span,
)


# --- Fixtures ---

def _span(span_id: str, text: str, source_id: str = "src-001") -> SourceSpan:
    return SourceSpan(source_id=source_id, source_span_id=span_id, text=text)


def _claim(
    subject: str = "Alice",
    relation: str = "knows",
    obj: str = "Bob",
    span_ids: tuple[str, ...] = ("span-1",),
) -> CandidateClaimView:
    return CandidateClaimView(
        claim_id="c-test",
        subject=subject,
        relation=relation,
        object=obj,
        source_span_ids=span_ids,
    )


def _relation(profile: str = SUPPORT_EXACT, relation_id: str = "knows") -> ActiveRelationView:
    return ActiveRelationView(relation_id=relation_id, support_profile_id=profile)


def _spans(*args: SourceSpan) -> dict[str, SourceSpan]:
    return {s.source_span_id: s for s in args}


def _relations(*args: ActiveRelationView) -> dict[str, ActiveRelationView]:
    return {r.relation_id: r for r in args}


def _client() -> TestClient:
    return TestClient(create_app())


# --- 1. Grounded span is NOT automatically SOURCE_SUPPORTED ---
def test_grounded_is_not_source_supported() -> None:
    claim = _claim(subject="Alice", obj="Bob", span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    relation = _relation(SUPPORT_EXACT)
    decision = evaluate_source_support(claim, _spans(span), _relations(relation))
    # Grounded (span exists) — but we verify it actually ran a profile check
    # If SUPPORT_EXACT passes, status is SOURCE_SUPPORTED; that's correct
    # The doctrine test: grounded alone doesn't grant SOURCE_SUPPORTED
    # Test the case where span exists but text doesn't support claim
    claim2 = _claim(subject="Charlie", obj="Dave", span_ids=("span-1",))
    decision2 = evaluate_source_support(claim2, _spans(span), _relations(relation))
    assert decision2.final_status == FINAL_STATUS_SOURCE_SUPPORT_FAILED
    assert decision2.supported is False


# --- 2. Missing source_span_ids returns NEEDS_SOURCE ---
def test_missing_source_span_ids_returns_needs_source() -> None:
    claim = CandidateClaimView(claim_id="c1", subject="A", relation="r", object="B", source_span_ids=())
    decision = evaluate_source_support(claim, {}, {})
    assert decision.final_status == FINAL_STATUS_NEEDS_SOURCE
    assert decision.supported is False


# --- 3. Unknown source_span_id returns UNKNOWN_SOURCE_SPAN ---
def test_unknown_source_span_returns_unknown() -> None:
    claim = _claim(span_ids=("nonexistent-span",))
    decision = evaluate_source_support(claim, {}, _relations(_relation()))
    assert decision.final_status == FINAL_STATUS_UNKNOWN_SOURCE_SPAN
    assert decision.supported is False


# --- 4. Unknown relation returns NEEDS_ONTOLOGY ---
def test_unknown_relation_returns_needs_ontology() -> None:
    claim = _claim(relation="unknown_relation", span_ids=("span-1",))
    span = _span("span-1", "some text")
    decision = evaluate_source_support(claim, _spans(span), {})
    assert decision.final_status == FINAL_STATUS_NEEDS_ONTOLOGY
    assert decision.supported is False


# --- 5. Active relation missing support_profile_id returns INVALID_ONTOLOGY_RELATION ---
def test_missing_support_profile_id_returns_invalid_ontology() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    bad_relation = ActiveRelationView(relation_id="knows", support_profile_id="")
    decision = evaluate_source_support(claim, _spans(span), _relations(bad_relation))
    assert decision.final_status == FINAL_STATUS_INVALID_ONTOLOGY_RELATION
    assert decision.supported is False


# --- 6. Unknown support_profile_id returns INVALID_ONTOLOGY_RELATION ---
def test_unknown_support_profile_returns_invalid_ontology() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    bad_relation = ActiveRelationView(relation_id="knows", support_profile_id="FUZZY_SEMANTIC_MATCH")
    decision = evaluate_source_support(claim, _spans(span), _relations(bad_relation))
    assert decision.final_status == FINAL_STATUS_INVALID_ONTOLOGY_RELATION
    assert decision.supported is False


# --- 7. SUPPORT_EXACT passes exact literal support ---
def test_support_exact_passes_literal() -> None:
    claim = _claim(subject="Alice", obj="Bob", span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob in this context.")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORTED
    assert decision.supported is True


# --- 8. SUPPORT_EXACT fails paraphrase / unsupported object ---
def test_support_exact_fails_paraphrase() -> None:
    claim = _claim(subject="Alice", obj="Carol", span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORT_FAILED
    assert decision.supported is False


# --- 9. SUPPORT_NORMALIZED passes deterministic casing/whitespace normalization ---
def test_support_normalized_passes_case_fold() -> None:
    claim = _claim(subject="alice", obj="bob", span_ids=("span-1",))
    span = _span("span-1", "ALICE  knows   BOB")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_NORMALIZED)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORTED
    assert decision.supported is True


# --- 10. SUPPORT_NORMALIZED passes simple deterministic whitespace normalization ---
def test_support_normalized_passes_whitespace() -> None:
    claim = _claim(subject="production deployments", obj="500ms", span_ids=("span-1",))
    span = _span("span-1", "All  production   deployments must use  500ms verifier timeout.")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_NORMALIZED)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORTED
    assert decision.supported is True


# --- 11. SUPPORT_NORMALIZED fails unsupported semantic drift ---
def test_support_normalized_fails_semantic_drift() -> None:
    claim = _claim(subject="Alice", obj="Carol", span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_NORMALIZED)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORT_FAILED
    assert decision.supported is False


# --- 12. SUPPORT_RULE_DERIVED does not fake support when rule/proof data absent ---
def test_support_rule_derived_fails_without_rule_data() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_RULE_DERIVED)))
    assert decision.final_status == FINAL_STATUS_SOURCE_SUPPORT_FAILED
    assert decision.supported is False


# --- 13. SUPPORT_AGENT_PROPOSED cannot emit SOURCE_SUPPORTED ---
def test_support_agent_proposed_cannot_emit_source_supported() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_AGENT_PROPOSED)))
    assert decision.final_status != FINAL_STATUS_SOURCE_SUPPORTED
    assert decision.supported is False


# --- 14. EXPLORATORY_SUPPORT_PROFILE emits EXPLORATORY_SUPPORT_CANDIDATE only ---
def test_exploratory_profile_emits_candidate_only() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(EXPLORATORY_SUPPORT_PROFILE)))
    assert decision.final_status == FINAL_STATUS_EXPLORATORY_SUPPORT_CANDIDATE
    assert decision.supported is False


# --- 15. SOURCE_SUPPORTED decision never emits VERIFIED ---
def test_source_supported_never_emits_verified() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    d = source_support_decision_to_dict(decision)
    assert "VERIFIED" not in d.values()
    assert "VERIFIED" not in str(d)


# --- 16. SOURCE_SUPPORTED decision never emits CERTIFIED ---
def test_source_supported_never_emits_certified() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    d = source_support_decision_to_dict(decision)
    assert "CERTIFIED" not in str(d)


# --- 17. Decision serialization is deterministic ---
def test_decision_serialization_deterministic() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    j1 = source_support_decision_to_json(decision)
    j2 = source_support_decision_to_json(decision)
    assert j1 == j2
    parsed = json.loads(j1)
    assert isinstance(parsed, dict)


# --- 18. No lowercase statuses/reason codes ---
def test_no_lowercase_statuses_or_reason_codes() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    decision = evaluate_source_support(claim, _spans(span), _relations(_relation(SUPPORT_EXACT)))
    assert decision.final_status == decision.final_status.upper()
    assert decision.reason_code == decision.reason_code.upper()


# --- 19. Service does not mutate inputs ---
def test_service_does_not_mutate_inputs() -> None:
    claim = _claim(span_ids=("span-1",))
    span = _span("span-1", "Alice knows Bob")
    spans = _spans(span)
    relations = _relations(_relation(SUPPORT_EXACT))
    original_span_text = span.text
    original_span_ids = claim.source_span_ids
    evaluate_source_support(claim, spans, relations)
    assert span.text == original_span_text
    assert claim.source_span_ids == original_span_ids


# --- 20. NaN/Inf in metadata is caught during serialization ---
def test_nan_inf_in_metadata_blocked() -> None:
    from vcse.support.serialize import _assert_json_safe
    with pytest.raises(ValueError, match="NON_FINITE_VALUE"):
        _assert_json_safe({"value": math.nan})
    with pytest.raises(ValueError, match="NON_FINITE_VALUE"):
        _assert_json_safe({"value": math.inf})


# --- 21 (API): POST /support/evaluate exact success returns unified contract ---
def test_api_support_evaluate_exact_success() -> None:
    resp = _client().post("/support/evaluate", json={
        "claim": {
            "claim_id": "c1",
            "subject": "production deployments",
            "relation": "requires_timeout",
            "object": "500ms",
            "source_span_ids": ["span_001"],
        },
        "source_spans": [
            {
                "source_id": "src_policy_001",
                "source_span_id": "span_001",
                "text": "All production deployments must use a 500ms verifier timeout.",
            }
        ],
        "active_relations": [
            {
                "relation_id": "requires_timeout",
                "support_profile_id": "SUPPORT_NORMALIZED",
            }
        ],
    })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert "support_status" in payload["data"]
    assert payload["data"]["support_status"] == FINAL_STATUS_SOURCE_SUPPORTED
    assert payload["data"]["supported"] is True


# --- 22 (API): POST /support/evaluate unknown relation returns OK with NEEDS_ONTOLOGY ---
def test_api_support_evaluate_unknown_relation() -> None:
    resp = _client().post("/support/evaluate", json={
        "claim": {
            "claim_id": "c2",
            "subject": "A",
            "relation": "unknown_rel",
            "object": "B",
            "source_span_ids": ["span_001"],
        },
        "source_spans": [{"source_id": "s1", "source_span_id": "span_001", "text": "A unknown_rel B"}],
        "active_relations": [],
    })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "OK"
    assert payload["data"]["support_status"] == FINAL_STATUS_NEEDS_ONTOLOGY


# --- 23 (API): X-Request-ID is echoed ---
def test_api_support_evaluate_echoes_request_id() -> None:
    resp = _client().post(
        "/support/evaluate",
        json={
            "claim": {"claim_id": "c3", "subject": "A", "relation": "r", "object": "B"},
            "source_spans": [],
            "active_relations": [],
        },
        headers={"X-Request-ID": "support-test-789"},
    )
    assert resp.json()["request_id"] == "support-test-789"
    assert resp.headers.get("X-Request-ID") == "support-test-789"


# --- 24 (API): errors is always list ---
def test_api_support_evaluate_errors_always_list() -> None:
    resp = _client().post("/support/evaluate", json={
        "claim": {"claim_id": "c4", "subject": "A", "relation": "r", "object": "B"},
    })
    assert isinstance(resp.json()["errors"], list)


# --- 25 (API): data is always object ---
def test_api_support_evaluate_data_always_object() -> None:
    resp = _client().post("/support/evaluate", json={
        "claim": {"claim_id": "c5", "subject": "A", "relation": "r", "object": "B"},
    })
    assert isinstance(resp.json()["data"], dict)


# --- 26 (CLI): vcse support evaluate returns expected JSON ---
def test_cli_support_evaluate_returns_json(tmp_path: Path) -> None:
    from vcse.cli import run_support_evaluate

    claim_file = tmp_path / "claim.json"
    spans_file = tmp_path / "spans.json"
    relations_file = tmp_path / "relations.json"

    claim_file.write_text(json.dumps({
        "claim_id": "cli-c1",
        "subject": "Alice",
        "relation": "knows",
        "object": "Bob",
        "source_span_ids": ["span-cli-1"],
    }), encoding="utf-8")

    spans_file.write_text(json.dumps([{
        "source_id": "src-cli",
        "source_span_id": "span-cli-1",
        "text": "Alice knows Bob in the system.",
    }]), encoding="utf-8")

    relations_file.write_text(json.dumps([{
        "relation_id": "knows",
        "support_profile_id": "SUPPORT_EXACT",
    }]), encoding="utf-8")

    output = run_support_evaluate(claim_file, spans_file, relations_file, json_output=True)
    parsed = json.loads(output)
    assert parsed["final_status"] == "SOURCE_SUPPORTED"
    assert parsed["supported"] is True


# --- 27 (CLI): CLI output is not API-wrapped ---
def test_cli_support_evaluate_not_api_wrapped(tmp_path: Path) -> None:
    from vcse.cli import run_support_evaluate

    claim_file = tmp_path / "claim.json"
    spans_file = tmp_path / "spans.json"
    relations_file = tmp_path / "relations.json"

    claim_file.write_text(json.dumps({
        "claim_id": "cli-c2", "subject": "A", "relation": "r", "object": "B",
        "source_span_ids": [],
    }), encoding="utf-8")
    spans_file.write_text("[]", encoding="utf-8")
    relations_file.write_text("[]", encoding="utf-8")

    output = run_support_evaluate(claim_file, spans_file, relations_file, json_output=True)
    parsed = json.loads(output)
    # Not API-wrapped — no "status", "version", "request_id", "errors" fields
    assert "status" not in parsed or parsed.get("final_status") is not None
    assert "version" not in parsed
    assert "request_id" not in parsed
    assert "errors" not in parsed


def test_validate_source_span_rejects_missing_text() -> None:
    issues = validate_source_span({"source_id": "s1", "source_span_id": "span-1"})
    codes = {i.code for i in issues}
    assert "MISSING_SOURCE_TEXT" in codes


def test_validate_source_span_rejects_non_string_text() -> None:
    issues = validate_source_span({"source_id": "s1", "source_span_id": "span-1", "text": 42})
    codes = {i.code for i in issues}
    assert "INVALID_SOURCE_TEXT" in codes


def test_validate_candidate_claim_view_rejects_missing_subject() -> None:
    issues = validate_candidate_claim_view({"claim_id": "c1", "relation": "r", "object": "B"})
    codes = {i.code for i in issues}
    assert "MISSING_CLAIM_SUBJECT" in codes


def test_validate_candidate_claim_view_rejects_missing_object() -> None:
    issues = validate_candidate_claim_view({"claim_id": "c1", "subject": "A", "relation": "r"})
    codes = {i.code for i in issues}
    assert "MISSING_CLAIM_OBJECT" in codes


def test_validate_candidate_claim_view_rejects_missing_relation() -> None:
    issues = validate_candidate_claim_view({"claim_id": "c1", "subject": "A", "object": "B"})
    codes = {i.code for i in issues}
    assert "MISSING_CLAIM_RELATION" in codes


def test_validate_active_relation_view_rejects_missing_relation_id() -> None:
    issues = validate_active_relation_view({"support_profile_id": "SUPPORT_EXACT"})
    codes = {i.code for i in issues}
    assert "MISSING_RELATION_ID" in codes


def test_validate_active_relation_view_rejects_missing_support_profile_id() -> None:
    issues = validate_active_relation_view({"relation_id": "knows"})
    codes = {i.code for i in issues}
    assert "MISSING_SUPPORT_PROFILE" in codes


def test_validate_active_relation_view_rejects_invalid_support_profile_id() -> None:
    issues = validate_active_relation_view({"relation_id": "knows", "support_profile_id": "BAD_PROFILE"})
    codes = {i.code for i in issues}
    assert "INVALID_SUPPORT_PROFILE" in codes


def test_validation_issue_codes_are_upper_snake_case() -> None:
    issues = []
    issues.extend(validate_source_span({}))
    issues.extend(validate_candidate_claim_view({}))
    issues.extend(validate_active_relation_view({}))
    assert issues
    for issue in issues:
        assert issue.code == issue.code.upper()


def test_cli_support_evaluate_rejects_malformed_semantic_input(tmp_path: Path) -> None:
    from vcse.cli import run_support_evaluate

    claim_file = tmp_path / "claim_bad.json"
    spans_file = tmp_path / "spans_bad.json"
    relations_file = tmp_path / "relations_bad.json"

    claim_file.write_text(json.dumps({
        "claim_id": "cli-bad-1",
        "subject": "",
        "relation": "knows",
        "object": "Bob",
        "source_span_ids": ["span-cli-1"],
    }), encoding="utf-8")

    spans_file.write_text(json.dumps([{
        "source_id": "src-cli",
        "source_span_id": "span-cli-1",
        "text": "Alice knows Bob",
    }]), encoding="utf-8")

    relations_file.write_text(json.dumps([{
        "relation_id": "knows",
        "support_profile_id": "SUPPORT_EXACT",
    }]), encoding="utf-8")

    with pytest.raises(ValueError, match="INVALID_SUPPORT_INPUT"):
        run_support_evaluate(claim_file, spans_file, relations_file, json_output=True)
