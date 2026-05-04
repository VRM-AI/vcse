from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from vcse.distribution.bundle import create_pack_bundle
from vcse.distribution.inspect import inspect_pack_bundle
from vcse.distribution.verify import verify_pack_bundle
from vcse.integrity.keys import generate_ed25519_keypair


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _example_pack() -> Path:
    return _repo_root() / "examples" / "packs" / "logic_basic"


def _copy_pack(tmp_path: Path) -> Path:
    dst = tmp_path / "pack"
    shutil.copytree(_example_pack(), dst)
    return dst


def _write_keypair(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    private_key, public_key = generate_ed25519_keypair()
    priv_path = tmp_path / "signing_private.pem"
    pub_path = tmp_path / "signing_public.pem"
    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_path, pub_path


def _run_cli(*args: str, pack_home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(_repo_root() / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    env["VCSE_PACK_HOME"] = str(pack_home)
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, text=True, env=env)


def test_bundle_manifest_deterministic(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    out = tmp_path / "out"
    b1 = create_pack_bundle(pack, out)
    m1 = json.loads((b1 / "manifest.json").read_text())
    b2 = create_pack_bundle(pack, out)
    m2 = json.loads((b2 / "manifest.json").read_text())
    assert m1 == m2


def test_bundle_includes_required_pack_files(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    assert (bundle / "pack" / "pack.json").exists()
    assert (bundle / "pack" / "claims.jsonl").exists()
    assert (bundle / "pack" / "provenance.jsonl").exists()


def test_unsigned_bundle_integrity_valid_with_missing_signature(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    result = verify_pack_bundle(bundle)
    assert result.integrity_status == "INTEGRITY_VALID"
    assert result.signature_status == "SIGNATURE_MISSING"
    assert result.status == "BUNDLE_UNSIGNED"


def test_signed_bundle_signature_valid(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    priv, pub = _write_keypair(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out", private_key_path=priv)
    result = verify_pack_bundle(bundle, public_key_path=pub)
    assert result.signature_status == "SIGNATURE_VALID"
    assert result.status == "BUNDLE_VALID"


def test_signed_bundle_wrong_key_invalid(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    priv, _ = _write_keypair(tmp_path)
    _, wrong_pub = _write_keypair(tmp_path / "other")
    bundle = create_pack_bundle(pack, tmp_path / "out", private_key_path=priv)
    result = verify_pack_bundle(bundle, public_key_path=wrong_pub)
    assert result.signature_status == "SIGNATURE_INVALID"
    assert result.status == "BUNDLE_INVALID"


def test_tampered_claims_fails_verification(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    claims = bundle / "pack" / "claims.jsonl"
    claims.write_text(claims.read_text() + "{\"tampered\": true}\n")
    result = verify_pack_bundle(bundle)
    assert result.status in {"BUNDLE_TAMPERED", "BUNDLE_INVALID"}
    assert result.integrity_status == "INTEGRITY_INVALID"


def test_missing_file_fails_verification(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    (bundle / "pack" / "provenance.jsonl").unlink()
    result = verify_pack_bundle(bundle)
    assert result.integrity_status == "INTEGRITY_INVALID"


def test_signature_does_not_imply_verified(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    priv, pub = _write_keypair(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out", private_key_path=priv)
    result = verify_pack_bundle(bundle, public_key_path=pub)
    assert result.status == "BUNDLE_VALID"
    assert "VERIFIED" not in result.status


def test_bundle_creation_does_not_mutate_source_pack(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    before = {name: (pack / name).read_bytes() for name in ("pack.json", "claims.jsonl", "provenance.jsonl")}
    create_pack_bundle(pack, tmp_path / "out")
    after = {name: (pack / name).read_bytes() for name in ("pack.json", "claims.jsonl", "provenance.jsonl")}
    assert before == after


def test_inspect_bundle_stable_json(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    one = inspect_pack_bundle(bundle)
    two = inspect_pack_bundle(bundle)
    assert one == two
    assert set(one.keys()) == {
        "bundle_id",
        "pack_id",
        "file_count",
        "signature_status",
        "integrity_status",
        "content_hash",
        "files",
    }


def test_cli_bundle_command_works(tmp_path: Path) -> None:
    home = tmp_path / "home"
    out = tmp_path / "out"
    result = _run_cli("pack", "bundle", str(_example_pack()), "--output", str(out), "--json", pack_home=home)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "BUNDLE_CREATED"


def test_cli_verify_bundle_command_works(tmp_path: Path) -> None:
    home = tmp_path / "home"
    out = tmp_path / "out"
    _run_cli("pack", "bundle", str(_example_pack()), "--output", str(out), pack_home=home)
    bundle = next(out.glob("*.vcsepack"))
    result = _run_cli("pack", "verify-bundle", str(bundle), "--json", pack_home=home)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "BUNDLE_UNSIGNED"
    assert payload["signature_status"] == "SIGNATURE_MISSING"


def test_cli_inspect_bundle_command_works(tmp_path: Path) -> None:
    home = tmp_path / "home"
    out = tmp_path / "out"
    _run_cli("pack", "bundle", str(_example_pack()), "--output", str(out), pack_home=home)
    bundle = next(out.glob("*.vcsepack"))
    result = _run_cli("pack", "inspect-bundle", str(bundle), "--json", pack_home=home)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "bundle_id" in payload
    assert "integrity_status" in payload


def test_statuses_are_upper_snake_case(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    result = verify_pack_bundle(bundle)
    inspect_payload = inspect_pack_bundle(bundle)
    assert result.status == result.status.upper()
    assert result.signature_status == result.signature_status.upper()
    assert result.integrity_status == result.integrity_status.upper()
    assert str(inspect_payload["signature_status"]).upper() == inspect_payload["signature_status"]
    assert str(inspect_payload["integrity_status"]).upper() == inspect_payload["integrity_status"]


def test_false_verification_invariants_unaffected(tmp_path: Path) -> None:
    pack = _copy_pack(tmp_path)
    bundle = create_pack_bundle(pack, tmp_path / "out")
    result = verify_pack_bundle(bundle)
    assert "VERIFIED" not in result.status
    assert result.signature_status in {
        "SIGNATURE_VALID",
        "SIGNATURE_INVALID",
        "SIGNATURE_MISSING",
        "SIGNATURE_UNTRUSTED_KEY",
        "SIGNATURE_ERROR",
    }
