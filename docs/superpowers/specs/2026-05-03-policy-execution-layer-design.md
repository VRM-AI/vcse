# Policy Execution Layer — VCSE v6.6.0 Design Spec

**Date:** 2026-05-03
**Version target:** 6.6.0
**Base:** 6.5.2

---

## Purpose

Add a deterministic, inspectable Policy Execution Layer that sits after trust promotion. It can downgrade, block, flag, or annotate trust decisions — but never upgrade them. Trust invariants (NO PROOF ≠ T4/T5) remain unconditionally enforced by the existing layer.

---

## Pipeline Position

```
Verifier → TrustPromoter.evaluate_claim() → TrustDecision
                                               ↓
                                    PolicyExecutionEngine.execute()
                                               ↓
                                    PolicyExecutionResult
                                               ↓
                                    Final Output (with policy_execution key)
```

---

## Existing Policy Module (unchanged)

`src/vcse/policy/` contains:
- `model.py`: PolicyRule, PolicySet, PolicyDecision (relation-level allow/block)
- `enforcer.py`: PolicyEnforcer (evaluates relation/pack/domain/inference_rule)
- `loader.py`: JSON policy file loader
- `defaults.py`: DEFAULT_POLICY

These are not modified.

---

## New Additions

### `src/vcse/policy/actions.py`

```python
ALLOWED_ACTIONS = {"DOWNGRADE_TRUST", "BLOCK_PROMOTION", "REQUIRE_REVIEW", "FLAG_CONFLICT", "ANNOTATE_ONLY"}
FORBIDDEN_ACTIONS = {"PROMOTE_TO_T4", "PROMOTE_TO_T5", "OVERRIDE_VERIFIER"}
```

`ExecutionAction` dataclass: `action_id`, `action_type`, `parameters: dict`.

### `src/vcse/policy/rules.py`

`ExecutionRule` dataclass:
- `rule_id: str`
- `condition_field: str` — field on TrustDecision to test
- `condition_op: str` — eq | lt | gt | lte | gte | in | not_in
- `condition_value: Any`
- `action: str` — must be in ALLOWED_ACTIONS
- `action_params: dict`
- `priority: int` — lower fires first

`ExecutionProfile` dataclass: `profile_id`, `description`, `rules: tuple[ExecutionRule, ...]`

Condition evaluator: `evaluate_condition(decision, rule) -> bool` — pure function, no side effects.

### `src/vcse/policy/engine.py`

`PolicyExecutionEngine.execute(decision: TrustDecision, profile: ExecutionProfile) -> PolicyExecutionResult`

- Sort rules by priority (ascending)
- Evaluate each rule's condition against decision
- Collect fired rules and actions
- Apply DOWNGRADE_TRUST: only if target_tier < current recommended_tier
- Apply BLOCK_PROMOTION: sets blocked=True, tier stays at current_tier
- Apply REQUIRE_REVIEW: sets requires_review=True
- Apply FLAG_CONFLICT: appends to annotations
- Apply ANNOTATE_ONLY: appends to annotations
- Return PolicyExecutionResult

Idempotent: same inputs always produce same output.

### `src/vcse/policy/executor.py`

`PolicyExecutor(promoter: TrustPromoter, engine: PolicyExecutionEngine)`

`run(claim, profile, support_count, conflict_count) -> (TrustDecision, PolicyExecutionResult)`

Convenience wrapper combining both pipeline stages.

---

## PolicyExecutionResult Model

```python
@dataclass
class PolicyExecutionResult:
    applied_rules: list[str]   # rule_ids that fired
    actions_taken: list[str]   # action types applied
    final_tier: str            # post-execution tier (≤ input tier)
    annotations: list[str]     # ANNOTATE_ONLY / FLAG messages
    requires_review: bool
    blocked: bool
```

---

## Invariant Preservation

- `DOWNGRADE_TRUST` enforces `new_tier < input_tier` — never equal or higher
- No PROMOTE actions exist in the allowed action set
- T4/T5 gate in `promoter.py` is unchanged
- Engine is a pure read+transform over TrustDecision, no mutation of input

---

## CLI Extensions

```
vcse policy apply <pack_path> --profile <profile.json>
```
Runs TrustPromoter + PolicyExecutionEngine over pack claims. Output JSON includes `policy_execution` block.

```
vcse policy inspect <profile.json>
```
Dumps profile rules in tabular form: rule_id, priority, condition, action.

---

## Testing

`tests/test_policy_execution.py`:
1. Deterministic rule ordering (priority)
2. Priority enforcement (lower fires first)
3. DOWNGRADE_TRUST behavior
4. BLOCK_PROMOTION behavior
5. No promotion beyond T3→T4 boundary
6. Interaction with conflict flags
7. Idempotency (same input → same output)

---

## Acceptance Criteria

- `python -m pytest -q` — all pass
- `vcse gauntlet benchmarks/gauntlet/ --search mcts --ts3 --index` — PASSED, false_verified_count=0
- No regression in trust invariants
- Version: 6.6.0
