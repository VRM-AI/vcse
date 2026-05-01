from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from vcse.cli import run_reason, run_trust_certify
from vcse.policy import DEFAULT_POLICY, PolicyEnforcer, PolicyLoadError, load_policy


def _write_pack(
    pack_dir: Path,
    *,
    pack_id: str,
    lifecycle_status: str = "candidate",
    claims: list[dict] | None = None,
) -> None:
    claims = claims or []
    pack_dir.mkdir(parents=True, exist_ok=True)
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
    (pack_dir / "claims.jsonl").write_text("\n".join(json.dumps(c, sort_keys=True) for c in claims) + ("\n" if claims else ""))
    (pack_dir / "provenance.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "source_type": "pack",
                    "source_id": str(c.get("source_id", "src")),
                    "location": "claims.jsonl",
                    "evidence_text": "evidence",
                },
                sort_keys=True,
            )
            for c in claims
        )
        + ("\n" if claims else "")
    )


def _claim(*, subject: str, relation: str, object_: str, claim_id: str = "c1") -> dict:
    return {
        "claim_id": claim_id,
        "subject": subject,
        "relation": relation,
        "object": object_,
        "source_id": "src1",
        "trust_tier": 1,
        "provenance": {
            "source_type": "pack",
            "source_id": "src1",
            "location": "claims.jsonl",
            "evidence_text": "evidence",
        },
    }


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "vcse.cli", *args], capture_output=True, text=True, env=env)


def test_default_open_policy_allows_unknown_relation() -> None:
    decision = PolicyEnforcer().evaluate_relation("unknown_relation", DEFAULT_POLICY)
    assert decision.status == "ALLOWED"


def test_restrictive_policy_blocks_unknown_relation() -> None:
    policy = load_policy(Path("examples/policies/geography_safe_policy.json"))
    decision = PolicyEnforcer().evaluate_relation("unknown_relation", policy)
    assert decision.status == "BLOCKED"


def test_explicit_allow_works() -> None:
    policy = load_policy(Path("examples/policies/geography_safe_policy.json"))
    decision = PolicyEnforcer().evaluate_relation("has_capital", policy)
    assert decision.status == "ALLOWED"


def test_explicit_block_overrides_allow(tmp_path: Path) -> None:
    policy_file = tmp_path / "override_policy.json"
    policy_file.write_text(
        json.dumps(
            {
                "policy_id": "override_policy",
                "description": "block wins",
                "default_effect": "allow",
                "rules": [
                    {
                        "rule_id": "allow_x",
                        "effect": "allow",
                        "target_type": "relation",
                        "target": "has_capital",
                        "reason": "allow",
                    },
                    {
                        "rule_id": "block_x",
                        "effect": "block",
                        "target_type": "relation",
                        "target": "has_capital",
                        "reason": "block",
                    },
                ],
            }
        )
    )
    policy = load_policy(policy_file)
    decision = PolicyEnforcer().evaluate_relation("has_capital", policy)
    assert decision.status == "BLOCKED"
    assert decision.matched_rule_id == "block_x"


def test_malformed_policy_fails_clearly(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"policy_id":"x","default_effect":"allow","rules":[]}')
    with pytest.raises(PolicyLoadError, match="missing required field: description"):
        load_policy(bad)


def test_policy_inspect_cli_works() -> None:
    result = _run_cli("policy", "inspect", "examples/policies/geography_safe_policy.json", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["policy_id"] == "geography_safe_policy"
    assert payload["rule_count"] == 2


def test_policy_evaluate_cli_works() -> None:
    result = _run_cli(
        "policy",
        "evaluate",
        "--policy",
        "examples/policies/geography_safe_policy.json",
        "--relation",
        "unsupported_relation",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "BLOCKED"


def test_certification_blocks_disallowed_relation(tmp_path: Path) -> None:
    packs_root = tmp_path / "packs"
    pack = packs_root / "candidate_pack"
    _write_pack(pack, pack_id="candidate_pack", claims=[_claim(subject="Socrates", relation="forbidden", object_="x")])

    policy_file = tmp_path / "restrictive.json"
    policy_file.write_text(
        json.dumps(
            {
                "policy_id": "restrictive",
                "description": "only has_capital",
                "default_effect": "block",
                "rules": [
                    {
                        "rule_id": "allow_has_capital",
                        "effect": "allow",
                        "target_type": "relation",
                        "target": "has_capital",
                        "reason": "allowed",
                    }
                ],
            }
        )
    )

    payload = json.loads(run_trust_certify(str(pack), policy_file=policy_file, json_output=True))
    assert payload["status"] in {"CERTIFICATION_BLOCKED", "CERTIFICATION_FAILED"}
    assert any(issue["code"] == "POLICY_BLOCKED_RELATION" for issue in payload["issues"])


def test_reasoning_with_policy_excludes_blocked_claims_and_reports_them(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        pack_id="p1",
        claims=[
            _claim(subject="Socrates", relation="has_type", object_="human", claim_id="a1"),
            _claim(subject="human", relation="implies", object_="mortal", claim_id="a2"),
        ],
    )
    policy_file = tmp_path / "restrictive.json"
    policy_file.write_text(
        json.dumps(
            {
                "policy_id": "restrictive",
                "description": "allow has_type only",
                "default_effect": "block",
                "rules": [
                    {
                        "rule_id": "allow_has_type",
                        "effect": "allow",
                        "target_type": "relation",
                        "target": "has_type",
                        "reason": "allowed",
                    }
                ],
            }
        )
    )

    payload = json.loads(run_reason(packs, json_output=True, policy_file=policy_file))
    assert payload["blocked_claim_count"] == 1
    assert any(item["status"] == "BLOCKED" for item in payload["policy_decisions"])


def test_default_reasoning_unchanged_without_policy(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    _write_pack(
        packs / "p1",
        pack_id="p1",
        claims=[
            _claim(subject="Socrates", relation="has_type", object_="human", claim_id="a1"),
            _claim(subject="human", relation="implies", object_="mortal", claim_id="a2"),
        ],
    )
    payload = json.loads(run_reason(packs, json_output=True))
    assert payload["blocked_claim_count"] == 0
    assert payload["policy_id"] == "default_open_policy"
    assert len(payload["inferred_claims"]) == 1
