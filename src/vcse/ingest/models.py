from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class IngestFileResult:
    source_file: str
    adapter_type: str
    pack_id: str | None
    claim_count: int
    conflict_count: int
    canonical_entity_count: int = 0
    duplicate_entity_count: int = 0
    mapping_path: str | None = None
    inferred_subject: str | None = None
    mapped_relations: list[str] = field(default_factory=list)
    ignored_fields: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IngestResult:
    run_id: str
    files_processed: int
    packs_created: list[str]
    total_claims: int
    total_conflicts: int
    total_entities: int
    total_duplicate_entities: int = 0
    errors: list[str] = field(default_factory=list)
    file_results: list[IngestFileResult] = field(default_factory=list)
    false_verified_count: int = 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["file_results"] = [item.to_dict() for item in self.file_results]
        return payload
