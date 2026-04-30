from vcse.identity.alias_registry import AliasRegistry
from vcse.identity.model import CanonicalEntity
from vcse.identity.normalizer import normalize_entity


def test_normalization_deterministic() -> None:
    assert normalize_entity("United States") == "united_states"
    assert normalize_entity(" New   York City ") == "new_york_city"


def test_identical_strings_normalize_same() -> None:
    assert normalize_entity("USA") == normalize_entity("usa")


def test_different_strings_do_not_collapse_incorrectly() -> None:
    assert normalize_entity("USA") != normalize_entity("United States")


def test_alias_registry_stores_and_resolves() -> None:
    registry = AliasRegistry()
    entity = CanonicalEntity(
        canonical_id="entity:united_states",
        original_text="United States",
        normalized="united_states",
        source_id="source_a",
    )
    registry.add(entity)
    assert registry.get_canonical("United States") == "entity:united_states"
    assert registry.get_aliases("entity:united_states") == ["United States"]
