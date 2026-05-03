# API Adapter

VCSE 1.9.0 exposes an OpenAI-compatible HTTP adapter for deterministic Correctness Model execution.

The adapter surfaces deterministic VCSE outcomes and supports multi-pack execution
paths consistent with v5.4 cross-pack reasoning and global consistency checks.

## Important

Compatibility is request/response shape compatibility, not LLM behavior.

VCSE still returns verifier-grounded states such as:

- `VERIFIED`
- `INCONCLUSIVE`
- `NEEDS_CLARIFICATION`
- `CONTRADICTORY`
- `UNSATISFIABLE`
- artifact statuses for generation

No probabilistic sampling is used.

## Structured Query CLI

VCSE v5.8.0 adds `vcse query` as a deterministic structured retrieval surface.

- Retrieval only: no mutation, no fuzzy matching, no embeddings, no LLM logic.
- Supports subject/relation/object filters, reverse lookup, pack scope,
  trusted-only pack filtering, and policy-filtered relation blocking.
- JSON output is stable for downstream UI/chatbot integrations.

## Explanation and Proof Rendering (v5.9.0)

`vcse query` and `vcse reason` now support opt-in explanation output.

- `--explain` is additive and does not change result selection.
- Explanation payloads render only existing result/provenance/proof data.
- Explanation rendering is deterministic and JSON-serializable.
- Zero-proof results are rendered explicitly as `UNVERIFIED`.

Examples:

```bash
vcse query --packs examples/packs --subject France --json --explain
vcse reason --packs examples/packs --json --explain
```

## CMCF and .csrf

- `CMCF` = `Correctness Model Canonical Format`
- `.csrf` = `Compiled Symbolic Runtime Format`

CMCF is the canonical deterministic record format for normalized claims.
`.csrf` is the deterministic compiled runtime format (v6.3.0) derived from CMCF and is not the canonical truth layer.

### Compiled Runtime Commands

- `vcse compile csrf <cmcf_file> --output <file.csrf> [--json]`
- `vcse query --csrf <file.csrf> --subject ... [--relation ...] [--json]`
- `vcse reason --csrf <file.csrf> [--trusted-only] [--policy <policy.json>] [--json]`
- `vcse runtime inspect <file.csrf> [--json]`

## Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`

## Supported Request Shape

```json
{
  "model": "vcse-vrm-1.9",
  "messages": [
    {"role": "user", "content": "All men are mortal. Socrates is a man. Can Socrates die?"}
  ],
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 256
}
```

`temperature`, `top_p`, and similar fields are accepted but ignored.

## Debug Mode

Use query param `?debug=true` to include `vcse_debug` in responses.

## Run Server

```bash
vcse serve
vcse serve --host 0.0.0.0 --port 8000
```

## curl Examples

```bash
curl http://localhost:8000/health

curl http://localhost:8000/v1/models

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"vcse-vrm-1.9","messages":[{"role":"user","content":"All men are mortal. Socrates is a man. Can Socrates die?"}]}'
```

## Python Example

```python
import requests

payload = {
    "model": "vcse-vrm-1.9",
    "messages": [{"role": "user", "content": "Is Socrates a man?"}],
}

r = requests.post("http://localhost:8000/v1/chat/completions", json=payload, timeout=30)
print(r.json())
```

## Universal Source Intake (v6.1.0)

`vcse ingest <source>` now supports deterministic CMCF-first intake for:

- local JSON / JSONL / CSV / HTML table
- local directories
- HTTP/HTTPS JSON / JSONL / CSV / HTML table

Pipeline:

`source -> fetch/resolve -> detect -> adapter -> rows -> profile -> CMCF -> validate -> candidate pack`

CLI flags:

- `--cmcf` enable new CMCF intake for local sources
- `--profile` force profile (`historical_events` or `generic_records`)
- `--limit` cap ingested rows before normalization
- `--dry-run` execute intake without writing a pack

Rules:

- URL sources always use universal intake.
- Local sources use legacy ingest unless `--cmcf` is provided.
- Output records are candidate-only with `UNVERIFIED` and `NOT_CERTIFIED` status.
- No auto-certification, no NLP/LLM logic, deterministic only.

## Configurable Trust Profiles (v6.2.0)

New CLI surface:

- `vcse trust profile inspect <profile_file> [--json]`
- `vcse trust profile apply <profile_file> --cmcf <file> [--json]`
- `vcse trust profile apply <profile_file> --pack <pack_id> [--json]` (clean unsupported status for non-CMCF-native packs)
- `vcse trust profile diff <old_profile> <new_profile> --cmcf <file> [--json]`

Model separation:

- `source_trust`: source eligibility policy
- `claim_trust`: per-claim decision
- `pack_trust`: aggregate assessment posture
- `derived_trust`: minimum supporting trust tier (`min` rule, no averaging)

Operational rules:

- Deterministic exact matching only
- No NLP/LLM/fuzzy/probabilistic logic
- No canonical CMCF mutation by default
- Self-certification requires explicit rule + gate success

## Proof Index (v6.4.0)

CLI commands:

- `vcse proof build --csrf <file.csrf> --output <file.proof.json> [--json]`
- `vcse proof why <claim_id> --proof-index <file.proof.json> [--json]`
- `vcse proof supports <claim_id> --proof-index <file.proof.json> [--json]`
- `vcse proof inspect <file.proof.json> [--json]`

Query / reason integration:

- `vcse query ... --proof-index <file.proof.json> --explain`
- `vcse reason ... --proof-index <file.proof.json> --explain`

When supplied, the proof index accelerates and augments explanation traces under
`proof_index_traces`. Result counts, inferred-claim counts, and reasoning output
remain identical to runs without the proof index.

Programmatic API (`vcse.proof`):

- `compile_proofs_from_csrf(csrf) -> ProofIndex`
- `compile_proofs_from_records(records) -> ProofIndex`
- `save_proof_index(index, path)` / `load_proof_index(path)`
- `select_best_proof(index, claim_id) -> ProofPath | None`
- `proof_path_to_explanation_trace(proof) -> dict`

Rules:

- Deterministic only; no fabricated proofs or VERIFIED zero-proof results.
- `.proof.json` is disposable — never committed unless an explicit fixture.

## Conflict Resolution Workflows (v6.5.0)

CLI commands:

- `vcse conflict workflow --pack <pack> [--proof-index <file>] [--json]`
- `vcse conflict workflow --packs <dir> [--proof-index <file>] [--json]`
- `vcse conflict impact <conflict_id> --report <workflow_report.json> [--json]`
- `vcse conflict export-report --pack <pack> [--proof-index <file>] --output <report.json>`

Programmatic API (`vcse.conflict`):

- `compute_conflict_id(subject, relation, object_a, object_b, claim_ids)`
- `derive_refs_from_claims(conflicts, claims) -> tuple[ConflictRef, ...]`
- `analyze_conflict_impact(refs, proof_index) -> tuple[ConflictImpact, ...]`
- `generate_resolution_options(ref, impact) -> tuple[ResolutionOption, ...]`
- `build_conflict_workflow_report(refs, proof_index) -> ConflictWorkflowReport`
- `conflict_workflow_report_to_dict(report) -> dict`

Resolution options always include `keep_a`, `keep_b`, `mark_disputed`, and
`require_review`; trust-tier comparisons appear as `recommended_by_trust`
annotations only. No option is ever auto-applied; `ConflictDetector` and CMCF/.csrf
data remain unchanged.
