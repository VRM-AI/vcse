"""Tests for performance benchmark harness."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from vcse.runtime.model import CSRFIndex, CSRFRecord
from vcse.runtime.serialize import save_csrf
from vcse.proof.model import ProofIndex, ProofPath, ProofStep
from vcse.proof.serialize import save_proof_index


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_csrf() -> CSRFIndex:
    rec = CSRFRecord(
        claim_id="c1",
        subject="Paris",
        relation="capital_of",
        object="France",
        trust_tier=1,
        lifecycle_status="active",
        verification_status="VERIFIED",
        provenance_id="prov:c1",
    )
    return CSRFIndex(
        records=(rec,),
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )


def _make_proof_index() -> ProofIndex:
    proof = ProofPath(
        proof_id="p1",
        result_claim_id="c1",
        result_subject="Paris",
        result_relation="capital_of",
        result_object="France",
        supporting_claim_ids=("c2",),
        steps=(ProofStep(
            claim_id="c2",
            subject="Paris",
            relation="capital_of",
            object="France",
            verification_status="VERIFIED",
        ),),
        path_length=1,
        trust_tier=1,
        verification_status="VERIFIED",
        source="materialized",
    )
    return ProofIndex(
        proofs=(proof,),
        by_result={"c1": (0,)},
        by_support={"c2": (0,)},
        by_subject={"Paris": (0,)},
        by_relation={"capital_of": (0,)},
        by_object={"France": (0,)},
    )


# ---------------------------------------------------------------------------
# 1. Benchmark report has deterministic structure
# ---------------------------------------------------------------------------

def test_benchmark_report_deterministic_structure():
    from vcse.perf.benchmark import run_runtime_benchmark
    from vcse.perf.model import BenchmarkReport

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        assert isinstance(report, BenchmarkReport)
        assert report.status in ("BENCHMARK_COMPLETE", "BENCHMARK_FAILED")
        assert report.case_count == len(report.results)


# ---------------------------------------------------------------------------
# 2. Benchmark supports LOAD_CSRF operation
# ---------------------------------------------------------------------------

def test_benchmark_includes_load_csrf():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        ops = {r.operation for r in report.results}
        assert "LOAD_CSRF" in ops


# ---------------------------------------------------------------------------
# 3. Benchmark supports QUERY_SUBJECT operation
# ---------------------------------------------------------------------------

def test_benchmark_includes_query_subject():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        ops = {r.operation for r in report.results}
        assert "QUERY_SUBJECT" in ops


# ---------------------------------------------------------------------------
# 4. Benchmark supports QUERY_RELATION operation
# ---------------------------------------------------------------------------

def test_benchmark_includes_query_relation():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        ops = {r.operation for r in report.results}
        assert "QUERY_RELATION" in ops


# ---------------------------------------------------------------------------
# 5. Benchmark supports QUERY_OBJECT operation
# ---------------------------------------------------------------------------

def test_benchmark_includes_query_object():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        ops = {r.operation for r in report.results}
        assert "QUERY_OBJECT" in ops


# ---------------------------------------------------------------------------
# 6. Benchmark accepts proof index when provided
# ---------------------------------------------------------------------------

def test_benchmark_accepts_proof_index():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        proof_path = Path(tmpdir) / "test.proof.json"
        save_csrf(_make_csrf(), csrf_path)
        save_proof_index(_make_proof_index(), proof_path)

        report = run_runtime_benchmark(csrf_path, proof_index_path=proof_path, iterations=1)
        ops = {r.operation for r in report.results}
        assert "PROOF_LOOKUP" in ops


# ---------------------------------------------------------------------------
# 7. Benchmark JSON contains no NaN/Inf
# ---------------------------------------------------------------------------

def test_benchmark_json_no_nan_inf():
    from vcse.perf.benchmark import run_runtime_benchmark
    from vcse.perf.report import benchmark_report_to_json

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        report = run_runtime_benchmark(csrf_path, iterations=1)
        text = benchmark_report_to_json(report)
        parsed = json.loads(text)  # would fail if NaN/Inf literals

        def _check(val):
            if isinstance(val, float):
                assert not math.isnan(val) and not math.isinf(val), f"NaN/Inf in JSON: {val}"
            elif isinstance(val, dict):
                for v in val.values():
                    _check(v)
            elif isinstance(val, list):
                for v in val:
                    _check(v)

        _check(parsed)


# ---------------------------------------------------------------------------
# 8. Benchmark does not mutate input files
# ---------------------------------------------------------------------------

def test_benchmark_does_not_mutate_input():
    from vcse.perf.benchmark import run_runtime_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)
        original = csrf_path.read_bytes()

        run_runtime_benchmark(csrf_path, iterations=2)

        assert csrf_path.read_bytes() == original


# ---------------------------------------------------------------------------
# 9. CLI: vcse runtime validate works
# ---------------------------------------------------------------------------

def test_cli_runtime_validate():
    from vcse.runtime.serialize import save_csrf
    import subprocess, sys

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        result = subprocess.run(
            [sys.executable, "-m", "vcse", "runtime", "validate", str(csrf_path), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "RUNTIME_VALID"


# ---------------------------------------------------------------------------
# 10. CLI: vcse proof validate works
# ---------------------------------------------------------------------------

def test_cli_proof_validate():
    import subprocess, sys

    with tempfile.TemporaryDirectory() as tmpdir:
        proof_path = Path(tmpdir) / "test.proof.json"
        save_proof_index(_make_proof_index(), proof_path)

        result = subprocess.run(
            [sys.executable, "-m", "vcse", "proof", "validate", str(proof_path), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "RUNTIME_VALID"


# ---------------------------------------------------------------------------
# 11. CLI: vcse perf benchmark works
# ---------------------------------------------------------------------------

def test_cli_perf_benchmark():
    import subprocess, sys

    with tempfile.TemporaryDirectory() as tmpdir:
        csrf_path = Path(tmpdir) / "test.csrf"
        save_csrf(_make_csrf(), csrf_path)

        result = subprocess.run(
            [sys.executable, "-m", "vcse", "perf", "benchmark",
             "--csrf", str(csrf_path), "--iterations", "1", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["status"] in ("BENCHMARK_COMPLETE", "BENCHMARK_FAILED")
