"""Proof index layer (v6.4).

Compiled, derived view of proof paths over CMCF/.csrf data.
Never canonical truth; reproducible and disposable.
"""

from vcse.proof.compiler import (
    compile_proofs_from_csrf,
    compile_proofs_from_records,
)
from vcse.proof.explain import (
    proof_path_to_explanation_trace,
    select_best_proof,
)
from vcse.proof.index import build_proof_index
from vcse.proof.loader import load_or_build_proof_index, load_proof_index
from vcse.proof.model import ProofIndex, ProofPath, ProofStep
from vcse.proof.serialize import (
    proof_index_to_dict,
    proof_index_from_dict,
    save_proof_index,
)

__all__ = [
    "ProofStep",
    "ProofPath",
    "ProofIndex",
    "build_proof_index",
    "compile_proofs_from_csrf",
    "compile_proofs_from_records",
    "save_proof_index",
    "load_proof_index",
    "load_or_build_proof_index",
    "proof_index_to_dict",
    "proof_index_from_dict",
    "select_best_proof",
    "proof_path_to_explanation_trace",
]
