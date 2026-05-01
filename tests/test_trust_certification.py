from __future__ import annotations

import json
from pathlib import Path

from vcse.cli import run_reason, run_trust_certify
from vcse.trust import CertificationGate, TrustPolicy, certification_report_payload


def _write_pack(
    pack_dir: Path,
    *,
    pack_id: str,
    lifecycle_status: str = "candidate",
    claims: list[dict] | None = None,
    provenance_rows: list[dict] | None = None,
) -> Path:
    pack_dir.mkdir(parents=True, exist_ok=True)
    claims = claims or []
    provenance_rows = provenance_rows if provenance_rows is not None else []

    (pack_dir / "pack.json").write_text(
        json.dumps(
            {
                "id": pack_id,
                "pack_id": pack_id,
                "version": "1.0.0",
                "lifecycle_status": lifecycle_status,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (pack_dir / "claims.jsonl").write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in claims) + ("\n" if claims else "")
    )
    (pack_dir / "provenance.jsonl").write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in provenance_rows) + ("\n" if provenance_rows else "")
    )
    return pack_dir


def _base_claim(
    *,
    claim_id: str,
    subject: str,
    relation: str,
    object_: str,
    source_id: str = "src-1",
    trust_tier: int = 1,
) -> dict:
    return {
        "claim_id": claim_id,
        "subject": subject,
        "relation": relation,
        "object": object_,
        "source_id": source_id,
        "trust_tier": trust_tier,
        "provenance": {
            "source_type": "pack",
            "source_id": source_id,
            "location": f"claims.jsonl:{claim_id}",
            "evidence_text": f"{subject} {relation} {object_}",
        },
    }


def test_candidate_pack_with_full_provenance_certifies_successfully(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path / "packs" / "candidate_ok",
        pack_id="candidate_ok",
        claims=[_base_claim(claim_id="c1", subject="Socrates", relation="is_a", object_="man")],
        provenance_rows=[{"source_id": "src-1", "source_type": "pack", "location": "claims.jsonl:1", "evidence_text": "ok"}],
    )
    result = CertificationGate.certify_pack(pack, TrustPolicy())
    assert result.status == "CERTIFICATION_PASSED"
    assert result.certified_claim_count == 1
    assert result.blocked_claim_count == 0


def test_missing_provenance_fails_certification(tmp_path: Path) -> None:
    claim = _base_claim(claim_id="c1", subject="Socrates", relation="is_a", object_="man")
    claim.pop("provenance")
    pack = _write_pack(tmp_path / "packs" / "missing_prov", pack_id="missing_prov", claims=[claim], provenance_rows=[])
    result = CertificationGate.certify_pack(pack, TrustPolicy())
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert result.missing_provenance_count > 0
    assert any(issue.code in {"MISSING_PROVENANCE_FOR_CLAIM", "PROVENANCE_COUNT_MISMATCH"} for issue in result.issues)


def test_duplicate_claims_fail_certification(tmp_path: Path) -> None:
    claim_a = _base_claim(claim_id="c1", subject="A", relation="is", object_="B")
    claim_b = _base_claim(claim_id="c2", subject="A", relation="is", object_="B")
    pack = _write_pack(
        tmp_path / "packs" / "dup",
        pack_id="dup",
        claims=[claim_a, claim_b],
        provenance_rows=[{"source_id": "src-1"}, {"source_id": "src-1"}],
    )
    result = CertificationGate.certify_pack(pack, TrustPolicy())
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert any(issue.code == "DUPLICATE_CLAIM_KEY" for issue in result.issues)


def test_conflict_blocks_certification_when_allow_conflicts_false(tmp_path: Path) -> None:
    claim_a = _base_claim(claim_id="c1", subject="France", relation="has_capital", object_="Paris")
    claim_b = _base_claim(claim_id="c2", subject="France", relation="has_capital", object_="Lyon")
    pack = _write_pack(
        tmp_path / "packs" / "conflict",
        pack_id="conflict",
        claims=[claim_a, claim_b],
        provenance_rows=[{"source_id": "src-1"}, {"source_id": "src-2"}],
    )
    result = CertificationGate.certify_pack(pack, TrustPolicy(allow_conflicts=False))
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert result.conflict_count > 0
    assert any(issue.code == "CONFLICTS_PRESENT" for issue in result.issues)


def test_blocked_relation_fails_certification(tmp_path: Path) -> None:
    claim = _base_claim(claim_id="c1", subject="Socrates", relation="forbidden_relation", object_="x")
    pack = _write_pack(
        tmp_path / "packs" / "blocked_rel",
        pack_id="blocked_rel",
        claims=[claim],
        provenance_rows=[{"source_id": "src-1"}],
    )
    policy = TrustPolicy(blocked_relations=("forbidden_relation",))
    result = CertificationGate.certify_pack(pack, policy)
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert any(issue.code == "RELATION_BLOCKED" for issue in result.issues)


