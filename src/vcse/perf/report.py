"""Benchmark report serialization."""

from __future__ import annotations

import json
from typing import Any

from vcse.perf.model import BenchmarkReport


def benchmark_report_to_dict(report: BenchmarkReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "case_count": report.case_count,
        "results": sorted(
            [
                {
                    "case_id": r.case_id,
                    "record_count": r.record_count,
                    "operation": r.operation,
                    "elapsed_ms": r.elapsed_ms,
                    "status": r.status,
                }
                for r in report.results
            ],
            key=lambda x: x["case_id"],
        ),
    }


def benchmark_report_to_json(report: BenchmarkReport) -> str:
    return json.dumps(
        benchmark_report_to_dict(report),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
