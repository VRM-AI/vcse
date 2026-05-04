"""Performance benchmark data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    record_count: int
    operation: str
    elapsed_ms: float
    status: str


@dataclass(frozen=True)
class BenchmarkReport:
    status: str
    case_count: int
    results: tuple[BenchmarkCaseResult, ...]


# Status constants
BENCHMARK_COMPLETE = "BENCHMARK_COMPLETE"
BENCHMARK_FAILED = "BENCHMARK_FAILED"

# Operation constants
LOAD_CSRF = "LOAD_CSRF"
QUERY_SUBJECT = "QUERY_SUBJECT"
QUERY_RELATION = "QUERY_RELATION"
QUERY_OBJECT = "QUERY_OBJECT"
REASON_SIMPLE = "REASON_SIMPLE"
PROOF_LOOKUP = "PROOF_LOOKUP"
