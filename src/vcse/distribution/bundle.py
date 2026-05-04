"""Pack bundle creation for distribution."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from vcse.integrity.keys import load_private_key
from vcse.integrity.signing import sign_data
from vcse.distribution.manifest import FORMAT_VERSION, build_bundle_manifest, manifest_payload_for_signature, write_manifest
from vcse.distribution.model import PackBundleManifest

TRANSIENT_EXCLUDES = {
    "__pycache__",
    ".DS_Store",
    "manifest.json",
    "signature.json",
}


def _load_pack_id(pack_path: Path) -> str:
    payload = json.loads((pack_path / "pack.json").read_text())
    pack_id = str(payload.get("id", "")).strip()
    if not pack_id:
        raise ValueError(f"pack id missing in {pack_path / 'pack.json'}")
    return pack_id


def _collect_pack_files(pack_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(pack_path.rglob("*")):
        if not path.is_file():
            continue
        if any(part in TRANSIENT_EXCLUDES for part in path.parts):
            continue
        files.append(path)
    return files


def create_pack_bundle(
    pack_path: Path,
    output_dir: Path,
    private_key_path: Path | None = None,
) -> Path:
    pack_root = Path(pack_path)
    if not pack_root.exists():
        raise FileNotFoundError(f"pack not found: {pack_root}")

    for required in ("pack.json", "claims.jsonl", "provenance.jsonl"):
        if not (pack_root / required).exists():
            raise FileNotFoundError(f"missing required pack file: {required}")

    pack_id = _load_pack_id(pack_root)
    bundle_root = Path(output_dir) / f"{pack_id}.vcsepack"
    pack_bundle_root = bundle_root / "pack"
    pack_bundle_root.mkdir(parents=True, exist_ok=True)

    for src in _collect_pack_files(pack_root):
        rel = src.relative_to(pack_root)
        dst = pack_bundle_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Bootstrap manifest scaffold so build_bundle_manifest has deterministic source metadata.
    scaffold = {
        "bundle_id": "",
        "content_hash": "",
        "created_by": "vcse",
        "file_count": 0,
        "files": [],
        "format_version": FORMAT_VERSION,
        "pack_id": pack_id,
        "signature_key_id": None,
        "signature_status": None,
    }
    (bundle_root / "manifest.json").write_text(json.dumps(scaffold, indent=2, sort_keys=True) + "\n")

    files = []
    for file_path in sorted(pack_bundle_root.rglob("*")):
        if file_path.is_file():
            rel = file_path.relative_to(bundle_root).as_posix()
            import hashlib
            files.append({"path": rel, "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest()})

    seed_manifest = PackBundleManifest(
        bundle_id="",
        format_version=FORMAT_VERSION,
        pack_id=pack_id,
        files=tuple(files),
        content_hash="",
    )
    write_manifest(bundle_root, seed_manifest)
    manifest = build_bundle_manifest(bundle_root)

    signature_payload = None
    if private_key_path is not None:
        private_key = load_private_key(private_key_path)
        signature = sign_data(manifest_payload_for_signature(manifest), private_key)
        signature_payload = {
            "signature_id": signature.signature_id,
            "algorithm": signature.algorithm,
            "key_id": signature.key_id,
            "signature": signature.signature,
            "signed_hash": signature.signed_hash,
        }
        (bundle_root / "signature.json").write_text(json.dumps(signature_payload, indent=2, sort_keys=True) + "\n")
        manifest = PackBundleManifest(
            bundle_id=manifest.bundle_id,
            format_version=manifest.format_version,
            pack_id=manifest.pack_id,
            files=manifest.files,
            content_hash=manifest.content_hash,
            signature_status="SIGNATURE_VALID",
            signature_key_id=signature.key_id,
        )
    else:
        manifest = PackBundleManifest(
            bundle_id=manifest.bundle_id,
            format_version=manifest.format_version,
            pack_id=manifest.pack_id,
            files=manifest.files,
            content_hash=manifest.content_hash,
            signature_status="SIGNATURE_MISSING",
            signature_key_id=None,
        )

    write_manifest(bundle_root, manifest)
    return bundle_root
