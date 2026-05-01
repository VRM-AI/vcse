"""Default policy configurations."""

from __future__ import annotations

from vcse.policy.model import PolicySet


DEFAULT_POLICY = PolicySet(
    policy_id="default_open_policy",
    description="Allows existing VCSE behavior unless explicit policy blocks are configured.",
    default_effect="allow",
    rules=(),
)
