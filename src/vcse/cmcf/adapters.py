"""Bridge adapters from existing claim dicts to CMCF records."""

from __future__ import annotations

from typing import Any

from vcse.cmcf.hash import compute_claim_id, compute_content_hash, compute_provenance_id
from vcse.cmcf.model import (
    CMCFClaim,
    CMCFIntegrity,
    CMCFMetadata,
    CMCFProvenance,
    CMCFRecord,
    CMCFStatus,
    CMCFTrust,
)
from vcse.cmcf.serialize import record_to_dict


def claim_dict_to_cmcf(
    claim: dict,
    *,
    source_type: str,
    source_uri: str | None = None,
    locator: str | None = None,
    raw_value: str | None = None,
    lifecycle_status: str = "candidate",
    verification_status: str = "UNVERIFIED",
    certification_status: str = "NOT_CERTIFIED",
    provenance_status: str = "SOURCE_ATTACHED_UNVERIFIED",
    policy_status: str = "ALLOWED",
    trust_tier: int = 0,
    trust_policy: str = "default_certification",
    domain: str | None = None,
    language: str | None = None,
) -> CMCFRecord:
    subject = _claim_text(claim, "subject", fallback="entity")
    relation = _claim_text(claim, "relation")
    object_value = _claim_text(claim, "object", fallback="value")

    provenance_id = compute_provenance_id(
        source_type=source_type,
        source_uri=source_uri,
        locator=locator,
        raw_value=raw_value,
    )
    claim_id = str(claim.get("claim_id", "")).strip() or compute_claim_id(
        subject=subject,
        relation=relation,
        object=object_value,
        provenance_id=provenance_id,
    )
    method = "claim_dict_to_cmcf"
    record = CMCFRecord(
        cmcf_version="1.0",
        claim=CMCFClaim(
            claim_id=claim_id,
            subject=subject,
            relation=relation,
            object=object_value,
            value_type="entity",
        ),
        provenance=CMCFProvenance(
            provenance_id=provenance_id,
            source_type=source_type,
            source_uri=source_uri,
            retrieved_at=None,
            content_hash=None,
            locator=locator,
            raw_value=raw_value,
            method=method,
            mapping_id=None,
        ),
        status=CMCFStatus(
            lifecycle_status=lifecycle_status,
            verification_status=verification_status,
            certification_status=certification_status,
            provenance_status=provenance_status,
            policy_status=policy_status,
        ),
        trust=CMCFTrust(
            trust_tier=int(trust_tier),
            trust_policy=trust_policy,
        ),
        integrity=CMCFIntegrity(content_hash="sha256:pending"),
        metadata=CMCFMetadata(
            domain=domain,
            language=language,
            created_by="vcse.cmcf.adapters",
            schema_version="1.0",
        ),
    )

    payload = record_to_dict(record)
    content_hash = compute_content_hash(
        {
            "cmcf_version": payload["cmcf_version"],
            "claim": payload["claim"],
            "provenance": payload["provenance"],
            "status": payload["status"],
            "trust": payload["trust"],
            "metadata": payload["metadata"],
        }
    )
    return CMCFRecord(
        cmcf_version=record.cmcf_version,
        claim=record.claim,
        provenance=record.provenance,
        status=record.status,
        trust=record.trust,
        integrity=CMCFIntegrity(
            content_hash=content_hash,
            pack_hash=None,
            signature=None,
            signing_key_id=None,
        ),
        metadata=record.metadata,
    )


def _claim_text(claim: dict[str, Any], primary: str, fallback: str | None = None) -> str:
    value = str(claim.get(primary, "")).strip()
    if value:
        return value
    if fallback is not None:
        fallback_value = str(claim.get(fallback, "")).strip()
        if fallback_value:
            return fallback_value
    raise ValueError(f"missing claim field: {primary}")
