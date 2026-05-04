"""Bundle manifest construction for VCSE signed pack distribution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from vcse.integrity.canonical import canonical_json
from vcse.distribution.model import PackBundleManifest

MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "signature.json"
FORMAT_VERSION = "1.0"


def _sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_hex_file(path: Path) -> str:
    return _sha256_hex_bytes(path.read_bytes())


def _canonical_manifest_payload(pack_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "created_by": "vcse",
        "file_count": len(files),
        "files": files,
        "format_version": FORMAT_VERSION,
        "pack_id": pack_id,
    }


def _manifest_to_dict(manifest: PackBundleManifest) -> dict[str, Any]:
    return {
        "bundle_id": manifest.bundle_id,
        "content_hash": manifest.content_hash,
        "created_by": "vcse",
        "file_count": len(manifest.files),
        "files": list(manifest.files),
        "format_version": manifest.format_version,
        "pack_id": manifest.pack_id,
        "signature_key_id": manifest.signature_key_id,
        "signature_status": manifest.signature_status,
    }


def build_bundle_manifest(bundle_path: Path) -> PackBundleManifest:
    root = Path(bundle_path)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest file: {manifest_path}")

    raw = json.loads(manifest_path.read_text())
    pack_id = str(raw.get("pack_id", "")).strip()
    if not pack_id:
        raise ValueError("manifest missing pack_id")

    files: list[dict[str, Any]] = []
    for item in sorted(raw.get("files", []), key=lambda i: str(i.get("path", ""))):
        rel_path = str(item.get("path", ""))
        if not rel_path:
            continue
        if rel_path == SIGNATURE_NAME:
            continue
        file_path = root / rel_path
        if not file_path.exists() or not file_path.is_file():
            continue
        files.append({"path": rel_path, "sha256": _sha256_hex_file(file_path)})

    canonical_payload = _canonical_manifest_payload(pack_id=pack_id, files=files)
    content_hash = _sha256_hex_bytes(canonical_json(canonical_payload).encode("utf-8"))
    bundle_id = _sha256_hex_bytes(f"{pack_id}:{content_hash}".encode("utf-8"))

    return PackBundleManifest(
        bundle_id=bundle_id,
        format_version=FORMAT_VERSION,
        pack_id=pack_id,
        files=tuple(files),
        content_hash=content_hash,
        signature_status=str(raw.get("signature_status")) if raw.get("signature_status") is not None else None,
        signature_key_id=str(raw.get("signature_key_id")) if raw.get("signature_key_id") is not None else None,
    )


def write_manifest(bundle_path: Path, manifest: PackBundleManifest) -> Path:
    manifest_path = Path(bundle_path) / MANIFEST_NAME
    payload = _manifest_to_dict(manifest)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return manifest_path


def manifest_payload_for_signature(manifest: PackBundleManifest) -> dict[str, Any]:
    return {
        "bundle_id": manifest.bundle_id,
        "content_hash": manifest.content_hash,
        "file_count": len(manifest.files),
        "files": list(manifest.files),
        "format_version": manifest.format_version,
        "pack_id": manifest.pack_id,
    }
