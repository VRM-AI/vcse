from __future__ import annotations

from collections.abc import Iterable

from vcse.cmcf import CMCFRecord
from vcse.trust.profile import TrustMatch, TrustProfile, TrustRule
from vcse.trust.profile_result import TrustAssessment, TrustDecision

_ACTION_STATUS = {
    "self_certify": "TRUST_SELF_CERTIFIED",
    "certify": "TRUST_CERTIFIED",
    "candidate": "TRUST_CANDIDATE",
    "review_required": "TRUST_REVIEW_REQUIRED",
    "block": "TRUST_BLOCKED",
    "downgrade": "TRUST_DOWNGRADED",
}

_PRIORITY = {
    "block": 1,
    "self_certify": 2,
    "certify": 2,
    "downgrade": 3,
    "review_required": 4,
    "candidate": 5,
}


class TrustProfileEngine:
    @staticmethod
    def evaluate_record(record: CMCFRecord, profile: TrustProfile) -> TrustDecision:
        matched_rules = [rule for rule in profile.rules if _matches(rule.match, record)]
        action = profile.default_action
        matched_rule: TrustRule | None = None

        if matched_rules:
            matched_rule = min(
                matched_rules,
                key=lambda rule: (_PRIORITY.get(rule.action, 999), rule.rule_id),
            )
            action = matched_rule.action

        trust_tier = max(0, int(record.trust.trust_tier))
        if matched_rule is not None and matched_rule.trust_tier is not None:
            trust_tier = matched_rule.trust_tier

        issues: list[str] = []
        reason = (
            f"Matched trust rule {matched_rule.rule_id}."
            if matched_rule is not None
            else f"No trust profile rule matched; default_action={profile.default_action}."
        )

        if action == "block":
            trust_tier = 0

        if action == "self_certify":
            action, trust_tier, gate_issues = _apply_self_certification_gates(
                record=record,
                profile=profile,
                matched_rule=matched_rule,
                trust_tier=trust_tier,
            )
            issues.extend(gate_issues)
            if gate_issues:
                reason = f"Self-certification gates failed ({'; '.join(gate_issues)})."

        return TrustDecision(
            status=_ACTION_STATUS[action],
            action=action,
            trust_profile_id=profile.trust_profile_id,
            matched_rule_id=matched_rule.rule_id if matched_rule is not None else None,
            subject=record.claim.subject,
            relation=record.claim.relation,
            object=record.claim.object,
            claim_id=record.claim.claim_id,
            source_uri=record.provenance.source_uri,
            trust_tier=trust_tier,
            reason=(matched_rule.reason or reason) if matched_rule is not None else reason,
            issues=tuple(issues),
        )

    @staticmethod
    def evaluate_records(records: Iterable[CMCFRecord], profile: TrustProfile) -> TrustAssessment:
        decisions = [TrustProfileEngine.evaluate_record(record, profile) for record in records]
        decisions = sorted(decisions, key=lambda item: ((item.claim_id or ""), (item.relation or ""), (item.subject or "")))
        return TrustAssessment(
            status="TRUST_ASSESSMENT_COMPLETE",
            trust_profile_id=profile.trust_profile_id,
            record_count=len(decisions),
            self_certified_count=sum(1 for d in decisions if d.action == "self_certify"),
            certified_count=sum(1 for d in decisions if d.action == "certify"),
            candidate_count=sum(1 for d in decisions if d.action == "candidate"),
            review_required_count=sum(1 for d in decisions if d.action == "review_required"),
            blocked_count=sum(1 for d in decisions if d.action == "block"),
            downgraded_count=sum(1 for d in decisions if d.action == "downgrade"),
            decisions=tuple(decisions),
        )


def _matches(match: TrustMatch, record: CMCFRecord) -> bool:
    if match.source_uri_prefix is not None:
        source_uri = record.provenance.source_uri or ""
        if not source_uri.startswith(match.source_uri_prefix):
            return False
    if match.source_type is not None and record.provenance.source_type != match.source_type:
        return False
    if match.domain is not None and record.metadata.domain != match.domain:
        return False
    if match.relation is not None and record.claim.relation != match.relation:
        return False
    if match.subject is not None and record.claim.subject != match.subject:
        return False
    if match.lifecycle_status is not None and record.status.lifecycle_status != match.lifecycle_status:
        return False
    if match.verification_status is not None and record.status.verification_status != match.verification_status:
        return False
    if match.provenance_status is not None and record.status.provenance_status != match.provenance_status:
        return False
    if match.certification_status is not None and record.status.certification_status != match.certification_status:
        return False
    if match.policy_status is not None and record.status.policy_status != match.policy_status:
        return False
    if match.field is not None:
        locator = record.provenance.locator or ""
        raw_value = record.provenance.raw_value or ""
        created_by = record.metadata.created_by or ""
        if match.field not in {locator, raw_value, created_by}:
            return False
    return True


def _apply_self_certification_gates(
    *,
    record: CMCFRecord,
    profile: TrustProfile,
    matched_rule: TrustRule | None,
    trust_tier: int,
) -> tuple[str, int, list[str]]:
    issues: list[str] = []
    policy = profile.self_certification
    if not policy.allowed:
        issues.append("self_certification_not_allowed")
    if matched_rule is None:
        issues.append("self_certification_requires_explicit_rule")
    if trust_tier > policy.max_trust_tier:
        issues.append("trust_tier_exceeds_max")
    if policy.requires_provenance and not (record.provenance.source_uri and record.provenance.source_type):
        issues.append("missing_required_provenance")
    if policy.requires_stable_source_hash and not record.provenance.content_hash:
        issues.append("missing_required_content_hash")
    if policy.requires_signature and not record.integrity.signature:
        issues.append("missing_required_signature")
    if policy.requires_policy_allowed and record.status.policy_status != "ALLOWED":
        issues.append("policy_status_not_allowed")
    if policy.requires_no_conflicts and "conflict" in (record.status.verification_status or "").lower():
        issues.append("conflict_marker_present")
    if (
        policy.requires_verification_status is not None
        and record.status.verification_status != policy.requires_verification_status
    ):
        issues.append("verification_status_mismatch")

    if issues:
        fallback_action = "review_required" if matched_rule is not None else "candidate"
        return fallback_action, 0, issues
    return "self_certify", trust_tier, issues


def derived_trust_min(*trust_tiers: int) -> int:
    if not trust_tiers:
        return 0
    return min(int(item) for item in trust_tiers)
