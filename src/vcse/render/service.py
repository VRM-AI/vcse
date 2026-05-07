"""Deterministic renderer guard service."""

from __future__ import annotations

from typing import Mapping

from vcse.render.model import (
    AnswerClaimRef,
    AnswerDraft,
    RendererGuardDecision,
    RendererGuardPolicy,
    ValidatedClaimView,
    CANONICAL_ONLY,
    NORMALIZED_CANONICAL,
    EXPLICIT_ALLOWED_RENDERING,
    DEFAULT_ALLOWED_CLAIM_STATUSES,
    RENDER_VALID,
    RENDER_INVALID,
    RENDER_NEEDS_CLAIM_MAP,
    RENDER_EXCEEDS_VALIDATED_MATERIAL,
    RENDER_GUARD_PASSED,
    MISSING_ANSWER_ID,
    MISSING_RENDERED_TEXT,
    MISSING_CLAIM_REFS,
    UNKNOWN_CLAIM_ID,
    CLAIM_STATUS_NOT_ALLOWED,
    RENDERED_TEXT_NOT_CANONICAL,
    UNSUPPORTED_SEGMENT_PRESENT,
    SOURCE_SPAN_MISMATCH,
    INVALID_RENDER_MODE,
    INVALID_RENDER_INPUT,
    NON_FINITE_VALUE,
    ALLOWED_RENDER_MODES,
)
from vcse.render.validate import _check_nan_inf, normalize_rendered_text


