# Policy Enforcement Layer (v5.6)

VCSE v5.6 adds a deterministic policy enforcement layer that constrains what
relations, packs, domains, and inference rules are allowed at runtime.

Core split:
- trust decides eligibility
- policy decides allowed use

## Components

- `PolicyRule`: deterministic allow/block rule
- `PolicySet`: named collection of rules plus `default_effect`
- `PolicyDecision`: explicit allow/block decision with reason
- `PolicyEnforcer`: evaluator for relation/pack/domain/inference rule/claim

## Defaults

`default_open_policy` preserves backward compatibility:
- `default_effect: allow`
- no rules

## Policy Files

Examples:
- `examples/policies/default_open_policy.json`
- `examples/policies/geography_safe_policy.json`

## CLI

Inspect a policy:

```bash
vcse policy inspect examples/policies/geography_safe_policy.json --json
```

Evaluate a relation:

```bash
vcse policy evaluate --policy examples/policies/geography_safe_policy.json --relation has_capital --json
```

Apply policy during trust certification:

```bash
vcse trust certify <pack_id> --policy-file examples/policies/geography_safe_policy.json --json
```

Apply policy during cross-pack reasoning:

```bash
vcse reason --packs examples/packs --policy examples/policies/geography_safe_policy.json --json
```

## Deterministic Rules

- block overrides allow
- allow applies when no matching block
- `default_effect` applies when no rule matches
- decisions are explicit and returned in outputs
- no silent policy bypass
