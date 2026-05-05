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

## Signed Pack Distribution (v6.8.0)

CLI:

- `vcse pack bundle <pack_path> --output <dir> [--key <private_key>] [--json]`
- `vcse pack verify-bundle <bundle_path> [--key <public_key>] [--json]`
- `vcse pack inspect-bundle <bundle_path> [--json]`

Behavior rules:

- Signing proves bundle authenticity/integrity only.
- `SIGNATURE_VALID` never implies `VERIFIED`, trusted, or certified claims.
- Unsigned bundles can be integrity-valid candidates.
- Tampered bundles are detected via deterministic manifest hash checks.

## Runtime Hardening and Performance Benchmarking (v6.9.0)

### CLI Commands

```sh
vcse runtime validate <file.csrf> [--json]
vcse proof validate <file.proof.json> [--json]
vcse perf benchmark --csrf <file.csrf> [--proof-index <file.proof.json>] [--iterations N] [--json]
```

### Python API

```python
from vcse.runtime.validate import validate_csrf_index
from vcse.proof.validate import validate_proof_index
from vcse.runtime.hardening import load_csrf_checked, load_proof_index_checked
from vcse.runtime.atomic import atomic_write_text, atomic_write_bytes
from vcse.perf.benchmark import run_runtime_benchmark
from vcse.perf.report import benchmark_report_to_json
```

Validation results use `status: RUNTIME_VALID | RUNTIME_INVALID | RUNTIME_ERROR`.
Benchmark reports use `status: BENCHMARK_COMPLETE | BENCHMARK_FAILED`.
All machine values are UPPER_SNAKE_CASE. No NaN/Inf in any serialized output.

## Operational API Interface (v6.12.0)

VCSE exposes a local-first operational HTTP interface alongside the OpenAI-compat `/v1/*` adapter.

### Default binding

`vcse serve` binds to `127.0.0.1:8000` by default. Override with `--host` and `--port`.

### Response contract

All operational endpoints return:
```json
{
  "status": "OK",
  "version": "6.13.0",
  "request_id": "...",
  "data": {},
  "errors": []
}
```
- `status`: `"OK"` or `"ERROR"` (always UPPER_SNAKE_CASE)
- `errors[].code`: machine code, e.g. `API_NOT_FOUND`, `API_RUNTIME_INVALID`
- No raw tracebacks exposed in responses
- `X-Request-ID` header echoed if sent

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Service health |
| GET | `/version` | VCSE version + Python version |
| GET | `/ready` | Readiness probe |
| GET | `/live` | Liveness probe |
| POST | `/runtime/validate` | Validate `.csrf` artifact by path |
| POST | `/proof/validate` | Validate `.proof.json` index by path |
| POST | `/pack/verify-bundle` | Verify `.vcsepack` bundle integrity |
| POST | `/query` | Structured query over `.csrf` runtime |
| POST | `/reason` | Reason over `.csrf` runtime (functional in v6.11.0) |
| POST | `/support/evaluate` | Deterministic source support evaluation (v6.12.0) |
| POST | `/ontology/validate` | Validate ontology registry (v6.13.0) |

### POST /reason

Runs the reason service over a validated `.csrf` runtime artifact.

Request:
```json
{
  "csrf_path": "/path/to/runtime.csrf",
  "proof_index_path": null,
  "trusted_only": false,
  "explain": false,
  "max_results": null
}
```

Success response:
```json
{
  "status": "OK",
  "version": "6.13.0",
  "request_id": "...",
  "data": {
    "reason_status": "REASON_COMPLETE",
    "inferred_count": 0,
    "inferred_claims": [],
    "explanations": null
  },
  "errors": []
}
```

Error codes:
- `API_NOT_FOUND` — missing `csrf_path` or `proof_index_path` file
- `API_RUNTIME_INVALID` — `.csrf` artifact fails structural validation
- `API_PROOF_INVALID` — `.proof.json` index fails structural validation
- `API_INTERNAL_ERROR` — unexpected service failure

