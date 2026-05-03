"""Compile CMCF records into deterministic CSRF runtime indexes."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from vcse.cmcf.model import CMCFRecord
from vcse.cmcf.validate import validate_record
from vcse.runtime.model import CSRFIndex, CSRFRecord


def compile_cmcf_to_csrf(records: Iterable[CMCFRecord]) -> CSRFIndex:
    cmcf_records = list(records)
    for record in cmcf_records:
        issues = validate_record(record)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            raise ValueError(
                "CMCF_VALIDATION_FAILED: " + "; ".join(f"{issue.code}@{issue.path}" for issue in errors)
            )

    runtime_records = tuple(
        sorted(
            (
                CSRFRecord(
                    claim_id=record.claim.claim_id,
                    subject=record.claim.subject,
                    relation=record.claim.relation,
                    object=record.claim.object,
                    trust_tier=record.trust.trust_tier,
                    lifecycle_status=record.status.lifecycle_status,
                    verification_status=record.status.verification_status,
                    provenance_id=record.provenance.provenance_id,
                )
                for record in cmcf_records
            ),
            key=lambda item: item.claim_id,
        )
    )

    by_subject_builder: dict[str, list[int]] = defaultdict(list)
    by_relation_builder: dict[str, list[int]] = defaultdict(list)
    by_object_builder: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(runtime_records):
        by_subject_builder[record.subject].append(index)
        by_relation_builder[record.relation].append(index)
        by_object_builder[record.object].append(index)

    return CSRFIndex(
        records=runtime_records,
        by_subject={key: tuple(value) for key, value in sorted(by_subject_builder.items())},
        by_relation={key: tuple(value) for key, value in sorted(by_relation_builder.items())},
        by_object={key: tuple(value) for key, value in sorted(by_object_builder.items())},
    )
