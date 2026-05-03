"""Index helpers for CSRF lookups."""

from __future__ import annotations

from vcse.identity.normalizer import normalize_entity


def lookup_indices(index_map: dict[str, tuple[int, ...]], value: str) -> tuple[int, ...]:
    exact = list(index_map.get(value, ()))
    normalized = normalize_entity(value)
    for key, indices in index_map.items():
        if key == value:
            continue
        if normalize_entity(key) == normalized:
            exact.extend(indices)
    return tuple(sorted(set(exact)))
