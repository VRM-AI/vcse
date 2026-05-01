from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

class IncrementalSupportError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class IngestFingerprint:
    source_path: str
    source_fingerprint: str
    mapping_fingerprint: str | None
    dataset_hash: str


@dataclass(frozen=True)
class IngestDelta:
    added_count: int
    removed_count: int
    unchanged_count: int
    previous_row_count: int
    current_row_count: int
    source_changed: bool
    mapping_changed: bool
    status: str


@dataclass(frozen=True)
class IncrementalIngestResult:
    status: str
    run_id: str
    delta: IngestDelta
    pack_created: str | None
    skipped: bool
    reason: str


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_row_hash(row: dict) -> str:
    normalized = {
        "subject": str(row.get("subject", row.get("entity", ""))).strip(),
        "relation": str(row.get("relation", "")).strip(),
        "object": str(row.get("object", row.get("value", ""))).strip(),
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_hex_bytes(payload)


def compute_fingerprint(source_file: Path, mapping_path: str | None = None) -> IngestFingerprint:
    canonical = str(source_file.resolve())
    source_bytes = source_file.read_bytes()
    source_fingerprint = sha256_hex_bytes(source_bytes)
    mapping_fingerprint: str | None = None
    if mapping_path:
        mapping_fingerprint = sha256_hex_bytes(Path(mapping_path).read_bytes())
    dataset_hash = sha256_hex_bytes(f"{canonical}|{source_fingerprint}".encode("utf-8"))
    return IngestFingerprint(
        source_path=canonical,
        source_fingerprint=source_fingerprint,
        mapping_fingerprint=mapping_fingerprint,
        dataset_hash=dataset_hash,
    )


def ingest_state_path(dataset_hash: str) -> Path:
    return Path(".vcse") / "ingest_state" / f"{dataset_hash}.json"


def load_ingest_state(dataset_hash: str) -> dict | None:
    path = ingest_state_path(dataset_hash)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_previous_state_for_source(source_path: str) -> dict | None:
    state_dir = Path(".vcse") / "ingest_state"
    if not state_dir.exists():
        return None
    candidates = sorted(state_dir.glob("*.json"), key=lambda item: item.name)
    for candidate in candidates:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        if data.get("source_path") == source_path:
            return data
    return None


def write_ingest_state(
    fingerprint: IngestFingerprint,
    explicit_row_hashes: list[str],
    last_pack_id: str | None,
    last_run_id: str,
) -> dict:
    path = ingest_state_path(fingerprint.dataset_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_hash": fingerprint.dataset_hash,
        "source_path": fingerprint.source_path,
        "source_fingerprint": fingerprint.source_fingerprint,
        "mapping_fingerprint": fingerprint.mapping_fingerprint,
        "explicit_row_hashes": sorted(explicit_row_hashes),
        "last_pack_id": last_pack_id,
        "last_run_id": last_run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def compute_delta(
    previous_state: dict | None,
    fingerprint: IngestFingerprint,
    current_row_hashes: list[str],
) -> IngestDelta:
    if previous_state is None:
        current_count = len(current_row_hashes)
        return IngestDelta(
            added_count=current_count,
            removed_count=0,
            unchanged_count=0,
            previous_row_count=0,
            current_row_count=current_count,
            source_changed=True,
            mapping_changed=bool(fingerprint.mapping_fingerprint),
            status="DELTA_NEW",
        )

    previous_rows = set(previous_state.get("explicit_row_hashes", []))
    current_rows = set(current_row_hashes)
    added = len(current_rows - previous_rows)
    removed = len(previous_rows - current_rows)
    unchanged = len(current_rows & previous_rows)
    source_changed = previous_state.get("source_fingerprint") != fingerprint.source_fingerprint
    mapping_changed = previous_state.get("mapping_fingerprint") != fingerprint.mapping_fingerprint
    if added == 0 and removed == 0 and not source_changed and not mapping_changed:
        status = "DELTA_NO_CHANGES"
    else:
        status = "DELTA_CHANGED"
    return IngestDelta(
        added_count=added,
        removed_count=removed,
        unchanged_count=unchanged,
        previous_row_count=len(previous_rows),
        current_row_count=len(current_rows),
        source_changed=source_changed,
        mapping_changed=mapping_changed,
        status=status,
    )


def ensure_incremental_supported(path: Path, adapter_type: str) -> None:
    if adapter_type != "jsonl":
        raise IncrementalSupportError(f"incremental mode currently supports explicit JSONL only: {path}")


def incremental_payload(
    result: IncrementalIngestResult,
    previous_pack_id: str | None = None,
) -> dict:
    payload = {
        "status": result.status,
        "incremental": True,
        "delta": asdict(result.delta),
        "pack_created": result.pack_created,
        "previous_pack_id": previous_pack_id,
        "skipped": result.skipped,
        "reason": result.reason,
    }
    return payload
