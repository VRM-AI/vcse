from __future__ import annotations

from vcse.trust.profile_result import TrustAssessment


def diff_trust_assessments(old: TrustAssessment, new: TrustAssessment) -> dict:
    old_map = {item.claim_id or "": item for item in old.decisions}
    new_map = {item.claim_id or "": item for item in new.decisions}
    claim_ids = sorted(set(old_map.keys()) | set(new_map.keys()))

    changed: list[dict[str, object]] = []
    newly_self_certified = 0
    newly_blocked = 0
    newly_review_required = 0
    trust_tier_changes = 0
    unchanged_count = 0

    for claim_id in claim_ids:
        old_item = old_map.get(claim_id)
        new_item = new_map.get(claim_id)
        if old_item is None or new_item is None:
            changed.append(
                {
                    "claim_id": claim_id,
                    "old_action": old_item.action if old_item is not None else None,
                    "new_action": new_item.action if new_item is not None else None,
                    "old_trust_tier": old_item.trust_tier if old_item is not None else None,
                    "new_trust_tier": new_item.trust_tier if new_item is not None else None,
                }
            )
            continue

        if old_item.action == new_item.action and old_item.trust_tier == new_item.trust_tier:
            unchanged_count += 1
            continue

        if old_item.action != "self_certify" and new_item.action == "self_certify":
            newly_self_certified += 1
        if old_item.action != "block" and new_item.action == "block":
            newly_blocked += 1
        if old_item.action != "review_required" and new_item.action == "review_required":
            newly_review_required += 1
        if old_item.trust_tier != new_item.trust_tier:
            trust_tier_changes += 1

        changed.append(
            {
                "claim_id": claim_id,
                "old_action": old_item.action,
                "new_action": new_item.action,
                "old_trust_tier": old_item.trust_tier,
                "new_trust_tier": new_item.trust_tier,
            }
        )

    return {
        "old_profile_id": old.trust_profile_id,
        "new_profile_id": new.trust_profile_id,
        "changed_count": len(changed),
        "newly_self_certified": newly_self_certified,
        "newly_blocked": newly_blocked,
        "newly_review_required": newly_review_required,
        "trust_tier_changes": trust_tier_changes,
        "unchanged_count": unchanged_count,
        "changes": changed,
    }
