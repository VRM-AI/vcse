"""Tests for vcse.integrity signing and verification layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vcse.integrity.canonical import canonical_bytes, canonical_json
from vcse.integrity.keys import generate_ed25519_keypair, key_id
from vcse.integrity.model import SignatureBlock, SignatureVerificationResult
from vcse.integrity.signing import sign_data
from vcse.integrity.verify import verify_signature
from vcse.integrity.manifest import create_manifest


# ---------------------------------------------------------------------------
# 1. Deterministic signing — same data + key → same signed_hash
# ---------------------------------------------------------------------------

def test_signing_is_deterministic():
    private_key, public_key = generate_ed25519_keypair()
    data = {"subject": "Paris", "relation": "capital_of", "object": "France"}

    block1 = sign_data(data, private_key)
    block2 = sign_data(data, private_key)

    assert block1.signed_hash == block2.signed_hash
    assert block1.algorithm == "ed25519"
    assert block1.key_id == block2.key_id


# ---------------------------------------------------------------------------
# 2. Signature verification success
# ---------------------------------------------------------------------------

def test_signature_verification_success():
    private_key, public_key = generate_ed25519_keypair()
    data = {"value": 42, "name": "test"}

    block = sign_data(data, private_key)
    result = verify_signature(data, block, public_key)

    assert result.status == "SIGNATURE_VALID"


# ---------------------------------------------------------------------------
# 3. Tampered data → SIGNATURE_INVALID
# ---------------------------------------------------------------------------

def test_tampered_data_is_invalid():
    private_key, public_key = generate_ed25519_keypair()
    data = {"value": 42}

    block = sign_data(data, private_key)
    tampered = {"value": 99}
    result = verify_signature(tampered, block, public_key)

    assert result.status == "SIGNATURE_INVALID"


# ---------------------------------------------------------------------------
# 4. Wrong key → SIGNATURE_INVALID
# ---------------------------------------------------------------------------

def test_wrong_key_is_invalid():
    private_key, public_key = generate_ed25519_keypair()
    _, wrong_public_key = generate_ed25519_keypair()
    data = {"value": 42}

    block = sign_data(data, private_key)
    result = verify_signature(data, block, wrong_public_key)

    assert result.status == "SIGNATURE_INVALID"


# ---------------------------------------------------------------------------
# 5. Missing signature → SIGNATURE_MISSING
# ---------------------------------------------------------------------------

def test_missing_signature_status():
    _, public_key = generate_ed25519_keypair()
    data = {"value": 42}

    missing_block = SignatureBlock(
        signature_id="",
        algorithm="ed25519",
        key_id="",
        signature="",
        signed_hash="",
    )
    result = verify_signature(data, missing_block, public_key)

    assert result.status == "SIGNATURE_MISSING"


# ---------------------------------------------------------------------------
# 6. Canonicalization consistency
# ---------------------------------------------------------------------------

def test_canonicalization_is_consistent():
    data_a = {"z": 1, "a": 2, "m": 3}
    data_b = {"m": 3, "z": 1, "a": 2}

    assert canonical_json(data_a) == canonical_json(data_b)
    assert canonical_bytes(data_a) == canonical_bytes(data_b)


def test_canonicalization_rejects_nan():
    with pytest.raises((ValueError, TypeError)):
        canonical_json({"value": float("nan")})


def test_canonicalization_rejects_inf():
    with pytest.raises((ValueError, TypeError)):
        canonical_json({"value": float("inf")})


# ---------------------------------------------------------------------------
# 7. Manifest hash consistency
# ---------------------------------------------------------------------------

def test_manifest_hash_consistency():
    with tempfile.TemporaryDirectory() as tmpdir:
        pack_path = Path(tmpdir)
        (pack_path / "claims.jsonl").write_text(
            json.dumps({"subject": "A", "relation": "r", "object": "B"}) + "\n"
        )
        (pack_path / "pack.json").write_text(json.dumps({"name": "test-pack"}) + "\n")

        manifest1 = create_manifest(pack_path)
        manifest2 = create_manifest(pack_path)

        assert manifest1 == manifest2
        assert "files" in manifest1
        assert "algorithm" in manifest1


def test_manifest_includes_all_present_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        pack_path = Path(tmpdir)
        (pack_path / "claims.jsonl").write_text("{}\n")
        (pack_path / "pack.json").write_text("{}\n")

        manifest = create_manifest(pack_path)

        assert isinstance(manifest["files"], dict)
        for fname in manifest["files"]:
            assert (pack_path / fname).exists()


# ---------------------------------------------------------------------------
# Model integrity
# ---------------------------------------------------------------------------

def test_signature_block_fields():
    private_key, _ = generate_ed25519_keypair()
    data = {"x": 1}
    block = sign_data(data, private_key)

    assert block.algorithm == "ed25519"
    assert len(block.key_id) == 64  # sha256 hex
    assert len(block.signature) > 0
    assert len(block.signed_hash) == 64  # sha256 hex


def test_key_id_is_sha256_of_public_key_bytes():
    from cryptography.hazmat.primitives import serialization
    import hashlib

    private_key, public_key = generate_ed25519_keypair()
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    expected_key_id = hashlib.sha256(pub_bytes).hexdigest()

    assert key_id(public_key) == expected_key_id
