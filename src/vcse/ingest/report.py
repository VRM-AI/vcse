from __future__ import annotations

import json
from pathlib import Path

from vcse.ingest.models import IngestResult


def persist_ingest_report(result: IngestResult) -> Path:
    report_dir = Path(".vcse") / "ingest_runs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{result.run_id}.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
    return report_path
