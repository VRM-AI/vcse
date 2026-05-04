"""Inspection helpers for VCSE distribution bundles."""

from __future__ import annotations

from pathlib import Path

from vcse.distribution.manifest import build_bundle_manifest
from vcse.distribution.verify import verify_pack_bundle


def inspect_pack_bundle(bundle_path: Path) -> dict:
    manifest = build_bundle_manifest(Path(bundle_path))
    verification = verify_pack_bundle(Path(bundle_path), public_key_path=None)
    return {
        "bundle_id": manifest.bundle_id,
        "pack_id": manifest.pack_id,
        "file_count": len(manifest.files),
        "signature_status": verification.signature_status,
        "integrity_status": verification.integrity_status,
        "content_hash": manifest.content_hash,
        "files": list(manifest.files),
    }
