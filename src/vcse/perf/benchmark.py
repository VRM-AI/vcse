"""Deterministic runtime benchmark harness."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from vcse.perf.model import (
    BENCHMARK_COMPLETE,
    BENCHMARK_FAILED,
    LOAD_CSRF,
    PROOF_LOOKUP,
    QUERY_OBJECT,
    QUERY_RELATION,
    QUERY_SUBJECT,
    BenchmarkCaseResult,
    BenchmarkReport,
)
from vcse.runtime.serialize import load_csrf


def run_runtime_benchmark(
    csrf_path: Path,
    proof_index_path: Path | None = None,
    iterations: int = 3,
) -> BenchmarkReport:
    results: list[BenchmarkCaseResult] = []

    try:
        # LOAD_CSRF
        elapsed = _time_op(lambda: load_csrf(Path(csrf_path)), iterations)
        csrf = load_csrf(Path(csrf_path))
        record_count = len(csrf.records)
        results.append(BenchmarkCaseResult(
            case_id=f"load_csrf_{uuid.uuid4().hex[:8]}",
            record_count=record_count,
            operation=LOAD_CSRF,
            elapsed_ms=elapsed,
            status="OK",
        ))

        # QUERY_SUBJECT
        first_subject = next(iter(csrf.by_subject), None)
        results.append(BenchmarkCaseResult(
            case_id=f"query_subject_{uuid.uuid4().hex[:8]}",
            record_count=record_count,
            operation=QUERY_SUBJECT,
            elapsed_ms=_time_op(
                lambda: csrf.by_subject.get(first_subject, ()),
                iterations,
            ),
            status="OK",
        ))

        # QUERY_RELATION
        first_relation = next(iter(csrf.by_relation), None)
        results.append(BenchmarkCaseResult(
            case_id=f"query_relation_{uuid.uuid4().hex[:8]}",
            record_count=record_count,
            operation=QUERY_RELATION,
            elapsed_ms=_time_op(
                lambda: csrf.by_relation.get(first_relation, ()),
                iterations,
            ),
            status="OK",
        ))

        # QUERY_OBJECT
        first_object = next(iter(csrf.by_object), None)
        results.append(BenchmarkCaseResult(
            case_id=f"query_object_{uuid.uuid4().hex[:8]}",
            record_count=record_count,
            operation=QUERY_OBJECT,
            elapsed_ms=_time_op(
                lambda: csrf.by_object.get(first_object, ()),
                iterations,
            ),
            status="OK",
        ))

        # PROOF_LOOKUP (only if proof index provided)
        if proof_index_path is not None and Path(proof_index_path).exists():
            from vcse.proof.loader import load_proof_index
            proof_index = load_proof_index(Path(proof_index_path))
            first_result = next(iter(proof_index.by_result), None)
            results.append(BenchmarkCaseResult(
                case_id=f"proof_lookup_{uuid.uuid4().hex[:8]}",
                record_count=len(proof_index.proofs),
                operation=PROOF_LOOKUP,
                elapsed_ms=_time_op(
                    lambda: proof_index.by_result.get(first_result, ()),
                    iterations,
                ),
                status="OK",
            ))

    except Exception as exc:
        results.append(BenchmarkCaseResult(
            case_id="error",
            record_count=0,
            operation=LOAD_CSRF,
            elapsed_ms=0.0,
            status=f"ERROR: {exc}",
        ))
        return BenchmarkReport(
            status=BENCHMARK_FAILED,
            case_count=len(results),
            results=tuple(results),
        )

    return BenchmarkReport(
        status=BENCHMARK_COMPLETE,
        case_count=len(results),
        results=tuple(results),
    )


def _time_op(fn, iterations: int) -> float:
    times: list[float] = []
    for _ in range(max(1, iterations)):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return sum(times) / len(times)
