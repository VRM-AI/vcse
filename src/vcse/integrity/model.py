"""Data models for integrity signing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SignatureBlock:
    signature_id: str
    algorithm: str  # "ed25519"
    key_id: str
    signature: str  # base64-encoded
    signed_hash: str  # sha256 hex of canonical payload

    @classmethod
    def new_id(cls) -> str:
        return str(uuid.uuid4())


@dataclass(frozen=True)
class SignatureVerificationResult:
    status: str
    reason: str = ""


# Status constants
SIGNATURE_VALID = "SIGNATURE_VALID"
SIGNATURE_INVALID = "SIGNATURE_INVALID"
SIGNATURE_MISSING = "SIGNATURE_MISSING"
SIGNATURE_UNTRUSTED_KEY = "SIGNATURE_UNTRUSTED_KEY"
SIGNATURE_ERROR = "SIGNATURE_ERROR"
