import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vcse.cmcf.model import CMCFClaim, CMCFIntegrity, CMCFMetadata, CMCFProvenance, CMCFRecord, CMCFStatus, CMCFTrust
from vcse.cmcf.serialize import record_to_dict
from vcse.trust.profile_diff import diff_trust_assessments
from vcse.trust.profile_engine import TrustProfileEngine, derived_trust_min
from vcse.trust.profile_loader import load_trust_profile


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, text=True, env=env)


def _record(
    *,
    claim_id: str = "c1",
    subject: str = "s",
    relation: str = "r",
    object_value: str = "o",
    source_uri: str | None = "https://www.noaa.gov/obs/1",
    source_type: str = "url",
    content_hash: str | None = "hash1",
    signature: str | None = None,
    verification_status: str = "UNVERIFIED",
    policy_status: str = "ALLOWED",
) -> CMCFRecord:
    return CMCFRecord(
        cmcf_version="1.0",
        claim=CMCFClaim(claim_id=claim_id, subject=subject, relation=relation, object=object_value),
        provenance=CMCFProvenance(
            provenance_id=f"p_{claim_id}",
            source_type=source_type,
            source_uri=source_uri,
            retrieved_at="2026-01-01T00:00:00Z",
            content_hash=content_hash,
            locator=f"claims.{relation}",
            raw_value=object_value,
            method="deterministic",
        ),
        status=CMCFStatus(
            lifecycle_status="candidate",
            verification_status=verification_status,
            certification_status="NOT_CERTIFIED",
            provenance_status="PROVENANCED",
            policy_status=policy_status,
        ),
        trust=CMCFTrust(trust_tier=0, trust_policy="default"),
        integrity=CMCFIntegrity(content_hash="integrity_hash", signature=signature),
        metadata=CMCFMetadata(domain="events", language="en", created_by="test"),
    )


def test_load_valid_trust_profile() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json")
    assert profile.trust_profile_id == "default_candidate_profile"
    assert profile.default_action == "candidate"


def test_reject_unknown_action(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "trust_profile_id": "x",
                "description": "x",
                "default_action": "candidate",
                "self_certification": {"allowed": False, "max_trust_tier": 0},
                "rules": [{"rule_id": "r1", "action": "magic", "match": {}}],
            }
        )
    )
    with pytest.raises(ValueError, match="TRUST_PROFILE_UNKNOWN_ACTION"):
        load_trust_profile(bad)


def test_reject_duplicate_rule_id(tmp_path: Path) -> None:
    bad = tmp_path / "dup.json"
    bad.write_text(
        json.dumps(
            {
                "trust_profile_id": "x",
                "description": "x",
                "default_action": "candidate",
                "self_certification": {"allowed": False, "max_trust_tier": 0},
                "rules": [
                    {"rule_id": "r1", "action": "candidate", "match": {}},
                    {"rule_id": "r1", "action": "block", "match": {}},
                ],
            }
        )
    )
    with pytest.raises(ValueError, match="TRUST_PROFILE_DUPLICATE_RULE_ID"):
        load_trust_profile(bad)


def test_default_candidate_action_applies_when_no_rule_matches() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json")
    decision = TrustProfileEngine.evaluate_record(_record(), profile)
    assert decision.action == "candidate"


def test_block_rule_overrides_allow_self_certify(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "trust_profile_id": "p",
                "description": "p",
                "default_action": "candidate",
                "self_certification": {"allowed": True, "max_trust_tier": 4},
                "rules": [
                    {"rule_id": "allow", "action": "self_certify", "match": {"relation": "r"}, "trust_tier": 4},
                    {"rule_id": "block", "action": "block", "match": {"relation": "r"}},
                ],
            }
        )
    )
    profile = load_trust_profile(profile_path)
    decision = TrustProfileEngine.evaluate_record(_record(relation="r"), profile)
    assert decision.action == "block"


def test_relation_rule_matches_exactly() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "historical_events_candidate_profile.json")
    matched = TrustProfileEngine.evaluate_record(_record(relation="occurred_on"), profile)
    not_matched = TrustProfileEngine.evaluate_record(_record(relation="occurred_on_exactly"), profile)
    assert matched.action == "review_required"
    assert not_matched.action == "candidate"


