from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vcse.adapters import get_adapter
from vcse.conflict.detector import ConflictDetector
from vcse.identity.normalizer import normalize_entity
from vcse.ingest.delta import (
    IncrementalIngestResult,
    IngestDelta,
    IncrementalSupportError,
    compute_delta,
    compute_fingerprint,
    ensure_incremental_supported,
    load_previous_state_for_source,
    normalized_row_hash,
    write_ingest_state,
)
from vcse.ingest.detector import detect_source_files
from vcse.ingest.models import IngestFileResult, IngestResult
from vcse.ingest.report import persist_ingest_report
from vcse.schema import MappingProposer, SchemaDetector, convert_rows_with_mapping, write_mapping_artifact


class IngestError(ValueError):
    def __init__(self, error_type: str, reason: str) -> None:
        super().__init__(f"{error_type}: {reason}")
        self.error_type = error_type
        self.reason = reason


@dataclass
class _CompiledClaims:
    claims: list[dict]
    canonical_entity_count: int
    duplicate_entity_count: int


def run_ingest(
    path: Path,
    run_id: str | None = None,
    auto_approve: bool = False,
    incremental: bool = False,
    force: bool = False,
) -> IngestResult:
    target = Path(path)
    if not target.exists():
        raise IngestError("INVALID_PATH", f"path not found: {target}")

    run_token = run_id or _timestamp_token()
    files = detect_source_files(target)

    file_results: list[IngestFileResult] = []
    packs_created: list[str] = []
    errors: list[str] = []
    used_pack_ids: set[str] = set()

    total_claims = 0
    total_conflicts = 0
    total_entities = 0
    total_duplicate_entities = 0

    if incremental and len(files) > 1:
        raise IngestError("INCREMENTAL_MULTI_SOURCE_UNSUPPORTED", "incremental mode currently supports one source file")

    incremental_result: IncrementalIngestResult | None = None
    previous_pack_id: str | None = None
    current_pack_id: str | None = None

    for source_file in files:
        adapter_type = source_file.suffix.lower().lstrip(".")
        try:
            adapter = get_adapter(adapter_type)
            rows = adapter.run(source_file)
            rows, inference_info = _prepare_rows_for_ingest(
                source_file=source_file,
                source_type=adapter_type,
                rows=rows,
                auto_approve=auto_approve,
            )
            explicit_row_hashes = sorted(normalized_row_hash(row) for row in rows)
            compiled = _compile_rows(rows)
            should_generate_pack = True
            delta = IngestDelta(
                added_count=0,
                removed_count=0,
                unchanged_count=0,
                previous_row_count=0,
                current_row_count=0,
                source_changed=False,
                mapping_changed=False,
                status="DELTA_NEW",
            )
            if incremental:
                try:
                    ensure_incremental_supported(source_file, adapter_type)
                except IncrementalSupportError as exc:
                    raise IngestError("INCREMENTAL_UNSUPPORTED_SOURCE", exc.reason) from exc
                fingerprint = compute_fingerprint(source_file, inference_info["mapping_path"])
                previous_state = load_previous_state_for_source(fingerprint.source_path)
                previous_pack_id = previous_state.get("last_pack_id") if previous_state else None
                delta = compute_delta(previous_state, fingerprint, explicit_row_hashes)
                if delta.status == "DELTA_NO_CHANGES" and not force:
                    should_generate_pack = False
                    incremental_result = IncrementalIngestResult(
                        status="INGEST_NO_CHANGES",
                        run_id=run_token,
                        delta=delta,
                        pack_created=None,
                        skipped=True,
                        reason="No explicit row changes detected",
                    )

            if should_generate_pack:
                pack_id = _build_pack_id(source_file, run_token, used_pack_ids)
                pack_path = _pack_path(pack_id)
                if pack_path.exists():
                    raise IngestError("PACK_EXISTS", f"pack already exists: {pack_path}")

                conflicts = ConflictDetector().detect(compiled.claims)
                _write_candidate_pack(pack_path, pack_id, compiled.claims, conflicts)
                _validate_pack(pack_path)
                current_pack_id = pack_id
            else:
                pack_id = None
                conflicts = []

            conflict_count = len(conflicts)
            claim_count = len(compiled.claims)
            if should_generate_pack:
                total_claims += claim_count
                total_conflicts += conflict_count
            total_entities += compiled.canonical_entity_count
            total_duplicate_entities += compiled.duplicate_entity_count
            if pack_id is not None:
                packs_created.append(pack_id)
                used_pack_ids.add(pack_id)
            file_results.append(
                IngestFileResult(
                    source_file=str(source_file),
                    adapter_type=adapter_type,
                    pack_id=pack_id,
                    claim_count=claim_count,
                    conflict_count=conflict_count,
                    canonical_entity_count=compiled.canonical_entity_count,
                    duplicate_entity_count=compiled.duplicate_entity_count,
                    mapping_path=inference_info["mapping_path"],
                    inferred_subject=inference_info["inferred_subject"],
                    mapped_relations=inference_info["mapped_relations"],
                    ignored_fields=inference_info["ignored_fields"],
                )
            )

            if incremental:
                if incremental_result is None:
                    incremental_result = IncrementalIngestResult(
                        status="INGEST_INCREMENTAL_COMPLETE",
                        run_id=run_token,
                        delta=delta,
                        pack_created=pack_id,
                        skipped=False,
                        reason="Delta detected and candidate pack generated" if delta.status != "DELTA_NO_CHANGES" else "Forced regeneration",
                    )
                fingerprint = compute_fingerprint(source_file, inference_info["mapping_path"])
                write_ingest_state(
                    fingerprint=fingerprint,
                    explicit_row_hashes=explicit_row_hashes,
                    last_pack_id=pack_id or previous_pack_id,
                    last_run_id=run_token,
                )
        except Exception as exc:  # noqa: BLE001
            reason = str(exc)
            errors.append(f"{source_file}: {reason}")
            file_results.append(
                IngestFileResult(
                    source_file=str(source_file),
                    adapter_type=adapter_type,
                    pack_id=None,
                    claim_count=0,
                    conflict_count=0,
                    error=reason,
                )
            )

    result = IngestResult(
        run_id=run_token,
        files_processed=len(files),
        packs_created=packs_created,
        total_claims=total_claims,
        total_conflicts=total_conflicts,
        total_entities=total_entities,
        total_duplicate_entities=total_duplicate_entities,
        errors=errors,
        file_results=file_results,
        false_verified_count=0,
        incremental=incremental,
        status=(incremental_result.status if incremental and incremental_result else "INGEST_COMPLETE"),
        delta_status=(incremental_result.delta.status if incremental and incremental_result else None),
        added_count=(incremental_result.delta.added_count if incremental and incremental_result else None),
        removed_count=(incremental_result.delta.removed_count if incremental and incremental_result else None),
        unchanged_count=(incremental_result.delta.unchanged_count if incremental and incremental_result else None),
        previous_row_count=(incremental_result.delta.previous_row_count if incremental and incremental_result else None),
        current_row_count=(incremental_result.delta.current_row_count if incremental and incremental_result else None),
        source_changed=(incremental_result.delta.source_changed if incremental and incremental_result else None),
        mapping_changed=(incremental_result.delta.mapping_changed if incremental and incremental_result else None),
        previous_pack_id=previous_pack_id,
        current_pack_id=current_pack_id,
        skipped_reason=(incremental_result.reason if incremental and incremental_result and incremental_result.skipped else None),
    )
    persist_ingest_report(result)
    return result


