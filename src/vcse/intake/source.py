from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRef:
    original: str
    source_type: str
    uri: str
    local_path: str | None
    content_type: str | None
    content_hash: str | None