The `/reason` endpoint:
- uses validated `.csrf` runtime artifacts (via `load_csrf_checked`)
- validates proof index when `proof_index_path` is supplied
- does not alter verifier, trust, or signature semantics
- does not certify claims or auto-trust signatures
- does not infer beyond existing CLI reason behavior
- no longer returns `API_UNSUPPORTED_OPERATION` for valid requests

### POST /support/evaluate

Deterministic source-support evaluation over a candidate claim, cited source spans, and active relation views.

Request:
```json
{
  "claim": {
    "claim_id": "claim_timeout_001",
    "subject": "production deployments",
    "relation": "requires_timeout",
    "object": "500ms",
    "source_span_ids": ["span_001"]
  },
  "source_spans": [
    {"source_id": "src_policy_001", "source_span_id": "span_001",
     "text": "All production deployments must use a 500ms verifier timeout."}
  ],
  "active_relations": [
    {"relation_id": "requires_timeout", "support_profile_id": "SUPPORT_NORMALIZED"}
  ]
}
```

Success response:
```json
{
  "status": "OK", "version": "6.12.0", "request_id": "...",
  "data": {"support_status": "SOURCE_SUPPORTED", "supported": true, "reason_code": "SUPPORT_PROFILE_PASSED"},
  "errors": []
}
```

Support statuses: `SOURCE_SUPPORTED`, `SOURCE_SUPPORT_FAILED`, `NEEDS_SOURCE`, `UNKNOWN_SOURCE_SPAN`, `NEEDS_ONTOLOGY`, `INVALID_ONTOLOGY_RELATION`, `EXPLORATORY_SUPPORT_CANDIDATE`.

The `/support/evaluate` endpoint:
- never emits `VERIFIED` or `CERTIFIED`
- `GROUNDED` (span exists) does not imply `SOURCE_SUPPORTED`
- Proposal-Agent/LLM judgment cannot assign `SOURCE_SUPPORTED`
- embedding similarity cannot assign `SOURCE_SUPPORTED`
- unknown relations return `NEEDS_ONTOLOGY`
- missing `support_profile_id` returns `INVALID_ONTOLOGY_RELATION`

### POST /ontology/validate

Validates an ontology registry for structural correctness and lifecycle consistency.

Request:
```json
{
  "ontology_version": "2024-06-01",
  "relations": [
    {
      "relation_id": "requires_timeout",
      "label": "requires timeout",
      "support_profile_id": "SUPPORT_NORMALIZED",
      "activation_status": "ACTIVE",
      "ontology_version": "2024-06-01",
      "subject_types": ["Deployment"],
      "object_types": ["Timeout"],
      "functional": true,
      "allowed_support_profiles": ["SUPPORT_NORMALIZED", "SUPPORT_EXACT"]
    }
  ],
  "entity_types": [],
  "claim_types": []
}
```

Success response:
```json
{
  "status": "OK",
  "version": "6.13.0",
  "request_id": "...",
  "data": {
    "ontology_status": "ONTOLOGY_VALID",
    "issue_count": 0,
    "issues": []
  },
  "errors": []
}
```

Error response (invalid ontology):
```json
{
  "status": "OK",
  "version": "6.13.0",
  "request_id": "...",
  "data": {
    "ontology_status": "ONTOLOGY_INVALID",
    "issue_count": 2,
    "issues": [
      {"code": "ACTIVE_RELATION_MISSING_SUPPORT_PROFILE", "message": "ACTIVE relation requires support_profile_id", "path": "relation['requires_timeout'].support_profile_id"},
      {"code": "ONTOLOGY_VERSION_REQUIRED", "message": "ontology_version is required", "path": "ontology_version"}
    ]
  },
  "errors": []
}
```

Validation rules:
- `relation_id` is required for each relation
- `ontology_version` is required at root and per-relation
- `activation_status` must be UPPER_SNAKE_CASE and a known lifecycle state
- ACTIVE relations must have a valid `support_profile_id`
- ACTIVE relations must reference a known support profile

Lifecycle states (in order): PROPOSED → STRUCTURALLY_VALID → IMPACT_ANALYZED → CONFLICT_CHECKED → REGRESSION_TESTED → APPROVED → STAGED → ACTIVE

