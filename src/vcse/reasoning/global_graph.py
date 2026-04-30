"""Runtime-only global claim graph for cross-pack reasoning."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeClaim:
    subject: str
    relation: str
    object: str
    pack_id: str
    provenance: dict[str, Any]
    trust_tier: int
    claim_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "pack_id": self.pack_id,
            "provenance": dict(sorted(self.provenance.items())),
            "trust_tier": self.trust_tier,
            "claim_id": self.claim_id,
        }


class GlobalClaimGraph:
    """Deterministic runtime projection over claims from multiple packs."""

    def __init__(self, claims: list[RuntimeClaim]) -> None:
        self._claims = sorted(
            claims,
            key=lambda item: (item.subject, item.relation, item.object, item.pack_id, item.claim_id),
        )

    @property
    def claims(self) -> list[RuntimeClaim]:
        return list(self._claims)

    def by_relation(self, relation: str) -> list[RuntimeClaim]:
        return [item for item in self._claims if item.relation == relation]

    def by_subject(self, subject: str) -> list[RuntimeClaim]:
        return [item for item in self._claims if item.subject == subject]

    def by_pack_id(self, pack_id: str) -> list[RuntimeClaim]:
        return [item for item in self._claims if item.pack_id == pack_id]

    def to_dicts(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._claims]

    @classmethod
    def from_pack_dirs(cls, pack_dirs: list[Path]) -> "GlobalClaimGraph":
        claims: list[RuntimeClaim] = []
        for pack_dir in sorted(pack_dirs, key=lambda item: str(item)):
            claims.extend(_load_pack_claims(pack_dir))
        return cls(claims)


def build_global_claim_graph(pack_dirs: list[Path]) -> GlobalClaimGraph:
    return GlobalClaimGraph.from_pack_dirs(pack_dirs)


def _load_pack_claims(pack_dir: Path) -> list[RuntimeClaim]:
    import json

    manifest_path = pack_dir / "pack.json"
    if not manifest_path.exists():
        raise ValueError(f"missing pack.json in {pack_dir}")
    manifest = json.loads(manifest_path.read_text())
    pack_id = str(manifest.get("id", "")).strip() or pack_dir.name

    claims_path = pack_dir / "claims.jsonl"
    if not claims_path.exists():
        return []

    rows: list[RuntimeClaim] = []
    for line_no, line in enumerate(claims_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        subject = str(payload.get("subject", "")).strip()
        relation = str(payload.get("relation", "")).strip()
        obj = str(payload.get("object", "")).strip()
        if not subject or not relation or not obj:
            continue
        provenance = payload.get("provenance")
        if not isinstance(provenance, dict):
            provenance = {}
        trust_tier = _parse_trust_tier(payload.get("trust_tier", 0))
        claim_id = str(payload.get("claim_id", "")).strip()
        if not claim_id:
            claim_id = _claim_id_for(pack_id, subject, relation, obj, provenance, line_no)
        rows.append(
            RuntimeClaim(
                subject=subject,
                relation=relation,
                object=obj,
                pack_id=pack_id,
                provenance=provenance,
                trust_tier=trust_tier,
                claim_id=claim_id,
            )
        )
    return rows


def _parse_trust_tier(raw: Any) -> int:
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    text = str(raw or "").strip()
    if text.isdigit():
        return int(text)
    if text.upper().startswith("T"):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            return int(digits)
    return 0


def _claim_id_for(
    pack_id: str,
    subject: str,
    relation: str,
    obj: str,
    provenance: dict[str, Any],
    line_no: int,
) -> str:
    payload = "|".join(
        [
            pack_id,
            subject,
            relation,
            obj,
            str(provenance.get("source_id", "")),
            str(provenance.get("location", "")),
            str(line_no),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

