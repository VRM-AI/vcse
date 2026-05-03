# VCSE Integrity Layer (v6.7.0)

Cryptographic signing and provenance guarantees. Answers: "Was this data produced by a known signer and has it been altered?" — not "Is this data true?"

## Core Invariant

`SIGNATURE_VALID ≠ VERIFIED ≠ TRUSTED`. Signatures never promote trust, bypass verifier, or affect T4/T5 gating.

## Modules

| Module | Purpose |
|--------|---------|
| `vcse.integrity.canonical` | Deterministic JSON canonicalization (NaN/Inf rejected) |
| `vcse.integrity.keys` | Ed25519 keypair generation, PEM load/save, key_id |
| `vcse.integrity.model` | `SignatureBlock`, `SignatureVerificationResult`, status constants |
| `vcse.integrity.signing` | `sign_data(data, private_key) → SignatureBlock` |
| `vcse.integrity.verify` | `verify_signature(data, block, public_key) → SignatureVerificationResult` |
| `vcse.integrity.manifest` | `create_manifest(pack_path) → dict` |

## Status Codes

- `SIGNATURE_VALID` — signature verified
- `SIGNATURE_INVALID` — hash/signature/key mismatch
- `SIGNATURE_MISSING` — no signature present
- `SIGNATURE_UNTRUSTED_KEY` — key not in trusted set
- `SIGNATURE_ERROR` — unexpected error during verification

## CLI

```sh
vcse integrity keygen --out <dir>
vcse integrity sign <file> --key <private.pem>
vcse integrity verify <file> --key <public.pem>
vcse integrity manifest <pack_dir>
vcse integrity verify-manifest <manifest.json> --pack <pack_dir>
```

All outputs include `signature_status`, `reason`, `key_id`.

## Key System

Ed25519 only. `key_id = sha256(raw_public_key_bytes)`. No network key resolution. No auto-trust.
