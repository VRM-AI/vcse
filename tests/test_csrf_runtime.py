from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from vcse.cmcf import CMCFRecord, claim_dict_to_cmcf, record_to_dict
from vcse.pipeline.runner import cross_pack_reason
from vcse.query import StructuredQuery, StructuredQueryEngine
from vcse.runtime import compile_cmcf_to_csrf, load_runtime, save_csrf
from vcse.runtime.serialize import load_csrf


def _mk_record(subject: str, relation: str, obj: str, *, source: str, trust_tier: int = 3) -> CMCFRecord:
    record = claim_dict_to_cmcf(
        {"subject": subject, "relation": relation, "object": obj},
        source_type="manual",
        source_uri=f"file://{source}",
        locator="row:1",
        raw_value=json.dumps({"subject": subject, "relation": relation, "object": obj}),
    )
    payload = record_to_dict(record)
    payload["trust"]["trust_tier"] = trust_tier
    payload["status"]["lifecycle_status"] = "certified" if trust_tier >= 4 else "candidate"
    payload["status"]["verification_status"] = "VERIFIED"
    from vcse.cmcf.hash import compute_content_hash

    payload["integrity"]["content_hash"] = compute_content_hash(
        {
            "cmcf_version": payload["cmcf_version"],
            "claim": payload["claim"],
            "provenance": payload["provenance"],
            "status": payload["status"],
            "trust": payload["trust"],
            "metadata": payload["metadata"],
        }
    )
    from vcse.cmcf import record_from_dict

    return record_from_dict(payload)


def _records() -> list[CMCFRecord]:
    return [
        _mk_record("Socrates", "has_type", "human", source="a", trust_tier=5),
        _mk_record("human", "implies", "mortal", source="b", trust_tier=2),
        _mk_record("France", "has_capital", "Paris", source="c", trust_tier=4),
    ]


def test_identical_cmcf_to_identical_csrf() -> None:
    first = compile_cmcf_to_csrf(_records())
    second = compile_cmcf_to_csrf(list(reversed(_records())))
    assert first == second


def test_modified_claim_changes_csrf() -> None:
    left = compile_cmcf_to_csrf(_records())
    modified = _records()
    modified[0] = _mk_record("Socrates", "has_type", "person", source="a", trust_tier=5)
    right = compile_cmcf_to_csrf(modified)
    assert left != right


def test_deterministic_ordering_by_claim_id() -> None:
    index = compile_cmcf_to_csrf(_records())
    claim_ids = [item.claim_id for item in index.records]
    assert claim_ids == sorted(claim_ids)


def test_subject_relation_object_indexes() -> None:
    index = compile_cmcf_to_csrf(_records())
    subject_rows = tuple(index.records[i].subject for i in index.by_subject["Socrates"])
    relation_rows = tuple(index.records[i].relation for i in index.by_relation["has_type"])
    object_rows = tuple(index.records[i].object for i in index.by_object["mortal"])
    assert subject_rows == ("Socrates",)
    assert relation_rows == ("has_type",)
    assert object_rows == ("mortal",)


def test_query_results_identical_with_csrf_runtime(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    packs.mkdir()
    pack = packs / "alpha"
    pack.mkdir()
    (pack / "pack.json").write_text(json.dumps({"id": "alpha", "lifecycle_status": "certified"}))
    (pack / "claims.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"claim_id": "a1", "subject": "France", "relation": "has_capital", "object": "Paris", "trust_tier": 4}),
                json.dumps({"claim_id": "a2", "subject": "France", "relation": "uses_currency", "object": "Euro", "trust_tier": 4}),
            ]
        )
        + "\n"
    )

    cmcf_records = [_mk_record("France", "has_capital", "Paris", source="q1", trust_tier=4), _mk_record("France", "uses_currency", "Euro", source="q2", trust_tier=4)]
    csrf_index = compile_cmcf_to_csrf(cmcf_records)

    query = StructuredQuery(subject="France")
    pack_result = StructuredQueryEngine().query_packs(packs, query)
    csrf_result = StructuredQueryEngine().query_csrf(csrf_index, query)

    pack_triples = {(item["subject"], item["relation"], item["object"]) for item in pack_result.results}
    csrf_triples = {(item["subject"], item["relation"], item["object"]) for item in csrf_result.results}
    assert pack_triples == csrf_triples


def test_reasoning_and_proofs_identical() -> None:
    cmcf = _records()
    csrf = compile_cmcf_to_csrf(cmcf)

    cmcf_claims = [
        {
            "subject": item.claim.subject,
            "relation": item.claim.relation,
            "object": item.claim.object,
            "pack_id": "cmcf",
            "claim_id": item.claim.claim_id,
            "trust_tier": item.trust.trust_tier,
            "provenance": {"provenance_id": item.provenance.provenance_id},
        }
        for item in cmcf
    ]
    csrf_claims = [
        {
            "subject": item.subject,
            "relation": item.relation,
            "object": item.object,
            "pack_id": "cmcf",
            "claim_id": item.claim_id,
            "trust_tier": item.trust_tier,
            "provenance": {"provenance_id": item.provenance_id},
        }
        for item in csrf.records
    ]

    left = cross_pack_reason(cmcf_claims)
    right = cross_pack_reason(csrf_claims)
    assert left == right


def test_trust_preserved_and_roundtrip(tmp_path: Path) -> None:
    index = compile_cmcf_to_csrf(_records())
    out = tmp_path / "runtime.csrf"
    save_csrf(index, out)
    reloaded = load_csrf(out)
    assert reloaded == index
    assert [r.trust_tier for r in reloaded.records] == [r.trust_tier for r in index.records]


def test_nan_inf_disallowed(tmp_path: Path) -> None:
    path = tmp_path / "bad.csrf"
    path.write_text('{"records":[{"claim_id":"x","subject":"a","relation":"b","object":"c","trust_tier":NaN,"lifecycle_status":"candidate","verification_status":"UNKNOWN","provenance_id":"p"}],"by_subject":{},"by_relation":{},"by_object":{}}')
    with pytest.raises(ValueError):
        load_csrf(path)


def test_runtime_loader_cmcf_and_csrf(tmp_path: Path) -> None:
    rows = [record_to_dict(item) for item in _records()]
    cmcf_file = tmp_path / "records.json"
    cmcf_file.write_text(json.dumps(rows))
    csrf_file = tmp_path / "records.csrf"
    save_csrf(compile_cmcf_to_csrf(_records()), csrf_file)

    from_cmcf = load_runtime(str(cmcf_file))
    from_csrf = load_runtime(str(csrf_file))
    assert from_cmcf == from_csrf


def test_csrf_query_path_is_faster_than_linear_scan() -> None:
    records = [_mk_record(f"s{i}", "has", "value", source=f"src-{i}", trust_tier=3) for i in range(1200)]
    index = compile_cmcf_to_csrf(records)
    query = StructuredQuery(relation="has")

    rows_examined = 0
    t0 = time.perf_counter()
    for _ in range(20):
        for item in records:
            rows_examined += 1
            row = record_to_dict(item)
            if row["claim"]["relation"] != "has":
                continue
    linear_elapsed = time.perf_counter() - t0

    t1 = time.perf_counter()
    csrf_result = None
    for _ in range(20):
        csrf_result = StructuredQueryEngine().query_csrf(index, query)
    csrf_elapsed = time.perf_counter() - t1

    assert rows_examined == 24000
    assert csrf_result is not None
    assert csrf_result.result_count == len(records)
    assert csrf_elapsed < linear_elapsed
