from __future__ import annotations

from vcse.cmcf.validate import validate_record
from vcse.intake.detect import FormatDetector
from vcse.intake.fetch import SourceFetcher
from vcse.intake.result import IntakeResult
from vcse.intake.router import IntakeRouter


def normalize_source_to_cmcf(source: str, profile: str | None = None, limit: int | None = None) -> IntakeResult:
    fetcher = SourceFetcher()
    detector = FormatDetector()
    router = IntakeRouter()

    source_ref = fetcher.fetch(source)
    detection = detector.detect(source_ref)
    adapter = router.select_adapter(detection.detected_format)
    if adapter is None:
        return IntakeResult(
            status="INTAKE_UNSUPPORTED_FORMAT",
            source=source_ref,
            detected_format=detection.detected_format,
            adapter_id=None,
            profile_id=profile,
            row_count=0,
            cmcf_record_count=0,
            validation_issue_count=0,
            records=tuple(),
            errors=(f"UNKNOWN_FORMAT: {detection.detected_format}",),
        )

    extracted = adapter.extract(source_ref)
    rows = tuple(item.data for item in extracted)
    if limit is not None and limit >= 0:
        rows = rows[:limit]

    selected_profile = router.select_profile(rows, requested_profile=profile)
    records = selected_profile.to_cmcf(rows, source_ref)

    issue_count = 0
    errors: list[str] = []
    for rec in records:
        issues = validate_record(rec)
        issue_count += len(issues)
        for issue in issues:
            errors.append(f"{issue.code}:{issue.path}")

    status = "INTAKE_COMPLETE" if issue_count == 0 else "INTAKE_INVALID"
    return IntakeResult(
        status=status,
        source=source_ref,
        detected_format=detection.detected_format,
        adapter_id=adapter.adapter_id,
        profile_id=selected_profile.profile_id,
        row_count=len(rows),
        cmcf_record_count=len(records),
        validation_issue_count=issue_count,
        records=records,
        errors=tuple(errors),
    )