Only ACTIVE relations are authoritative for source-support evaluation.

The `/ontology/validate` endpoint:
- is read-only; does not persist or mutate any registry
- uses UPPER_SNAKE_CASE status codes in issues
- returns `ONTOLOGY_VALID` or `ONTOLOGY_INVALID` in data.ontology_status
- does not validate transitions between lifecycle states

### Invariants

The API never:
- auto-certifies or auto-trusts any data
- bypasses verifier or trust promotion logic
- exposes private keys or performs remote key lookup
- introduces probabilistic or LLM-based logic

Bundle signature validity is not truth. `BUNDLE_VALID` means structurally sound + signatures match; it does not certify claims.

---

## POST /proposal/validate

Validates a candidate proposal. External systems may submit candidate material only — VCSE owns canonicalization, verification, and trust promotion.

### Request body

```json
{
  "proposal_version": "1.0",
  "proposal_kind": "CANDIDATE_PROPOSAL",
  "candidate_kind": "FACTUAL_CLAIM_PACK",
  "claims": [
    {
      "claim_id": "claim-001",
      "claim_type": "FACTUAL",
      "status": "PROPOSED",
      "subject": "Paris",
      "predicate": "is_capital_of",
      "object": "France",
      "source_span_ids": ["span-001"]
    }
  ]
}
```

### Response — valid proposal

```json
{
  "status": "OK",
  "version": "6.14.0",
  "request_id": "...",
  "data": {
    "proposal_status": "PROPOSAL_VALID",
    "accepted": true,
    "claim_count": 1,
    "issues": []
  },
  "errors": []
}
```

### Response — invalid proposal

```json
{
  "status": "OK",
  "version": "6.14.0",
  "request_id": "...",
  "data": {
    "proposal_status": "PROPOSAL_INVALID",
    "accepted": false,
    "claim_count": 0,
    "issues": ["MISSING_PROPOSAL_VERSION"]
  },
  "errors": []
}
```

### Candidate Proposal Contract

- External callers may submit candidate material only.
- `CANDIDATE_ACCEPTED` does not mean VERIFIED, CERTIFIED, or SOURCE_SUPPORTED.
- Input claim `status` must be `PROPOSED`. Any other value is rejected.
- Forbidden authority fields (`verification_status`, `certification_status`, `trust_tier`, `authoritative_support_profile_id`) are **rejected**, not silently stripped.
- Unknown top-level or claim-level fields are rejected.
- Payload must be ≤ 1 MiB.
- VCSE owns all status transitions: canonicalization, source-support, verification, trust promotion, and certification.
- This endpoint has no side effects — it does not persist, verify, promote, or certify anything.

### Rejection reason codes (UPPER_SNAKE_CASE)

`MISSING_PROPOSAL_VERSION`, `MISSING_PROPOSAL_KIND`, `INVALID_PROPOSAL_KIND`, `MISSING_CANDIDATE_KIND`, `INVALID_CANDIDATE_KIND`, `MISSING_CLAIMS`, `INVALID_CLAIMS`, `MISSING_CLAIM_ID`, `MISSING_CLAIM_TYPE`, `MISSING_CLAIM_STATUS`, `INVALID_CLAIM_STATUS`, `MISSING_CLAIM_SUBJECT`, `MISSING_CLAIM_PREDICATE`, `MISSING_CLAIM_OBJECT`, `MISSING_SOURCE_SPAN_IDS`, `INVALID_SOURCE_SPAN_IDS`, `FORBIDDEN_VERIFICATION_STATUS`, `FORBIDDEN_CERTIFICATION_STATUS`, `FORBIDDEN_TRUST_TIER`, `FORBIDDEN_AUTHORITATIVE_SUPPORT_PROFILE`, `UNKNOWN_TOP_LEVEL_FIELD`, `UNKNOWN_CLAIM_FIELD`, `PAYLOAD_TOO_LARGE`, `STATUS_CASING_INVALID`, `NON_FINITE_VALUE`.