def test_source_uri_prefix_rule_matches_deterministically() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "government_open_data_profile.json")
    allow = TrustProfileEngine.evaluate_record(_record(source_uri="https://www.noaa.gov/abc"), profile)
    miss = TrustProfileEngine.evaluate_record(_record(source_uri="https://example.org/noaa"), profile)
    assert allow.action == "self_certify"
    assert miss.action == "candidate"


def test_self_certification_succeeds_only_when_all_gates_pass() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "government_open_data_profile.json")
    decision = TrustProfileEngine.evaluate_record(_record(), profile)
    assert decision.action == "self_certify"
    assert decision.trust_tier == 4


def test_self_certification_downgrades_when_provenance_missing() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "government_open_data_profile.json")
    decision = TrustProfileEngine.evaluate_record(_record(source_type=""), profile)
    assert decision.action == "review_required"
    assert "missing_required_provenance" in decision.issues


def test_self_certification_downgrades_when_content_hash_missing() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "government_open_data_profile.json")
    decision = TrustProfileEngine.evaluate_record(_record(content_hash=None), profile)
    assert decision.action == "review_required"
    assert "missing_required_content_hash" in decision.issues


def test_field_relation_specific_rule_can_keep_description_candidate() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "historical_events_candidate_profile.json")
    decision = TrustProfileEngine.evaluate_record(_record(relation="has_description"), profile)
    assert decision.action == "candidate"


def test_apply_cli_works_on_cmcf_jsonl(tmp_path: Path) -> None:
    cmcf = tmp_path / "records.cmcf.jsonl"
    cmcf.write_text(json.dumps(record_to_dict(_record(claim_id="c1"))) + "\n")
    result = run_cli(
        "trust",
        "profile",
        "apply",
        str(ROOT / "examples" / "trust_profiles" / "historical_events_candidate_profile.json"),
        "--cmcf",
        str(cmcf),
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "TRUST_ASSESSMENT_COMPLETE"
    assert payload["record_count"] == 1


def test_inspect_cli_works() -> None:
    result = run_cli(
        "trust",
        "profile",
        "inspect",
        str(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json"),
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["trust_profile_id"] == "default_candidate_profile"


def test_diff_cli_reports_changed_decisions(tmp_path: Path) -> None:
    cmcf = tmp_path / "records.cmcf.jsonl"
    cmcf.write_text(json.dumps(record_to_dict(_record(claim_id="c1", relation="occurred_on"))) + "\n")
    result = run_cli(
        "trust",
        "profile",
        "diff",
        str(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json"),
        str(ROOT / "examples" / "trust_profiles" / "historical_events_candidate_profile.json"),
        "--cmcf",
        str(cmcf),
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["changed_count"] >= 1


def test_no_cmcf_input_mutation(tmp_path: Path) -> None:
    cmcf = tmp_path / "records.cmcf.jsonl"
    original = json.dumps(record_to_dict(_record(claim_id="c1"))) + "\n"
    cmcf.write_text(original)
    run_cli(
        "trust",
        "profile",
        "apply",
        str(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json"),
        "--cmcf",
        str(cmcf),
    )
    assert cmcf.read_text() == original


def test_assessment_output_ordering_deterministic() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json")
    records = [_record(claim_id="c2"), _record(claim_id="c1")]
    assessment = TrustProfileEngine.evaluate_records(records, profile)
    assert [item.claim_id for item in assessment.decisions] == ["c1", "c2"]


def test_pack_evaluation_unsupported_path_reports_cleanly() -> None:
    result = run_cli(
        "trust",
        "profile",
        "apply",
        str(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json"),
        "--pack",
        "examples/packs/trusted_basic",
    )
    assert result.returncode == 2
    assert "TRUST_PROFILE_PACK_UNSUPPORTED" in result.stderr


def test_derived_trust_min_rule_helper() -> None:
    assert derived_trust_min(4, 2, 3) == 2


def test_diff_function_deterministic_by_claim_id() -> None:
    profile = load_trust_profile(ROOT / "examples" / "trust_profiles" / "default_candidate_profile.json")
    profile2 = load_trust_profile(ROOT / "examples" / "trust_profiles" / "historical_events_candidate_profile.json")
    records = [_record(claim_id="b", relation="occurred_on"), _record(claim_id="a", relation="occurred_on")]
    old = TrustProfileEngine.evaluate_records(records, profile)
    new = TrustProfileEngine.evaluate_records(records, profile2)
    diff = diff_trust_assessments(old, new)
    claim_ids = [item["claim_id"] for item in diff["changes"]]
    assert claim_ids == sorted(claim_ids)
