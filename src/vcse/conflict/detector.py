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
