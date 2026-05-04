"""Verification for VCSE pack distribution bundles."""

from __future__ import annotations

import json
from pathlib import Path

from vcse.distribution.manifest import SIGNATURE_NAME, build_bundle_manifest, manifest_payload_for_signature
from vcse.distribution.model import (
    BUNDLE_ERROR,
    BUNDLE_INVALID,
    BUNDLE_TAMPERED,
    BUNDLE_UNSIGNED,
    BUNDLE_VALID,
    INTEGRITY_INVALID,
    INTEGRITY_MISSING,
    INTEGRITY_VALID,
    BundleVerificationResult,
)
from vcse.integrity.keys import load_public_key
from vcse.integrity.model import SIGNATURE_MISSING, SIGNATURE_UNTRUSTED_KEY
from vcse.integrity.verify import verify_signature
from vcse.integrity.model import SignatureBlock


def _result(
    *,
    status: str,
    bundle_id: str | None,
    pack_id: str | None,
    file_count: int,
    signature_status: str,
    integrity_status: str,
    issues: list[str],
) -> BundleVerificationResult:
    return BundleVerificationResult(
        status=status,
        bundle_id=bundle_id,
        pack_id=pack_id,
        file_count=file_count,
        signature_status=signature_status,
        integrity_status=integrity_status,
        issues=tuple(issues),
    )


def verify_pack_bundle(
    bundle_path: Path,
    public_key_path: Path | None = None,
) -> BundleVerificationResult:
    root = Path(bundle_path)
    issues: list[str] = []

    manifest_file = root / "manifest.json"
    if not manifest_file.exists():
        return _result(
            status=BUNDLE_ERROR,
            bundle_id=None,
            pack_id=None,
            file_count=0,
            signature_status=SIGNATURE_MISSING,
            integrity_status=INTEGRITY_MISSING,
            issues=["MISSING_MANIFEST"],
        )

    try:
        raw_manifest = json.loads(manifest_file.read_text())
        manifest = build_bundle_manifest(root)
    except Exception as exc:
        return _result(
            status=BUNDLE_ERROR,
            bundle_id=None,
            pack_id=None,
            file_count=0,
            signature_status="SIGNATURE_ERROR",
            integrity_status=INTEGRITY_INVALID,
            issues=[f"MANIFEST_ERROR:{exc}"],
        )

    integrity_status = INTEGRITY_VALID
    expected_files = sorted(raw_manifest.get("files", []), key=lambda i: str(i.get("path", "")))
    for item in expected_files:
        rel = str(item.get("path", ""))
        expected = str(item.get("sha256", ""))
        if rel == SIGNATURE_NAME:
            continue
        p = root / rel
        if not p.exists():
            issues.append(f"MISSING_FILE:{rel}")
            integrity_status = INTEGRITY_INVALID
            continue
        import hashlib
        observed = hashlib.sha256(p.read_bytes()).hexdigest()
        if observed != expected:
            issues.append(f"HASH_MISMATCH:{rel}")
            integrity_status = INTEGRITY_INVALID

    signature_status = SIGNATURE_MISSING
    signature_file = root / SIGNATURE_NAME
    if signature_file.exists():
        if public_key_path is None:
            signature_status = SIGNATURE_UNTRUSTED_KEY
            issues.append("MISSING_PUBLIC_KEY")
        else:
            try:
                payload = json.loads(signature_file.read_text())
                block = SignatureBlock(
                    signature_id=str(payload.get("signature_id", "")),
                    algorithm=str(payload.get("algorithm", "")),
                    key_id=str(payload.get("key_id", "")),
                    signature=str(payload.get("signature", "")),
                    signed_hash=str(payload.get("signed_hash", "")),
                )
                public_key = load_public_key(public_key_path)
                verify_result = verify_signature(manifest_payload_for_signature(manifest), block, public_key)
                signature_status = verify_result.status
                if verify_result.reason:
                    issues.append(f"SIGNATURE_REASON:{verify_result.reason}")
            except Exception as exc:
                signature_status = "SIGNATURE_ERROR"
                issues.append(f"SIGNATURE_ERROR:{exc}")

    if integrity_status != INTEGRITY_VALID:
        status = BUNDLE_TAMPERED
    elif signature_status == "SIGNATURE_VALID":
        status = BUNDLE_VALID
    elif signature_status in {SIGNATURE_MISSING, SIGNATURE_UNTRUSTED_KEY}:
        status = BUNDLE_UNSIGNED
    elif signature_status in {"SIGNATURE_INVALID", "SIGNATURE_ERROR"}:
        status = BUNDLE_INVALID
    else:
        status = BUNDLE_ERROR

    return _result(
        status=status,
        bundle_id=manifest.bundle_id,
        pack_id=manifest.pack_id,
        file_count=len(expected_files),
        signature_status=signature_status,
        integrity_status=integrity_status,
        issues=issues,
    )
