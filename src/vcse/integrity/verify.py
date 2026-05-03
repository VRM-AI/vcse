"""Verify Ed25519 signatures. Never raises for normal failures."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from vcse.integrity.canonical import canonical_bytes
from vcse.integrity.keys import key_id as compute_key_id
from vcse.integrity.model import (
    SIGNATURE_ERROR,
    SIGNATURE_INVALID,
    SIGNATURE_MISSING,
    SIGNATURE_VALID,
    SignatureBlock,
    SignatureVerificationResult,
)


def verify_signature(
    data: Any,
    signature_block: SignatureBlock,
    public_key: Ed25519PublicKey,
) -> SignatureVerificationResult:
    if not signature_block.signature or not signature_block.signed_hash:
        return SignatureVerificationResult(status=SIGNATURE_MISSING, reason="empty signature block")

    try:
        payload = canonical_bytes(data)
        digest = hashlib.sha256(payload).hexdigest()

        if digest != signature_block.signed_hash:
            return SignatureVerificationResult(status=SIGNATURE_INVALID, reason="hash mismatch")

        expected_key_id = compute_key_id(public_key)
        if signature_block.key_id and signature_block.key_id != expected_key_id:
            return SignatureVerificationResult(status=SIGNATURE_INVALID, reason="key_id mismatch")

        sig_bytes = base64.b64decode(signature_block.signature)
        public_key.verify(sig_bytes, payload)
        return SignatureVerificationResult(status=SIGNATURE_VALID)
    except InvalidSignature:
        return SignatureVerificationResult(status=SIGNATURE_INVALID, reason="invalid signature")
    except Exception as exc:
        return SignatureVerificationResult(status=SIGNATURE_ERROR, reason=str(exc))
