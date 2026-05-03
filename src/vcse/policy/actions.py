"""Policy execution action definitions."""

from __future__ import annotations

ALLOWED_ACTIONS: frozenset[str] = frozenset({
    "DOWNGRADE_TRUST",
    "BLOCK_PROMOTION",
    "REQUIRE_REVIEW",
    "FLAG_CONFLICT",
    "ANNOTATE_ONLY",
})

FORBIDDEN_ACTIONS: frozenset[str] = frozenset({
    "PROMOTE_TO_T4",
    "PROMOTE_TO_T5",
    "OVERRIDE_VERIFIER",
})
