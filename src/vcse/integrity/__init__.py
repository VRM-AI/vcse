"""VCSE cryptographic integrity, signing, and provenance layer."""

from vcse.integrity.canonical import canonical_bytes, canonical_json
from vcse.integrity.keys import generate_ed25519_keypair, key_id, load_private_key, load_public_key
from vcse.integrity.manifest import create_manifest
from vcse.integrity.model import SignatureBlock, SignatureVerificationResult
from vcse.integrity.signing import sign_data
from vcse.integrity.verify import verify_signature

__all__ = [
    "canonical_bytes",
    "canonical_json",
    "create_manifest",
    "generate_ed25519_keypair",
    "key_id",
    "load_private_key",
    "load_public_key",
    "sign_data",
    "SignatureBlock",
    "SignatureVerificationResult",
    "verify_signature",
]
