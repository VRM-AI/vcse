from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FieldSpec:
    path: str
    type: str
    cardinality: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SchemaModel:
    record_type: str
    fields: list[FieldSpec]

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "fields": [field.to_dict() for field in self.fields],
        }


@dataclass(frozen=True)
class MappingProposal:
    source_type: str
    record_path: str
    fields: dict[str, str]
    relations: list[dict[str, str]]
    ignored_fields: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_type": self.source_type,
            "record_path": self.record_path,
            "fields": dict(self.fields),
            "relations": [dict(item) for item in self.relations],
            "ignored_fields": list(self.ignored_fields),
        }
