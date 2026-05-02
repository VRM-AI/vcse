"""CMCF canonical record models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CMCFClaim:
    claim_id: str
    subject: str
    relation: str
    object: str
    value_type: str = "entity"


@dataclass(frozen=True)
class CMCFProvenance:
    provenance_id: str
    source_type: str
    source_uri: str | None
    retrieved_at: str | None
    content_hash: str | None
    locator: str | None
    raw_value: str | None
    method: str
    mapping_id: str | None = None


@dataclass(frozen=True)
class CMCFStatus:
    lifecycle_status: str
    verification_status: str
    certification_status: str
    provenance_status: str
    policy_status: str


@dataclass(frozen=True)
class CMCFTrust:
    trust_tier: int
    trust_policy: str


@dataclass(frozen=True)
class CMCFIntegrity:
    content_hash: str
    pack_hash: str | None = None
    signature: str | None = None
    signing_key_id: str | None = None


@dataclass(frozen=True)
class CMCFMetadata:
    domain: str | None
    language: str | None
    created_by: str
    schema_version: str = "1.0"


@dataclass(frozen=True)
class CMCFRecord:
    cmcf_version: str
    claim: CMCFClaim
    provenance: CMCFProvenance
    status: CMCFStatus
    trust: CMCFTrust
    integrity: CMCFIntegrity
    metadata: CMCFMetadata
