"""Data models for signed pack distribution bundles."""

from __future__ import annotations

from dataclasses import dataclass

BUNDLE_VALID = "BUNDLE_VALID"
BUNDLE_INVALID = "BUNDLE_INVALID"
BUNDLE_UNSIGNED = "BUNDLE_UNSIGNED"
BUNDLE_TAMPERED = "BUNDLE_TAMPERED"
BUNDLE_ERROR = "BUNDLE_ERROR"

INTEGRITY_VALID = "INTEGRITY_VALID"
INTEGRITY_INVALID = "INTEGRITY_INVALID"
INTEGRITY_MISSING = "INTEGRITY_MISSING"


@dataclass(frozen=True)
class PackBundleManifest:
    bundle_id: str
    format_version: str
    pack_id: str
    files: tuple[dict, ...]
    content_hash: str
    signature_status: str | None = None
    signature_key_id: str | None = None


@dataclass(frozen=True)
class BundleVerificationResult:
    status: str
    bundle_id: str | None
    pack_id: str | None
    file_count: int
    signature_status: str
    integrity_status: str
    issues: tuple[str, ...]