def test_certified_output_pack_created_without_mutating_original(tmp_path: Path) -> None:
    packs_root = tmp_path / "packs"
    source = _write_pack(
        packs_root / "source_pack",
        pack_id="source_pack",
        claims=[_base_claim(claim_id="c1", subject="Socrates", relation="is_a", object_="man")],
        provenance_rows=[{"source_id": "src-1", "source_type": "pack", "location": "claims:1", "evidence_text": "x"}],
    )
    source_before = (source / "pack.json").read_text()

    output = run_trust_certify(str(source), output_pack_id="source_pack_certified", json_output=True)
    payload = json.loads(output)

    assert payload["status"] == "CERTIFICATION_PASSED"
    out_path = Path(payload["output_pack_path"])
    out_manifest = json.loads((out_path / "pack.json").read_text())
    assert out_manifest["lifecycle_status"] == "certified"
    assert json.loads((source / "pack.json").read_text()) == json.loads(source_before)


def test_trust_report_is_deterministic(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path / "packs" / "deterministic",
        pack_id="deterministic",
        claims=[
            _base_claim(claim_id="c2", subject="B", relation="is", object_="C"),
            _base_claim(claim_id="c1", subject="A", relation="is", object_="B"),
        ],
        provenance_rows=[{"source_id": "src-2"}, {"source_id": "src-1"}],
    )
    policy = TrustPolicy()
    first = certification_report_payload(CertificationGate.certify_pack(pack, policy))
    second = certification_report_payload(CertificationGate.certify_pack(pack, policy))
    assert first == second


def test_trusted_only_reasoning_loads_certified_packs_only(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "candidate",
        pack_id="candidate",
        lifecycle_status="candidate",
        claims=[_base_claim(claim_id="c1", subject="Socrates", relation="has_type", object_="human")],
        provenance_rows=[{"source_id": "src-a"}],
    )
    _write_pack(
        packs / "certified",
        pack_id="certified",
        lifecycle_status="certified",
        claims=[_base_claim(claim_id="c2", subject="human", relation="implies", object_="mortal")],
        provenance_rows=[{"source_id": "src-b"}],
    )
    payload = json.loads(run_reason(packs, json_output=True, trusted_only=True))
    assert payload["trusted_only"] is True
    assert len(payload["packs_loaded"]) == 1
    assert "certified" in payload["packs_loaded"][0]


def test_skipped_packs_are_reported(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "blocked",
        pack_id="blocked",
        lifecycle_status="blocked",
        claims=[_base_claim(claim_id="c1", subject="A", relation="r", object_="B")],
        provenance_rows=[{"source_id": "src"}],
    )
    payload = json.loads(run_reason(packs, json_output=True, trusted_only=True))
    assert len(payload["packs_skipped"]) == 1
    assert payload["packs_skipped"][0]["lifecycle_status"] == "blocked"


def test_default_reasoning_behavior_unchanged(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "candidate",
        pack_id="candidate",
        lifecycle_status="candidate",
        claims=[_base_claim(claim_id="c1", subject="Socrates", relation="has_type", object_="human")],
        provenance_rows=[{"source_id": "src-a"}],
    )
    _write_pack(
        packs / "certified",
        pack_id="certified",
        lifecycle_status="certified",
        claims=[_base_claim(claim_id="c2", subject="human", relation="implies", object_="mortal")],
        provenance_rows=[{"source_id": "src-b"}],
    )
    payload = json.loads(run_reason(packs, json_output=True, trusted_only=False))
    assert payload["trusted_only"] is False
    assert len(payload["packs_loaded"]) == 2
    assert payload["packs_skipped"] == []


def test_certification_handles_bad_encoding_as_structured_failure(tmp_path: Path) -> None:
    pack_dir = tmp_path / "packs" / "bad_encoding"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text(json.dumps({"id": "bad_encoding", "lifecycle_status": "candidate"}))
    (pack_dir / "claims.jsonl").write_bytes(b"\xff\xfe\xfd")
    (pack_dir / "provenance.jsonl").write_text("")

    result = CertificationGate.certify_pack(pack_dir, TrustPolicy())
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert any(issue.code == "CLAIMS_ENCODING_ERROR" for issue in result.issues)


def test_certification_handles_unreadable_json_as_structured_issue(tmp_path: Path) -> None:
    pack_dir = tmp_path / "packs" / "io_error_pack_json"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").mkdir()
    (pack_dir / "claims.jsonl").write_text("")
    (pack_dir / "provenance.jsonl").write_text("")

    result = CertificationGate.certify_pack(pack_dir, TrustPolicy())
    assert result.status in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert any(issue.code == "PACK_IO_ERROR" for issue in result.issues)
