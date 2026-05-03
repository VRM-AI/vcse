"""Load CSRF runtime indexes from compiled files or source formats."""

from __future__ import annotations

import json
from pathlib import Path

from vcse.cmcf.hash import compute_content_hash
from vcse.cmcf import record_from_dict
from vcse.runtime.compiler import compile_cmcf_to_csrf
from vcse.runtime.model import CSRFIndex
from vcse.runtime.serialize import load_csrf


def load_runtime(source: str) -> CSRFIndex:
    path = Path(source)
    if path.suffix.lower() == ".csrf":
        return load_csrf(path)
    if path.is_file():
        return compile_cmcf_to_csrf(_load_cmcf_records(path))
    if path.is_dir():
        return compile_cmcf_to_csrf(_load_pack_as_cmcf(path))
    raise ValueError(f"RUNTIME_SOURCE_NOT_FOUND: {source}")


def _load_cmcf_records(path: Path):
    rows: list[dict] = []
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        raise ValueError("CMCF_EMPTY_INPUT")
    if path.suffix.lower() == ".jsonl":
        for line in text.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("CMCF_INVALID_JSONL_ROW")
            rows.append(payload)
    else:
        payload = json.loads(text)
        if isinstance(payload, dict):
            rows.append(payload)
        elif isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    raise ValueError("CMCF_INVALID_JSON_ARRAY_ROW")
                rows.append(item)
        else:
            raise ValueError("CMCF_INVALID_JSON_ROOT")
    return [record_from_dict(row) for row in rows]


def _load_pack_as_cmcf(path: Path):
    manifest_path = path / "pack.json"
    claims_path = path / "claims.jsonl"
    if not manifest_path.exists() or not claims_path.exists():
        raise ValueError(f"PACK_INVALID_LAYOUT: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lifecycle_status = str(manifest.get("lifecycle_status", "candidate")).strip() or "candidate"

    rows = []
    for idx, line in enumerate(claims_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        claim = json.loads(line)
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id", f"pack:{path.name}:{idx}"))
        provenance = claim.get("provenance") if isinstance(claim.get("provenance"), dict) else {}
        provenance_id = str(provenance.get("source_id") or provenance.get("id") or f"prov:{claim_id}")
        row = {
            "cmcf_version": "6.0.0",
            "claim": {
                "claim_id": claim_id,
                "subject": str(claim.get("subject", "")),
                "relation": str(claim.get("relation", "")),
                "object": str(claim.get("object", "")),
                "value_type": "entity",
            },
            "provenance": {
                "provenance_id": provenance_id,
                "source_type": str(provenance.get("source_type", "pack")),
                "source_uri": provenance.get("source_uri"),
                "retrieved_at": provenance.get("retrieved_at"),
                "content_hash": provenance.get("content_hash"),
                "locator": provenance.get("locator"),
                "raw_value": provenance.get("raw_value"),
                "method": str(provenance.get("method", "pack_import")),
                "mapping_id": provenance.get("mapping_id"),
            },
            "status": {
                "lifecycle_status": lifecycle_status,
                "verification_status": str(claim.get("verification_status", "UNKNOWN")),
                "certification_status": "NOT_CERTIFIED",
                "provenance_status": "SOURCE_ATTACHED_UNVERIFIED",
                "policy_status": "UNKNOWN",
            },
            "trust": {
                "trust_tier": int(claim.get("trust_tier", 0)),
                "trust_policy": "pack_runtime",
            },
            "integrity": {
                "content_hash": "",
                "pack_hash": None,
                "signature": None,
                "signing_key_id": None,
            },
            "metadata": {
                "domain": manifest.get("domain"),
                "language": None,
                "created_by": "pack_loader",
                "schema_version": "1.0",
            },
        }
        row["integrity"]["content_hash"] = compute_content_hash(
            {
                "cmcf_version": row["cmcf_version"],
                "claim": row["claim"],
                "provenance": row["provenance"],
                "status": row["status"],
                "trust": row["trust"],
                "metadata": row["metadata"],
            }
        )
        rows.append(row)

    return [record_from_dict(row) for row in rows]
