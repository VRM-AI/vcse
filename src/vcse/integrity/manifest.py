"""File manifest with content hashes for signing targets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def create_manifest(pack_path: str | Path) -> dict[str, Any]:
    root = Path(pack_path)
    files: dict[str, str] = {}
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name != "manifest.json":
            files[p.name] = _file_hash(p)
    return {
        "files": files,
        "algorithm": "sha256",
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
