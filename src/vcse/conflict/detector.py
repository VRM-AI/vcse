"""Deterministic conflict detection for claims."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from vcse.conflict.model import Conflict
from vcse.domain.loader import get_relation_properties


class ConflictDetector:
    def detect(self, claims: list[dict[str, Any]]) -> list[Conflict]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for claim in claims:
            subject = str(claim.get("normalized_subject", claim.get("subject", ""))).strip()
            relation = str(claim.get("relation", "")).strip()
            if not subject or not relation:
                continue
            grouped[(subject, relation)].append(claim)

        conflicts: list[Conflict] = []
        for (subject, relation), bucket in sorted(grouped.items()):
            relation_props = get_relation_properties(relation)
            if not relation_props.get("functional", True):
                continue
            by_object: dict[str, dict[str, Any]] = {}
            for claim in bucket:
                normalized_object = str(claim.get("normalized_object", claim.get("object", ""))).strip()
                if not normalized_object:
                    continue
                if normalized_object not in by_object:
                    by_object[normalized_object] = claim
            objects = sorted(by_object.keys())
            if len(objects) < 2:
                continue
            for idx in range(len(objects)):
                for jdx in range(idx + 1, len(objects)):
                    first = by_object[objects[idx]]
                    second = by_object[objects[jdx]]
                    conflicts.append(
                        Conflict(
                            subject=subject,
                            relation=relation,
                            object_a=str(first.get("object", objects[idx])),
                            object_b=str(second.get("object", objects[jdx])),
                            source_a=str(first.get("provenance", {}).get("source_id", "")),
                            source_b=str(second.get("provenance", {}).get("source_id", "")),
                            reason="multiple_distinct_objects_for_subject_relation",
                        )
                    )
        return conflicts

    def detect_global_conflicts(self, claims: list[dict[str, Any]]) -> list[Conflict]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for claim in claims:
            subject = str(claim.get("subject", "")).strip()
            relation = str(claim.get("relation", "")).strip()
            if not subject or not relation:
                continue
            grouped[(subject, relation)].append(claim)

        conflicts: list[Conflict] = []
        for (subject, relation), bucket in sorted(grouped.items()):
            relation_props = get_relation_properties(relation)
            if not relation_props.get("functional", True):
                continue

            by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for claim in sorted(
                bucket,
                key=lambda item: (
                    str(item.get("object", "")),
                    str(item.get("pack_id", "")),
                    str(item.get("claim_id", "")),
                ),
            ):
                obj = str(claim.get("object", "")).strip()
                if not obj:
                    continue
                by_object[obj].append(claim)

            objects = sorted(by_object.keys())
            if len(objects) < 2:
                continue

            for idx in range(len(objects)):
                for jdx in range(idx + 1, len(objects)):
                    left_bucket = by_object[objects[idx]]
                    right_bucket = by_object[objects[jdx]]
                    left = left_bucket[0]
                    right = right_bucket[0]
                    pack_ids = tuple(
                        sorted(
                            {
                                str(item.get("pack_id", "")).strip()
                                for item in [*left_bucket, *right_bucket]
                                if str(item.get("pack_id", "")).strip()
                            }
                        )
                    )
                    provenance_refs = tuple(
                        sorted(
                            {
                                str(item.get("provenance", {}).get("source_id", "")).strip()
                                for item in [*left_bucket, *right_bucket]
                                if str(item.get("provenance", {}).get("source_id", "")).strip()
                            }
                        )
                    )
                    conflicts.append(
                        Conflict(
                            subject=subject,
                            relation=relation,
                            object_a=str(left.get("object", objects[idx])),
                            object_b=str(right.get("object", objects[jdx])),
                            source_a=str(left.get("provenance", {}).get("source_id", "")),
                            source_b=str(right.get("provenance", {}).get("source_id", "")),
                            reason="global_multiple_distinct_objects_for_subject_relation",
                            pack_ids=pack_ids,
                            provenance_refs=provenance_refs,
                        )
                    )
        return conflicts
