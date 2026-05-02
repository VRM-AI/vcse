"""CMCF: Correctness Model Canonical Format foundation."""

from vcse.cmcf.adapters import claim_dict_to_cmcf
from vcse.cmcf.hash import (
    canonical_json,
    compute_claim_id,
    compute_content_hash,
    compute_provenance_id,
    sha256_text,
)
from vcse.cmcf.model import (
    CMCFClaim,
    CMCFIntegrity,
    CMCFMetadata,
    CMCFProvenance,
    CMCFRecord,
    CMCFStatus,
    CMCFTrust,
)
from vcse.cmcf.serialize import record_from_dict, record_from_json, record_to_dict, record_to_json
from vcse.cmcf.validate import CMCFValidationIssue, validate_record

__all__ = [
    "CMCFClaim",
    "CMCFIntegrity",
    "CMCFMetadata",
    "CMCFProvenance",
    "CMCFRecord",
    "CMCFStatus",
    "CMCFTrust",
    "CMCFValidationIssue",
    "canonical_json",
    "claim_dict_to_cmcf",
    "compute_claim_id",
    "compute_content_hash",
    "compute_provenance_id",
    "record_from_dict",
    "record_from_json",
    "record_to_dict",
    "record_to_json",
    "sha256_text",
    "validate_record",
]
