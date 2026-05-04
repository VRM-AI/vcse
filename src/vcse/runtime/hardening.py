"""Checked loaders for runtime artifacts that validate before returning."""

from __future__ import annotations

from pathlib import Path

from vcse.proof.model import ProofIndex
from vcse.proof.loader import load_proof_index
from vcse.proof.validate import validate_proof_index
from vcse.runtime.model import CSRFIndex
from vcse.runtime.serialize import load_csrf
from vcse.runtime.validate import validate_csrf_index


class RuntimeArtifactError(ValueError):
    """Raised when a runtime artifact fails structural validation."""


def load_csrf_checked(path: Path) -> CSRFIndex:
    """Load and validate a .csrf file. Raises RuntimeArtifactError if invalid."""
    index = load_csrf(Path(path))
    result = validate_csrf_index(index)
    if result.status != "RUNTIME_VALID":
        details = "; ".join(f"{iss.code}: {iss.message}" for iss in result.issues[:5])
        raise RuntimeArtifactError(
            f"CSRF_VALIDATION_FAILED ({result.issue_count} issues): {details}"
        )
    return index


def load_proof_index_checked(path: Path) -> ProofIndex:
    """Load and validate a .proof.json file. Raises RuntimeArtifactError if invalid."""
    index = load_proof_index(Path(path))
    result = validate_proof_index(index)
    if result.status != "RUNTIME_VALID":
        details = "; ".join(f"{iss.code}: {iss.message}" for iss in result.issues[:5])
        raise RuntimeArtifactError(
            f"PROOF_VALIDATION_FAILED ({result.issue_count} issues): {details}"
        )
    return index
