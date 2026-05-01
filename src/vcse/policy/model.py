"""Deterministic policy data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    effect: str  # allow | block
    target_type: str  # relation | pack | domain | inference_rule
    target: str
    reason: str


@dataclass(frozen=True)
class PolicySet:
    policy_id: str
    description: str
    default_effect: str  # allow | block
    rules: tuple[PolicyRule, ...]


@dataclass(frozen=True)
class PolicyDecision:
    status: str  # ALLOWED | BLOCKED
    policy_id: str
    target_type: str
    target: str
    matched_rule_id: str | None
    reason: str
