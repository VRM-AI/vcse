"""Tests for v6.16.0 Renderer Guard + Answer Verification."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vcse.api.server import create_app
from vcse.render import (
    CANONICAL_ONLY,
    CLAIM_STATUS_NOT_ALLOWED,
    DEFAULT_ALLOWED_CLAIM_STATUSES,
    EXPLICIT_ALLOWED_RENDERING,
    INVALID_RENDER_MODE,
    MISSING_ANSWER_ID,
    MISSING_CLAIM_REFS,
    MISSING_RENDERED_TEXT,
    NON_FINITE_VALUE,
    NORMALIZED_CANONICAL,
    RENDER_EXCEEDS_VALIDATED_MATERIAL,
    RENDER_GUARD_PASSED,
    RENDER_INVALID,
    RENDER_NEEDS_CLAIM_MAP,
    RENDER_VALID,
    RENDERED_TEXT_NOT_CANONICAL,
    SOURCE_SPAN_MISMATCH,
    UNKNOWN_CLAIM_ID,
    UNSUPPORTED_SEGMENT_PRESENT,
    AnswerClaimRef,
    AnswerDraft,
    RendererGuardDecision,
    RendererGuardPolicy,
    ValidatedClaimView,
    renderer_guard_decision_to_dict,
    renderer_guard_decision_to_json,
    verify_rendered_answer,
)


# --- Fixtures ---

def _view(
    claim_id: str = "c-001",
    canonical_text: str = "Alice knows Bob.",
    final_status: str = "VERIFIED",
    source_span_ids: tuple[str, ...] = ("span-1",),
    allowed_renderings: tuple[str, ...] = (),
    subject: str = "Alice",
    relation: str = "knows",
    obj: str = "Bob",
) -> ValidatedClaimView:
    return ValidatedClaimView(
        claim_id=claim_id,
        subject=subject,
        relation=relation,
        object=obj,
        canonical_text=canonical_text,
        final_status=final_status,
        source_span_ids=source_span_ids,
        allowed_renderings=allowed_renderings,
    )


def _ref(
    claim_id: str = "c-001",
    rendered_text: str = "Alice knows Bob.",
    source_span_ids: tuple[str, ...] = (),
) -> AnswerClaimRef:
    return AnswerClaimRef(
        claim_id=claim_id,
        rendered_text=rendered_text,
        source_span_ids=source_span_ids,
    )


def _draft(
    answer_id: str = "a-001",
    render_mode: str = CANONICAL_ONLY,
    rendered_text: str = "Alice knows Bob.",
    claim_refs: tuple[AnswerClaimRef, ...] = (),
    unsupported_segments: tuple[str, ...] = (),
) -> AnswerDraft:
    if not claim_refs:
        claim_refs = (_ref(),)
    return AnswerDraft(
        answer_id=answer_id,
        render_mode=render_mode,
        rendered_text=rendered_text,
        claim_refs=claim_refs,
        unsupported_segments=unsupported_segments,
    )


def _views(**kwargs) -> dict[str, ValidatedClaimView]:
    v = _view(**kwargs)
    return {v.claim_id: v}


def _client() -> TestClient:
    return TestClient(create_app())


# --- 1. Model construction ---

def test_validated_claim_view_construction() -> None:
    v = _view()
    assert v.claim_id == "c-001"
    assert v.final_status == "VERIFIED"
    assert isinstance(v.source_span_ids, tuple)


def test_answer_draft_construction() -> None:
    d = _draft()
    assert d.answer_id == "a-001"
    assert d.render_mode == CANONICAL_ONLY
    assert isinstance(d.claim_refs, tuple)


def test_renderer_guard_decision_construction() -> None:
    dec = RendererGuardDecision(
        answer_id="a-001",
        final_status=RENDER_VALID,
        valid=True,
        reason_code=RENDER_GUARD_PASSED,
        issues=(),
        claim_count=1,
        accepted_claim_ids=("c-001",),
        rejected_claim_ids=(),
        render_mode=CANONICAL_ONLY,
    )
    assert dec.valid is True


# --- 2. Deterministic serialization ---

def test_serialization_sort_keys() -> None:
    dec = RendererGuardDecision(
        answer_id="a-001", final_status=RENDER_VALID, valid=True,
        reason_code=RENDER_GUARD_PASSED, issues=(), claim_count=1,
        accepted_claim_ids=("c-001",), rejected_claim_ids=(), render_mode=CANONICAL_ONLY,
    )
    d = renderer_guard_decision_to_dict(dec)
    keys = list(d.keys())
    assert keys == sorted(keys)


def test_serialization_to_json() -> None:
    dec = RendererGuardDecision(
        answer_id="a-001", final_status=RENDER_VALID, valid=True,
        reason_code=RENDER_GUARD_PASSED, issues=(), claim_count=1,
        accepted_claim_ids=("c-001",), rejected_claim_ids=(), render_mode=CANONICAL_ONLY,
    )
    s = renderer_guard_decision_to_json(dec)
    parsed = json.loads(s)
    assert parsed["final_status"] == RENDER_VALID
    assert parsed["valid"] is True


def test_serialization_tuples_as_lists() -> None:
    dec = RendererGuardDecision(
        answer_id="a-001", final_status=RENDER_VALID, valid=True,
        reason_code=RENDER_GUARD_PASSED, issues=("x",), claim_count=1,
        accepted_claim_ids=("c-001",), rejected_claim_ids=("c-002",), render_mode=CANONICAL_ONLY,
    )
    d = renderer_guard_decision_to_dict(dec)
    assert isinstance(d["accepted_claim_ids"], list)
    assert isinstance(d["rejected_claim_ids"], list)
    assert isinstance(d["issues"], list)


# --- 3. NaN/Inf rejection ---

def test_nan_in_metadata_rejected() -> None:
    draft = AnswerDraft(
        answer_id="a-001",
        render_mode=CANONICAL_ONLY,
        rendered_text="Alice knows Bob.",
        claim_refs=(_ref(),),
        unsupported_segments=(),
        metadata={"score": float("nan")},
    )
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_INVALID
    assert decision.reason_code == NON_FINITE_VALUE
    assert decision.valid is False


def test_inf_in_metadata_rejected() -> None:
    draft = AnswerDraft(
        answer_id="a-001",
        render_mode=CANONICAL_ONLY,
        rendered_text="Alice knows Bob.",
        claim_refs=(_ref(),),
        unsupported_segments=(),
        metadata={"score": float("inf")},
    )
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_INVALID
    assert decision.reason_code == NON_FINITE_VALUE


# --- 4. Missing answer_id rejected ---

def test_missing_answer_id_rejected() -> None:
    draft = _draft(answer_id="")
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_INVALID
    assert decision.reason_code == MISSING_ANSWER_ID
    assert decision.valid is False


def test_whitespace_answer_id_rejected() -> None:
    draft = _draft(answer_id="   ")
    decision = verify_rendered_answer(draft, _views())
    assert decision.reason_code == MISSING_ANSWER_ID


# --- 5. Missing rendered_text rejected ---

def test_missing_rendered_text_rejected() -> None:
    draft = _draft(rendered_text="")
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_INVALID
    assert decision.reason_code == MISSING_RENDERED_TEXT


# --- 6. Missing claim_refs rejected ---

def test_empty_claim_refs_rejected() -> None:
    draft = AnswerDraft(
        answer_id="a-001",
        render_mode=CANONICAL_ONLY,
        rendered_text="Alice knows Bob.",
        claim_refs=(),
    )
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_NEEDS_CLAIM_MAP
    assert decision.reason_code == MISSING_CLAIM_REFS
    assert decision.valid is False


# --- 7. Unknown claim id rejected ---

def test_unknown_claim_id_rejected() -> None:
    draft = _draft(claim_refs=(_ref(claim_id="c-999"),))
    decision = verify_rendered_answer(draft, _views())
    assert decision.valid is False
    assert decision.reason_code == UNKNOWN_CLAIM_ID
    assert "c-999" in decision.rejected_claim_ids


# --- 8. Unsupported_segments rejected ---

def test_unsupported_segments_rejected() -> None:
    draft = _draft(unsupported_segments=("This fact has no backing.",))
    decision = verify_rendered_answer(draft, _views())
    assert decision.final_status == RENDER_EXCEEDS_VALIDATED_MATERIAL
    assert decision.reason_code == UNSUPPORTED_SEGMENT_PRESENT
    assert decision.valid is False


def test_multiple_unsupported_segments_all_reported() -> None:
    draft = _draft(unsupported_segments=("seg1", "seg2"))
    decision = verify_rendered_answer(draft, _views())
    assert decision.reason_code == UNSUPPORTED_SEGMENT_PRESENT
    assert len(decision.issues) == 2


# --- 9. Default allowed statuses accept VERIFIED/CERTIFIED ---

def test_verified_status_accepted_by_default() -> None:
    draft = _draft()
    decision = verify_rendered_answer(draft, _views(final_status="VERIFIED"))
    assert decision.final_status == RENDER_VALID
    assert decision.valid is True


def test_certified_status_accepted_by_default() -> None:
    draft = _draft()
    decision = verify_rendered_answer(draft, _views(final_status="CERTIFIED"))
    assert decision.final_status == RENDER_VALID
    assert decision.valid is True


# --- 10. Default allowed statuses reject SOURCE_SUPPORTED ---

def test_source_supported_rejected_by_default() -> None:
    draft = _draft()
    decision = verify_rendered_answer(draft, _views(final_status="SOURCE_SUPPORTED"))
    assert decision.valid is False
    assert decision.reason_code == CLAIM_STATUS_NOT_ALLOWED


# --- 11. Explicit allowed SOURCE_SUPPORTED policy ---

def test_source_supported_allowed_by_explicit_policy() -> None:
    policy = RendererGuardPolicy(allowed_claim_statuses=frozenset({"SOURCE_SUPPORTED"}))
    draft = _draft()
    decision = verify_rendered_answer(draft, _views(final_status="SOURCE_SUPPORTED"), policy=policy)
    assert decision.valid is True
    assert decision.final_status == RENDER_VALID


# --- 12. SOURCE_SUPPORTED never becomes VERIFIED/CERTIFIED ---

def test_source_supported_never_becomes_verified() -> None:
    policy = RendererGuardPolicy(allowed_claim_statuses=frozenset({"SOURCE_SUPPORTED"}))
    draft = _draft()
    decision = verify_rendered_answer(draft, _views(final_status="SOURCE_SUPPORTED"), policy=policy)
    assert decision.final_status not in ("VERIFIED", "CERTIFIED")
    d = renderer_guard_decision_to_dict(decision)
    assert d["final_status"] not in ("VERIFIED", "CERTIFIED")


# --- 13. Canonical exact rendering passes ---

def test_canonical_exact_match_passes() -> None:
    draft = _draft(
        render_mode=CANONICAL_ONLY,
        claim_refs=(_ref(rendered_text="Alice knows Bob."),),
    )
    decision = verify_rendered_answer(draft, _views(canonical_text="Alice knows Bob."))
    assert decision.valid is True
    assert decision.final_status == RENDER_VALID


# --- 14. Non-canonical rendering fails ---

def test_non_canonical_rendering_fails() -> None:
    draft = _draft(
        render_mode=CANONICAL_ONLY,
        claim_refs=(_ref(rendered_text="alice knows bob."),),
    )
    decision = verify_rendered_answer(draft, _views(canonical_text="Alice knows Bob."))
    assert decision.valid is False
    assert decision.reason_code == RENDERED_TEXT_NOT_CANONICAL


# --- 15. Normalized canonical mode ---

def test_normalized_canonical_passes_with_whitespace() -> None:
    draft = _draft(
        render_mode=NORMALIZED_CANONICAL,
        claim_refs=(_ref(rendered_text="Alice  knows   Bob."),),
    )
    decision = verify_rendered_answer(draft, _views(canonical_text="Alice knows Bob."))
    assert decision.valid is True


def test_normalized_canonical_fails_on_case_difference() -> None:
    draft = _draft(
        render_mode=NORMALIZED_CANONICAL,
        claim_refs=(_ref(rendered_text="alice knows bob."),),
    )
    decision = verify_rendered_answer(draft, _views(canonical_text="Alice knows Bob."))
    assert decision.valid is False


# --- 16. Explicit allowed rendering ---

def test_explicit_allowed_rendering_passes() -> None:
    views = {
        "c-001": _view(
            canonical_text="Alice knows Bob.",
            allowed_renderings=("Alice is acquainted with Bob.",),
        )
    }
    draft = _draft(
        render_mode=EXPLICIT_ALLOWED_RENDERING,
        claim_refs=(_ref(rendered_text="Alice is acquainted with Bob."),),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is True


def test_explicit_allowed_rendering_canonical_also_passes() -> None:
    views = {
        "c-001": _view(
            canonical_text="Alice knows Bob.",
            allowed_renderings=("Alice is acquainted with Bob.",),
        )
    }
    draft = _draft(
        render_mode=EXPLICIT_ALLOWED_RENDERING,
        claim_refs=(_ref(rendered_text="Alice knows Bob."),),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is True


def test_explicit_allowed_rendering_unknown_text_fails() -> None:
    views = {
        "c-001": _view(
            canonical_text="Alice knows Bob.",
            allowed_renderings=("Alice is acquainted with Bob.",),
        )
    }
    draft = _draft(
        render_mode=EXPLICIT_ALLOWED_RENDERING,
        claim_refs=(_ref(rendered_text="Alice met Bob."),),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is False


# --- 17. Source span mismatch fails ---

def test_source_span_mismatch_fails() -> None:
    views = {
        "c-001": _view(source_span_ids=("span-1", "span-2"))
    }
    draft = _draft(
        claim_refs=(_ref(source_span_ids=("span-99",)),),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is False
    assert decision.reason_code == SOURCE_SPAN_MISMATCH


def test_source_span_subset_passes() -> None:
    views = {
        "c-001": _view(source_span_ids=("span-1", "span-2"))
    }
    draft = _draft(
        claim_refs=(_ref(source_span_ids=("span-1",)),),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is True


# --- 18. Service does not mutate input ---

def test_service_does_not_mutate_draft() -> None:
    draft = _draft()
    views = _views()
    original_refs = draft.claim_refs
    verify_rendered_answer(draft, views)
    assert draft.claim_refs is original_refs


def test_service_does_not_mutate_views() -> None:
    views = _views()
    original_view = views["c-001"]
    verify_rendered_answer(_draft(), views)
    assert views["c-001"] is original_view


# --- 19. No verifier/trust/source-support calls ---

def test_render_package_does_not_import_verifier() -> None:
    import vcse.render.service as svc
    import inspect
    src = inspect.getsource(svc)
    assert "vcse.trust" not in src
    assert "vcse.verifier" not in src
    assert "vcse.support.service" not in src
    assert "vcse.proof" not in src


# --- 20. Invalid render mode rejected ---

def test_invalid_render_mode_rejected() -> None:
    draft = _draft(render_mode="FUZZY_MATCH")
    decision = verify_rendered_answer(draft, _views())
    assert decision.valid is False
    assert decision.reason_code == INVALID_RENDER_MODE


# --- 21. CLI tests ---

def test_cli_valid_json_output(tmp_path: Path) -> None:
    from vcse.cli import run_render_verify

    answer_data = {
        "answer_id": "a-cli-001",
        "render_mode": "CANONICAL_ONLY",
        "rendered_text": "Alice knows Bob.",
        "claim_refs": [{"claim_id": "c-001", "rendered_text": "Alice knows Bob.", "role": "primary"}],
        "unsupported_segments": [],
    }
    claims_data = [
        {
            "claim_id": "c-001",
            "subject": "Alice",
            "relation": "knows",
            "object": "Bob",
            "canonical_text": "Alice knows Bob.",
            "final_status": "VERIFIED",
            "source_span_ids": [],
        }
    ]
    answer_path = tmp_path / "answer.json"
    claims_path = tmp_path / "claims.json"
    answer_path.write_text(json.dumps(answer_data))
    claims_path.write_text(json.dumps(claims_data))

    result = run_render_verify(answer_path, claims_path, json_output=True)
    parsed = json.loads(result)
    assert parsed["final_status"] == "RENDER_VALID"
    assert parsed["valid"] is True


def test_cli_invalid_input_behavior(tmp_path: Path) -> None:
    from vcse.cli import run_render_verify

    answer_path = tmp_path / "answer.json"
    claims_path = tmp_path / "claims.json"
    answer_path.write_text("{not valid json")
    claims_path.write_text("[]")

    result = run_render_verify(answer_path, claims_path, json_output=True)
    parsed = json.loads(result)
    assert parsed["final_status"] == "RENDER_INVALID"
    assert parsed["valid"] is False


def test_cli_human_output(tmp_path: Path) -> None:
    from vcse.cli import run_render_verify

    answer_data = {
        "answer_id": "a-cli-002",
        "render_mode": "CANONICAL_ONLY",
        "rendered_text": "Alice knows Bob.",
        "claim_refs": [{"claim_id": "c-001", "rendered_text": "Alice knows Bob.", "role": "primary"}],
        "unsupported_segments": [],
    }
    claims_data = [
        {
            "claim_id": "c-001",
            "subject": "Alice", "relation": "knows", "object": "Bob",
            "canonical_text": "Alice knows Bob.", "final_status": "VERIFIED",
        }
    ]
    answer_path = tmp_path / "answer.json"
    claims_path = tmp_path / "claims.json"
    answer_path.write_text(json.dumps(answer_data))
    claims_path.write_text(json.dumps(claims_data))

    result = run_render_verify(answer_path, claims_path, json_output=False)
    assert "RENDER_VALID" in result
    assert "valid: True" in result


# --- 22. API /render/verify unified response contract ---

def test_api_render_verify_valid() -> None:
    client = _client()
    payload = {
        "answer": {
            "answer_id": "a-api-001",
            "render_mode": "CANONICAL_ONLY",
            "rendered_text": "Alice knows Bob.",
            "claim_refs": [
                {"claim_id": "c-001", "rendered_text": "Alice knows Bob.", "role": "primary"}
            ],
            "unsupported_segments": [],
        },
        "claims": [
            {
                "claim_id": "c-001",
                "subject": "Alice",
                "relation": "knows",
                "object": "Bob",
                "canonical_text": "Alice knows Bob.",
                "final_status": "VERIFIED",
            }
        ],
    }
    resp = client.post("/render/verify", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OK"
    assert "decision" in body["data"]
    assert body["data"]["decision"]["final_status"] == "RENDER_VALID"
    assert body["data"]["decision"]["valid"] is True


def test_api_render_verify_invalid_claim_status() -> None:
    client = _client()
    payload = {
        "answer": {
            "answer_id": "a-api-002",
            "render_mode": "CANONICAL_ONLY",
            "rendered_text": "Alice knows Bob.",
            "claim_refs": [
                {"claim_id": "c-001", "rendered_text": "Alice knows Bob.", "role": "primary"}
            ],
        },
        "claims": [
            {
                "claim_id": "c-001",
                "subject": "Alice",
                "relation": "knows",
                "object": "Bob",
                "canonical_text": "Alice knows Bob.",
                "final_status": "SOURCE_SUPPORTED",
            }
        ],
    }
    resp = client.post("/render/verify", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["decision"]["valid"] is False
    assert body["data"]["decision"]["reason_code"] == "CLAIM_STATUS_NOT_ALLOWED"


def test_api_render_verify_unsupported_segment() -> None:
    client = _client()
    payload = {
        "answer": {
            "answer_id": "a-api-003",
            "render_mode": "CANONICAL_ONLY",
            "rendered_text": "Alice knows Bob. And some extra claim.",
            "claim_refs": [
                {"claim_id": "c-001", "rendered_text": "Alice knows Bob.", "role": "primary"}
            ],
            "unsupported_segments": ["And some extra claim."],
        },
        "claims": [
            {
                "claim_id": "c-001",
                "subject": "Alice",
                "relation": "knows",
                "object": "Bob",
                "canonical_text": "Alice knows Bob.",
                "final_status": "VERIFIED",
            }
        ],
    }
    resp = client.post("/render/verify", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["decision"]["valid"] is False
    assert body["data"]["decision"]["reason_code"] == "UNSUPPORTED_SEGMENT_PRESENT"


def test_api_x_request_id_echo() -> None:
    client = _client()
    payload = {
        "answer": {
            "answer_id": "a-req-id",
            "render_mode": "CANONICAL_ONLY",
            "rendered_text": "Alice knows Bob.",
            "claim_refs": [{"claim_id": "c-001", "rendered_text": "Alice knows Bob."}],
        },
        "claims": [
            {
                "claim_id": "c-001",
                "subject": "Alice", "relation": "knows", "object": "Bob",
                "canonical_text": "Alice knows Bob.", "final_status": "VERIFIED",
            }
        ],
    }
    resp = client.post("/render/verify", json=payload, headers={"X-Request-ID": "test-req-42"})
    assert resp.status_code == 200
    body = resp.json()
    assert "request_id" in body


# --- 23. Multiple claims: partial accept/reject ---

def test_multiple_claims_partial_accept() -> None:
    views = {
        "c-001": _view(claim_id="c-001", canonical_text="Alice knows Bob.", final_status="VERIFIED"),
        "c-002": _view(claim_id="c-002", canonical_text="Bob knows Carol.", final_status="SOURCE_SUPPORTED"),
    }
    draft = AnswerDraft(
        answer_id="a-multi",
        render_mode=CANONICAL_ONLY,
        rendered_text="Alice knows Bob. Bob knows Carol.",
        claim_refs=(
            _ref(claim_id="c-001", rendered_text="Alice knows Bob."),
            _ref(claim_id="c-002", rendered_text="Bob knows Carol."),
        ),
    )
    decision = verify_rendered_answer(draft, views)
    assert decision.valid is False
    assert "c-001" in decision.accepted_claim_ids
    assert "c-002" in decision.rejected_claim_ids


# --- 24. DEFAULT_ALLOWED_CLAIM_STATUSES constant ---

def test_default_allowed_statuses_contains_verified_certified() -> None:
    assert "VERIFIED" in DEFAULT_ALLOWED_CLAIM_STATUSES
    assert "CERTIFIED" in DEFAULT_ALLOWED_CLAIM_STATUSES
    assert "SOURCE_SUPPORTED" not in DEFAULT_ALLOWED_CLAIM_STATUSES
