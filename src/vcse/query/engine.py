"""Structured deterministic query engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vcse.identity.normalizer import normalize_entity
from vcse.policy import PolicyEnforcer, PolicyLoadError
from vcse.policy import load_policy as load_policy_set
from vcse.query.structured import StructuredQuery, StructuredQueryResult


_TRUSTED_LIFECYCLE = frozenset({"certified", "trusted"})


class StructuredQueryEngine:
    def query_pack(self, pack_path: Path, query: StructuredQuery) -> StructuredQueryResult:
        return self._query_pack_paths((Path(pack_path),), query)

    def query_packs(self, pack_dir: Path, query: StructuredQuery) -> StructuredQueryResult:
        root = Path(pack_dir)
        if not root.exists() or not root.is_dir():
            return StructuredQueryResult(
                status="QUERY_ERROR",
                query=query,
                results=tuple(),
                result_count=0,
                packs_searched=tuple(),
                packs_skipped=tuple(),
                rows_examined=0,
                filters_applied=(f"error:packs_dir_not_found:{root}",),
            )
        pack_paths = tuple(
            sorted(
                [
                    path
                    for path in root.iterdir()
                    if path.is_dir() and (path / "pack.json").exists() and (path / "claims.jsonl").exists()
                ],
                key=lambda item: str(item),
            )
        )
        return self._query_pack_paths(pack_paths, query)

    def _query_pack_paths(self, pack_paths: tuple[Path, ...], query: StructuredQuery) -> StructuredQueryResult:
        filters: list[str] = []
        if query.trusted_only:
            filters.append("trusted_only")
        if not query.include_provenance:
            filters.append("provenance:excluded")
        if query.include_inferred:
            filters.append("include_inferred")
        if query.limit is not None:
            filters.append(f"limit:{query.limit}")

        policy = None
        policy_enforcer: PolicyEnforcer | None = None
        if query.policy_file:
            try:
                policy = load_policy_set(Path(query.policy_file))
                policy_enforcer = PolicyEnforcer()
                filters.append(f"policy:{policy.policy_id}")
            except PolicyLoadError as exc:
                return StructuredQueryResult(
                    status="QUERY_ERROR",
                    query=query,
                    results=tuple(),
                    result_count=0,
                    packs_searched=tuple(),
                    packs_skipped=tuple(),
                    rows_examined=0,
                    filters_applied=tuple(filters + [f"error:policy_load_failed:{exc}"]),
                )

        rows_examined = 0
        blocked_claim_count = 0
        results: list[dict[str, Any]] = []
        packs_searched: list[str] = []
        packs_skipped: list[str] = []

        for pack_path in pack_paths:
            meta = json.loads((pack_path / "pack.json").read_text())
            pack_id = str(meta.get("id") or meta.get("pack_id") or pack_path.name)
            lifecycle_status = str(meta.get("lifecycle_status", "candidate")).strip() or "candidate"

            if query.pack_id and pack_id != query.pack_id:
                packs_skipped.append(pack_id)
                continue
            if query.trusted_only and lifecycle_status not in _TRUSTED_LIFECYCLE:
                packs_skipped.append(pack_id)
                continue

            packs_searched.append(pack_id)
            claims_path = pack_path / "claims.jsonl"
            if not claims_path.exists():
                continue
            for line_index, line in enumerate(claims_path.read_text().splitlines(), start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                row = json.loads(stripped)
                if not isinstance(row, dict):
                    continue
                rows_examined += 1

                if not query.include_inferred and _claim_is_inferred(row):
                    continue
                if policy_enforcer is not None and policy is not None:
                    decision = policy_enforcer.evaluate_claim(row, policy)
                    if decision.status == "BLOCKED":
                        blocked_claim_count += 1
                        continue
                if not _matches(row, query):
                    continue

                result = {
                    "subject": str(row.get("subject", "")),
                    "relation": str(row.get("relation", "")),
                    "object": str(row.get("object", "")),
                    "pack_id": pack_id,
                    "claim_id": str(row.get("claim_id") or f"{pack_id}:{line_index}"),
                    "trust_tier": row.get("trust_tier"),
                    "lifecycle_status": lifecycle_status,
                    "provenance": row.get("provenance") if query.include_provenance else None,
                }
                results.append(result)

        results_sorted = sorted(
            results,
            key=lambda item: (
                str(item.get("subject", "")),
                str(item.get("relation", "")),
                str(item.get("object", "")),
                str(item.get("pack_id", "")),
                str(item.get("claim_id", "")),
            ),
        )
        if query.limit is not None:
            results_sorted = results_sorted[: max(0, query.limit)]

        if blocked_claim_count > 0:
            filters.append(f"blocked_claims:{blocked_claim_count}")

        status = "QUERY_COMPLETE" if results_sorted else "QUERY_NO_RESULTS"
        return StructuredQueryResult(
            status=status,
            query=query,
            results=tuple(results_sorted),
            result_count=len(results_sorted),
            packs_searched=tuple(sorted(set(packs_searched))),
            packs_skipped=tuple(sorted(set(packs_skipped))),
            rows_examined=rows_examined,
            filters_applied=tuple(filters),
        )


def _matches(row: dict[str, Any], query: StructuredQuery) -> bool:
    return (
        _exact_or_normalized_match(query.subject, row.get("subject"))
        and _exact_or_normalized_match(query.relation, row.get("relation"))
        and _exact_or_normalized_match(query.object, row.get("object"))
    )


def _exact_or_normalized_match(expected: str | None, actual: Any) -> bool:
    if expected is None:
        return True
    expected_text = str(expected)
    actual_text = str(actual if actual is not None else "")
    if expected_text == actual_text:
        return True
    return normalize_entity(expected_text) == normalize_entity(actual_text)


def _claim_is_inferred(claim: dict[str, Any]) -> bool:
    qualifiers = claim.get("qualifiers")
    if isinstance(qualifiers, dict) and str(qualifiers.get("inference_type", "")).strip():
        return True
    derived_from = claim.get("derived_from")
    if isinstance(derived_from, list) and bool(derived_from):
        return True
    return bool(claim.get("inferred", False))