def _prepare_rows_for_ingest(
    source_file: Path,
    source_type: str,
    rows: list[dict],
    auto_approve: bool,
) -> tuple[list[dict], dict[str, object]]:
    if _rows_are_explicit(rows):
        return rows, {
            "mapping_path": None,
            "inferred_subject": None,
            "mapped_relations": [],
            "ignored_fields": [],
        }
    detector = SchemaDetector()
    schema = detector.detect_records(rows)
    proposer = MappingProposer()
    proposal = proposer.propose(schema, source_type=source_type)
    mapping = proposal.to_dict()
    mapping_path = write_mapping_artifact(source_file, mapping)
    if not auto_approve:
        raise IngestError(
            "MAPPING_APPROVAL_REQUIRED",
            f"inferred mapping saved to {mapping_path}; rerun with --auto-approve",
        )
    explicit_rows = convert_rows_with_mapping(rows, mapping)
    mapped_relations = [f"{item['path']} -> {item['relation']}" for item in mapping.get("relations", [])]
    return explicit_rows, {
        "mapping_path": str(mapping_path),
        "inferred_subject": mapping.get("fields", {}).get("subject"),
        "mapped_relations": mapped_relations,
        "ignored_fields": list(mapping.get("ignored_fields", [])),
    }


def _rows_are_explicit(rows: list[dict]) -> bool:
    if not rows:
        return True
    for row in rows:
        if not isinstance(row, dict):
            return False
        if not {"subject", "relation", "object"}.issubset(set(row.keys())) and not {
            "entity",
            "relation",
            "value",
        }.issubset(set(row.keys())):
            return False
    return True