def verify_rendered_answer(
    answer: AnswerDraft,
    claim_views: Mapping[str, ValidatedClaimView],
    policy: RendererGuardPolicy | None = None,
) -> RendererGuardDecision:
    """
    Deterministically verify a structured answer draft against supplied validated claim views.

    Invariants:
    - Never emits VERIFIED, CERTIFIED, or SOURCE_SUPPORTED.
    - Never modifies inputs.
    - Never calls verifier/trust/proof/certification/source-support.
    - No generative model calls, embeddings, fuzzy matching, or probabilistic thresholds.
    - Fails closed on any invalid/missing input.
    """
    effective_policy = policy or RendererGuardPolicy()
    allowed_statuses = effective_policy.allowed_claim_statuses

    issues: list[str] = []

    # --- Input validation ---
    nan_issues: list[str] = []
    _check_nan_inf(dict(answer.metadata), "answer.metadata", nan_issues)
    if nan_issues:
        return _fail(answer.answer_id, answer.render_mode, NON_FINITE_VALUE, nan_issues)

    if not str(answer.answer_id).strip():
        return _fail("", answer.render_mode, MISSING_ANSWER_ID, ["answer_id is required"])

    if not str(answer.rendered_text).strip():
        return _fail(answer.answer_id, answer.render_mode, MISSING_RENDERED_TEXT, ["rendered_text is required"])

    if answer.render_mode not in ALLOWED_RENDER_MODES:
        return _fail(answer.answer_id, answer.render_mode, INVALID_RENDER_MODE,
                     [f"unknown render_mode: {answer.render_mode!r}"])

    if not answer.claim_refs:
        return RendererGuardDecision(
            answer_id=answer.answer_id,
            final_status=RENDER_NEEDS_CLAIM_MAP,
            valid=False,
            reason_code=MISSING_CLAIM_REFS,
            issues=("claim_refs is required and must be non-empty",),
            claim_count=0,
            accepted_claim_ids=(),
            rejected_claim_ids=(),
            render_mode=answer.render_mode,
        )

    # --- Unsupported segments (fail immediately) ---
    if answer.unsupported_segments:
        seg_issues = tuple(f"unsupported_segment: {s}" for s in answer.unsupported_segments)
        return RendererGuardDecision(
            answer_id=answer.answer_id,
            final_status=RENDER_EXCEEDS_VALIDATED_MATERIAL,
            valid=False,
            reason_code=UNSUPPORTED_SEGMENT_PRESENT,
            issues=seg_issues,
            claim_count=len(answer.claim_refs),
            accepted_claim_ids=(),
            rejected_claim_ids=tuple(ref.claim_id for ref in answer.claim_refs),
            render_mode=answer.render_mode,
        )

    accepted: list[str] = []
    rejected: list[str] = []
    first_fail_reason: str = RENDER_GUARD_PASSED

    for ref in answer.claim_refs:
        ref_issues: list[str] = []

        # Unknown claim id
        if ref.claim_id not in claim_views:
            ref_issues.append(f"unknown claim_id: {ref.claim_id!r}")
            issues.extend(ref_issues)
            rejected.append(ref.claim_id)
            if first_fail_reason == RENDER_GUARD_PASSED:
                first_fail_reason = UNKNOWN_CLAIM_ID
            continue

        view = claim_views[ref.claim_id]

        # Claim status not allowed
        if view.final_status not in allowed_statuses:
            ref_issues.append(
                f"claim {ref.claim_id!r} has status {view.final_status!r} which is not in allowed statuses"
            )
            issues.extend(ref_issues)
            rejected.append(ref.claim_id)
            if first_fail_reason == RENDER_GUARD_PASSED:
                first_fail_reason = CLAIM_STATUS_NOT_ALLOWED
            continue

        # Rendered text canonical check
        text_ok = _check_rendered_text(ref.rendered_text, view, answer.render_mode)
        if not text_ok:
            ref_issues.append(
                f"rendered_text for claim {ref.claim_id!r} is not canonical/allowed under mode {answer.render_mode!r}"
            )
            issues.extend(ref_issues)
            rejected.append(ref.claim_id)
            if first_fail_reason == RENDER_GUARD_PASSED:
                first_fail_reason = RENDERED_TEXT_NOT_CANONICAL
            continue

        # Source span mismatch (if ref supplies spans, they must be a subset of view spans)
        if ref.source_span_ids and view.source_span_ids:
            unknown_spans = [s for s in ref.source_span_ids if s not in view.source_span_ids]
            if unknown_spans:
                ref_issues.append(
                    f"source_span_ids {unknown_spans!r} not in validated spans for claim {ref.claim_id!r}"
                )
                issues.extend(ref_issues)
                rejected.append(ref.claim_id)
                if first_fail_reason == RENDER_GUARD_PASSED:
                    first_fail_reason = SOURCE_SPAN_MISMATCH
                continue

        accepted.append(ref.claim_id)

    if rejected:
        # Determine appropriate final_status
        if first_fail_reason == UNSUPPORTED_SEGMENT_PRESENT:
            final_status = RENDER_EXCEEDS_VALIDATED_MATERIAL
        elif first_fail_reason in (UNKNOWN_CLAIM_ID, CLAIM_STATUS_NOT_ALLOWED,
                                   RENDERED_TEXT_NOT_CANONICAL, SOURCE_SPAN_MISMATCH):
            final_status = RENDER_EXCEEDS_VALIDATED_MATERIAL if first_fail_reason in (
                RENDERED_TEXT_NOT_CANONICAL, CLAIM_STATUS_NOT_ALLOWED
            ) else RENDER_INVALID
        else:
            final_status = RENDER_INVALID

        return RendererGuardDecision(
            answer_id=answer.answer_id,
            final_status=final_status,
            valid=False,
            reason_code=first_fail_reason,
            issues=tuple(issues),
            claim_count=len(answer.claim_refs),
            accepted_claim_ids=tuple(accepted),
            rejected_claim_ids=tuple(rejected),
            render_mode=answer.render_mode,
        )

    return RendererGuardDecision(
        answer_id=answer.answer_id,
        final_status=RENDER_VALID,
        valid=True,
        reason_code=RENDER_GUARD_PASSED,
        issues=(),
        claim_count=len(answer.claim_refs),
        accepted_claim_ids=tuple(accepted),
        rejected_claim_ids=(),
        render_mode=answer.render_mode,
    )


def _check_rendered_text(rendered: str, view: ValidatedClaimView, render_mode: str) -> bool:
    if render_mode == CANONICAL_ONLY:
        return rendered == view.canonical_text
    if render_mode == NORMALIZED_CANONICAL:
        return normalize_rendered_text(rendered) == normalize_rendered_text(view.canonical_text)
    if render_mode == EXPLICIT_ALLOWED_RENDERING:
        if rendered == view.canonical_text:
            return True
        return rendered in view.allowed_renderings
    return False


def _fail(
    answer_id: str,
    render_mode: str,
    reason_code: str,
    issues: list[str],
) -> RendererGuardDecision:
    return RendererGuardDecision(
        answer_id=answer_id,
        final_status=RENDER_INVALID,
        valid=False,
        reason_code=reason_code,
        issues=tuple(issues),
        claim_count=0,
        accepted_claim_ids=(),
        rejected_claim_ids=(),
        render_mode=render_mode,
    )
