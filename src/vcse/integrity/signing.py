"""Sign data with Ed25519 private key."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from vcse.integrity.canonical import canonical_bytes
from vcse.integrity.keys import key_id
from vcse.integrity.model import SignatureBlock


def sign_data(data: Any, private_key: Ed25519PrivateKey) -> SignatureBlock:
    payload = canonical_bytes(data)
    digest = hashlib.sha256(payload).hexdigest()
    signature_bytes = private_key.sign(payload)
    pub = private_key.public_key()
    return SignatureBlock(
        signature_id=SignatureBlock.new_id(),
        algorithm="ed25519",
        key_id=key_id(pub),
        signature=base64.b64encode(signature_bytes).decode("ascii"),
        signed_hash=digest,
    )
