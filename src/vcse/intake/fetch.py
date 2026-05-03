from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from vcse.intake.source import SourceRef

_MAX_BYTES = 25 * 1024 * 1024
_TIMEOUT_SECONDS = 20


class SourceFetchError(ValueError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


class SourceFetcher:
    def fetch(self, source: str) -> SourceRef:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            return self._fetch_url(source)
        return self._fetch_local(source)

    def _fetch_local(self, source: str) -> SourceRef:
        path = Path(source)
        if not path.exists():
            raise SourceFetchError(f"INVALID_SOURCE: path not found: {source}")
        resolved = path.resolve()
        if path.is_dir():
            return SourceRef(
                original=source,
                source_type="directory",
                uri=f"file://{resolved}",
                local_path=str(resolved),
                content_type=None,
                content_hash=None,
            )
        digest = _sha256_bytes(path.read_bytes())
        return SourceRef(
            original=source,
            source_type="file",
            uri=f"file://{resolved}",
            local_path=str(resolved),
            content_type=None,
            content_hash=digest,
        )

    def _fetch_url(self, source: str) -> SourceRef:
        req = Request(source, headers={"User-Agent": "vcse/6.1.0"})
        with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:  # noqa: S310
            content_type = resp.headers.get("Content-Type")
            data = resp.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            raise SourceFetchError("SOURCE_TOO_LARGE: max size is 25MB")

        digest = _sha256_bytes(data)
        cache_dir = Path(".vcse") / "source_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_stem = digest.replace(":", "_")
        data_path = cache_dir / f"{cache_stem}.data"
        meta_path = cache_dir / f"{cache_stem}.json"
        data_path.write_bytes(data)
        meta_path.write_text(
            json.dumps(
                {
                    "source": source,
                    "content_type": content_type,
                    "content_hash": digest,
                    "size": len(data),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

        return SourceRef(
            original=source,
            source_type="url",
            uri=source,
            local_path=str(data_path.resolve()),
            content_type=content_type,
            content_hash=digest,
        )
