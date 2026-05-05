"""Validation helpers for source support input models."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from vcse.support.profiles import KNOWN_PROFILES


@dataclass(frozen=True)
class SupportValidationIssue:
    code: str
    message: str
    path: str


def validate_source_span(span_dict: dict[str, Any]) -> list[SupportValidationIssue]:
    issues: list[SupportValidationIssue] = []
    if not str(span_dict.get("source_id", "")).strip():
        issues.append(SupportValidationIssue("MISSING_SOURCE_ID", "source_id is required", "source_id"))
    if not str(span_dict.get("source_span_id", "")).strip():
        issues.append(SupportValidationIssue("MISSING_SOURCE_SPAN_ID", "source_span_id is required", "source_span_id"))
    _check_nan_inf_dict(span_dict, "", issues)
    return issues


def validate_candidate_claim_view(claim_dict: dict[str, Any]) -> list[SupportValidationIssue]:
    issues: list[SupportValidationIssue] = []
    if not str(claim_dict.get("relation", "")).strip():
        issues.append(SupportValidationIssue("MISSING_CLAIM_RELATION", "relation is required", "relation"))
    return issues


def validate_active_relation_view(rel_dict: dict[str, Any]) -> list[SupportValidationIssue]:
    issues: list[SupportValidationIssue] = []
    profile_id = str(rel_dict.get("support_profile_id", "")).strip()
    if not profile_id:
        issues.append(SupportValidationIssue("MISSING_SUPPORT_PROFILE", "support_profile_id is required", "support_profile_id"))
    elif profile_id not in KNOWN_PROFILES:
        issues.append(SupportValidationIssue("INVALID_SUPPORT_PROFILE", f"unknown profile: {profile_id}", "support_profile_id"))
    return issues


def _check_nan_inf_dict(
    d: Mapping[str, Any],
    prefix: str,
    issues: list[SupportValidationIssue],
) -> None:
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            issues.append(SupportValidationIssue("NON_FINITE_VALUE", f"NaN/Inf at {path}", path))
        elif isinstance(v, dict):
            _check_nan_inf_dict(v, path, issues)
        elif isinstance(v, (list, tuple)):
            for i, item in enumerate(v):
                if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
                    issues.append(SupportValidationIssue("NON_FINITE_VALUE", f"NaN/Inf at {path}[{i}]", f"{path}[{i}]"))
