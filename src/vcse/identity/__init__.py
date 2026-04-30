"""Entity identity utilities."""

from vcse.identity.alias_registry import AliasRegistry
from vcse.identity.model import CanonicalEntity
from vcse.identity.normalizer import normalize_entity

__all__ = ["AliasRegistry", "CanonicalEntity", "normalize_entity"]
