"""Deterministic alias registry."""

from __future__ import annotations

from vcse.identity.model import CanonicalEntity
from vcse.identity.normalizer import normalize_entity


class AliasRegistry:
    def __init__(self) -> None:
        self._normalized_to_canonical: dict[str, str] = {}
        self._canonical_to_aliases: dict[str, set[str]] = {}

    def add(self, entity: CanonicalEntity) -> None:
        self._normalized_to_canonical[entity.normalized] = entity.canonical_id
        aliases = self._canonical_to_aliases.setdefault(entity.canonical_id, set())
        aliases.add(entity.original_text)

    def get_canonical(self, text: str) -> str | None:
        normalized = normalize_entity(text)
        if not normalized:
            return None
        return self._normalized_to_canonical.get(normalized)

    def get_aliases(self, canonical_id: str) -> list[str]:
        return sorted(self._canonical_to_aliases.get(canonical_id, set()))

    @staticmethod
    def canonical_id_for(text: str) -> str:
        return f"entity:{normalize_entity(text)}"

    @property
    def normalized_mappings(self) -> dict[str, str]:
        return dict(self._normalized_to_canonical)

    def canonical_count(self) -> int:
        return len(self._canonical_to_aliases)
