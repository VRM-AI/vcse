"""Validation for compiled runtime artifacts (.csrf)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from vcse.runtime.model import CSRFIndex


@dataclass(frozen=True)
class RuntimeValidationIssue:
    code: str
    severity: str
    message: str
    path: str


@dataclass(frozen=True)
class RuntimeValidationResult:
    status: str
    issue_count: int
    issues: tuple[RuntimeValidationIssue, ...]


_VALID_STATUSES = frozenset({
    "RUNTIME_VALID",
    "RUNTIME_INVALID",
    "RUNTIME_ERROR",
})

_VALID_SEVERITIES = frozenset({"ERROR", "WARNING", "INFO"})


def validate_csrf_index(index: CSRFIndex) -> RuntimeValidationResult:
    issues: list[RuntimeValidationIssue] = []
    n = len(index.records)

    # Per-record checks
    for i, rec in enumerate(index.records):
        path = f"records[{i}]"

        if rec.trust_tier < 0:
            issues.append(RuntimeValidationIssue(
                code="RUNTIME_INVALID_TRUST_TIER",
                severity="ERROR",
                message=f"trust_tier must be >= 0, got {rec.trust_tier}",
                path=path,
            ))

        if rec.verification_status != rec.verification_status.upper():
            issues.append(RuntimeValidationIssue(
                code="RUNTIME_STATUS_CASING_INVALID",
                severity="ERROR",
                message=f"verification_status must be UPPER_SNAKE_CASE: {rec.verification_status!r}",
                path=path,
            ))

        # NaN/Inf check on any float fields
        for field_name in ("trust_tier",):
            val = getattr(rec, field_name)
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                issues.append(RuntimeValidationIssue(
                    code="RUNTIME_NON_FINITE_VALUE",
                    severity="ERROR",
                    message=f"non-finite value in {field_name}",
                    path=f"{path}.{field_name}",
                ))

    # Index consistency checks
    for index_name, index_map in (
        ("by_subject", index.by_subject),
        ("by_relation", index.by_relation),
        ("by_object", index.by_object),
    ):
        for key, positions in index_map.items():
            seen: set[int] = set()
            for pos in positions:
                if pos < 0 or pos >= n:
                    issues.append(RuntimeValidationIssue(
                        code="RUNTIME_INDEX_OUT_OF_RANGE",
                        severity="ERROR",
                        message=f"{index_name}[{key!r}] position {pos} out of range (records={n})",
                        path=f"{index_name}[{key}][{pos}]",
                    ))
                if pos in seen:
                    issues.append(RuntimeValidationIssue(
                        code="RUNTIME_DUPLICATE_INDEX_POSITION",
                        severity="ERROR",
                        message=f"{index_name}[{key!r}] duplicate position {pos}",
                        path=f"{index_name}[{key}]",
                    ))
                seen.add(pos)

    # Every record must appear in all three indexes
    for i, rec in enumerate(index.records):
        if rec.subject not in index.by_subject or i not in index.by_subject[rec.subject]:
            issues.append(RuntimeValidationIssue(
                code="RUNTIME_MISSING_SUBJECT_INDEX",
                severity="ERROR",
                message=f"record[{i}] subject {rec.subject!r} missing from by_subject",
                path=f"records[{i}]",
            ))
        if rec.relation not in index.by_relation or i not in index.by_relation[rec.relation]:
            issues.append(RuntimeValidationIssue(
                code="RUNTIME_MISSING_RELATION_INDEX",
                severity="ERROR",
                message=f"record[{i}] relation {rec.relation!r} missing from by_relation",
                path=f"records[{i}]",
            ))
        if rec.object not in index.by_object or i not in index.by_object[rec.object]:
            issues.append(RuntimeValidationIssue(
                code="RUNTIME_MISSING_OBJECT_INDEX",
                severity="ERROR",
                message=f"record[{i}] object {rec.object!r} missing from by_object",
                path=f"records[{i}]",
            ))

    if issues:
        return RuntimeValidationResult(
            status="RUNTIME_INVALID",
            issue_count=len(issues),
            issues=tuple(issues),
        )
    return RuntimeValidationResult(
        status="RUNTIME_VALID",
        issue_count=0,
        issues=(),
    )
