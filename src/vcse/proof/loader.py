"""Loader helpers for ProofIndex."""

from __future__ import annotations

import json
from pathlib import Path

from vcse.proof.compiler import compile_proofs_from_csrf
from vcse.proof.model import ProofIndex
from vcse.proof.serialize import proof_index_from_dict, save_proof_index
from vcse.runtime.serialize import load_csrf


def load_proof_index(path: Path) -> ProofIndex:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return proof_index_from_dict(payload)


def load_or_build_proof_index(
    csrf_path: Path,
    proof_path: Path | None = None,
    *,
    write_if_missing: bool = False,
) -> ProofIndex:
    if proof_path is not None and Path(proof_path).exists():
        return load_proof_index(proof_path)
    csrf = load_csrf(Path(csrf_path))
    index = compile_proofs_from_csrf(csrf)
    if write_if_missing and proof_path is not None:
        save_proof_index(index, Path(proof_path))
    return index