def _compile_rows(rows: list[dict]) -> _CompiledClaims:
    claims: list[dict] = []
    canonical_entities: set[str] = set()
    duplicates = 0

    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise IngestError("INVALID_ROW", f"row {idx} must be an object")

        subject_raw = row.get("subject", row.get("entity"))
        relation_raw = row.get("relation")
        object_raw = row.get("object", row.get("value"))

        if subject_raw is None or relation_raw is None or object_raw is None:
            raise IngestError(
                "UNSUPPORTED_ROW_SCHEMA",
                "rows must include subject/relation/object or entity/relation/value",
            )

        subject = str(subject_raw).strip()
        relation = str(relation_raw).strip()
        object_value = str(object_raw).strip()
        if not subject or not relation or not object_value:
            raise IngestError("INVALID_ROW", f"row {idx} has empty subject/relation/object")

        norm_subject = normalize_entity(subject)
        norm_object = normalize_entity(object_value)
        if not norm_subject or not norm_object:
            raise IngestError("INVALID_ROW", f"row {idx} cannot be normalized")

        subject_canonical_id = f"entity:{norm_subject}"
        object_canonical_id = f"entity:{norm_object}"

        before_size = len(canonical_entities)
        canonical_entities.add(subject_canonical_id)
        canonical_entities.add(object_canonical_id)
        if len(canonical_entities) == before_size:
            duplicates += 2

        claim = {
            "claim_key": f"{norm_subject}|{relation}|{norm_object}",
            "subject": subject,
            "relation": relation,
            "object": object_value,
            "normalized_subject": norm_subject,
            "normalized_object": norm_object,
            "subject_canonical_id": subject_canonical_id,
            "object_canonical_id": object_canonical_id,
            "qualifiers": {"inference_type": "explicit"},
            "provenance": {
                "source_type": "ingest",
                "source_id": "autonomous_ingest",
                "location": f"row_{idx}",
                "evidence_text": f"{subject} {relation} {object_value}",
                "confidence": 1.0,
                "trust_level": "unrated",
            },
        }
        claims.append(claim)

    ordered_claims = sorted(claims, key=lambda item: json.dumps(item, sort_keys=True))
    canonical_entity_count = len(canonical_entities)
    duplicate_entity_count = max(0, (2 * len(claims)) - canonical_entity_count)
    return _CompiledClaims(
        claims=ordered_claims,
        canonical_entity_count=canonical_entity_count,
        duplicate_entity_count=duplicate_entity_count,
    )


def _build_pack_id(source_file: Path, timestamp: str, used_pack_ids: set[str]) -> str:
    base = source_file.stem.strip() or "source"
    candidate = f"{base}_candidate_{timestamp}"
    if candidate not in used_pack_ids:
        return candidate
    suffix = 2
    while True:
        numbered = f"{candidate}_{suffix}"
        if numbered not in used_pack_ids:
            return numbered
        suffix += 1


def _pack_path(pack_id: str) -> Path:
    return Path("examples") / "packs" / pack_id


def _write_candidate_pack(pack_path: Path, pack_id: str, claims: list[dict], conflicts: list[object]) -> None:
    pack_path.mkdir(parents=True, exist_ok=False)

    conflicts_rows = [
        {
            "subject": item.subject,
            "relation": item.relation,
            "object_a": item.object_a,
            "object_b": item.object_b,
            "source_a": item.source_a,
            "source_b": item.source_b,
            "reason": item.reason,
        }
        for item in conflicts
    ]

    canonical_entities = {
        claim["subject_canonical_id"] for claim in claims
    } | {
        claim["object_canonical_id"] for claim in claims
    }
    duplicate_entity_count = max(0, (2 * len(claims)) - len(canonical_entities))

    (pack_path / "pack.json").write_text(
        json.dumps(
            {
                "id": pack_id,
                "version": "1.0.0",
                "domain": "ingest",
                "lifecycle_status": "candidate",
                "claim_count": len(claims),
                "provenance_count": len(claims),
                "conflict_count": len(conflicts_rows),
                "constraint_count": 0,
                "template_count": 0,
                "metrics": {},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _write_jsonl(pack_path / "claims.jsonl", claims)
    _write_jsonl(pack_path / "provenance.jsonl", [claim["provenance"] for claim in claims])
    (pack_path / "conflicts.json").write_text(
        json.dumps({"conflict_count": len(conflicts_rows), "conflicts": conflicts_rows}, indent=2, sort_keys=True) + "\n"
    )
    (pack_path / "metrics.json").write_text(
        json.dumps(
            {
                "claim_count": len(claims),
                "input_record_count": len(claims),
                "duplicate_count": 0,
                "conflict_count": len(conflicts_rows),
                "duplicate_entity_count": duplicate_entity_count,
                "canonical_entity_count": len(canonical_entities),
                "provenance_count": len(claims),
                "benchmark_count": 0,
                "false_verified_count": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (pack_path / "trust_report.json").write_text(
        json.dumps(
            {
                "status": "TRUST_PENDING",
                "false_verified_count": 0,
                "decisions": [],
                "conflicts": conflicts_rows,
                "staleness": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _validate_pack(pack_path: Path) -> None:
    required = ["pack.json", "claims.jsonl", "provenance.jsonl", "metrics.json", "trust_report.json", "conflicts.json"]
    for name in required:
        if not (pack_path / name).exists():
            raise IngestError("INVALID_PACK_STRUCTURE", f"missing {name} in {pack_path}")
    manifest = json.loads((pack_path / "pack.json").read_text())
    if manifest.get("lifecycle_status") != "candidate":
        raise IngestError("INVALID_PACK_LIFECYCLE", "lifecycle_status must be candidate")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in rows))


def _timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
