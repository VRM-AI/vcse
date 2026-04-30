# Identity + Conflict Layer (v5.1.0)

VCSE v5.1.0 introduces deterministic entity canonicalization and conflict detection.

## Deterministic Identity

- `normalize_entity(text)` rules:
  - lowercase
  - trim surrounding whitespace
  - replace whitespace with `_`
  - remove punctuation (except `_`)
  - collapse repeated underscores
- Canonical ID format: `entity:<normalized>`
- Alias registry behavior is strict 1:1 (`normalized -> canonical_id`)
- No fuzzy matching and no heuristic merges

## Claim Key Normalization

Compiler-internal keys are normalized:

- `claim_key = "<normalized_subject>|<relation>|<normalized_object>"`

Original `subject` and `object` text remain preserved in `claims.jsonl`.

## Conflict Detection

Conflict grouping key:

- same normalized subject
- same relation

When two or more distinct normalized objects are present, VCSE reports conflicts.

No auto-resolution is performed.

## Reports

Compiler and pipeline reports now expose:

- `conflict_count`
- `duplicate_entity_count`
- `canonical_entity_count`

Compiler emits `conflicts.json` with a bounded `conflicts` sample.

## Runtime Store

`entity_dictionary` now includes:

- `normalized`
- `canonical_id`

New table:

- `entity_aliases(normalized PRIMARY KEY, canonical_id)`

Indexes:

- `idx_entity_normalized`
- `idx_entity_canonical`

## CLI

- `vcse entity normalize "United States"`
- `vcse conflict detect --pack <pack_id_or_path> --json`
