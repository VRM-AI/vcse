# VCSE Roadmap

## Naming Standards

- `CMCF` = `Correctness Model Canonical Format`
- `.csrf` = `Compiled Symbolic Runtime Format`

Rules:

- CMCF is canonical, human-readable, hashable source-of-truth structure.
- `.csrf` is a derived runtime artifact compiled from CMCF.
- JSONL/CMCF remains canonical truth; `.csrf` is never primary truth.

## Completed

- v5.0 — pack system
- v5.1 — identity + conflict detection
- v5.2 — ingest system
- v5.3 — schema inference / mapping proposal
- v5.4 — cross-pack reasoning
- v5.5 — trust certification
- v5.6 — policy enforcement
- v5.7 — incremental ingest
- v5.8 — structured query
- v5.8.x — edge-case hardening
- v5.9 — explanation + proof rendering

## v6.1 Delivered

- Universal source intake with deterministic adapters (JSON/JSONL/CSV/HTML table)
- URL fetch + cache layer with bounded timeout/size
- Profile-based CMCF normalization (`historical_events`, `generic_records`)
- `vcse ingest` integration with `--cmcf`, `--profile`, `--limit`, `--dry-run`
- Candidate-only output policy enforcement (`UNVERIFIED`, `NOT_CERTIFIED`)

## v6.2 Delivered

- Configurable trust profiles with deterministic rule matching
- Retroactive trust assessment for CMCF JSON/JSONL inputs
- Trust decision diffing between profile versions
- Explicit self-certification gates with downgrade-on-failure behavior
- No default mutation of canonical CMCF records

## v6.3 Delivered

- Added deterministic compiled runtime layer (`CMCF -> .csrf`)
- Added indexed runtime model (`by_subject`, `by_relation`, `by_object`)
- Added CLI support:
  - `vcse compile csrf`
  - `vcse query --csrf`
  - `vcse reason --csrf`
  - `vcse runtime inspect`
- Added CSRF runtime tests for determinism, equivalence, and serialization

## v6.4 Delivered

- Proof index data models (`ProofStep`, `ProofPath`, `ProofIndex`)
- Deterministic proof compiler (`compile_proofs_from_csrf`, `compile_proofs_from_records`)
- Reverse dependency graph (`by_support`)
- Proof index serialization (`.proof.json`) and loader
- Proof-aware explanation acceleration (`select_best_proof`, `proof_path_to_explanation_trace`)
- CLI:
  - `vcse proof build`
  - `vcse proof why`
  - `vcse proof supports`
  - `vcse proof inspect`
  - `vcse query --proof-index`
  - `vcse reason --proof-index`
- Proof index never creates new truth; CMCF remains canonical, `.proof.json` is disposable

## v6.5 Delivered

- Conflict workflow data models (`ConflictRef`, `ConflictImpact`, `ResolutionOption`, `ConflictWorkflowReport`)
- Deterministic conflict identity (`compute_conflict_id`)
- Impact analysis using proof reverse dependencies (`analyze_conflict_impact`)
- Resolution option generation (`keep_a`, `keep_b`, `mark_disputed`, `require_review`)
- Trust-aware option annotation (recommendation only, never auto-applied)
- Workflow report builder + serializer
- CLI:
  - `vcse conflict workflow --pack` / `--packs`
  - `vcse conflict impact <id> --report`
  - `vcse conflict export-report`
- No automatic conflict resolution; maintainer-controlled review

## v6.8 Delivered

- Signed pack bundle lifecycle (`.vcsepack`) with deterministic manifests
- Bundle signing with Ed25519 using existing integrity primitives
- Bundle verification for manifest integrity + optional signature verification
- Bundle inspection command surface for pre-ingest decisioning
- Explicit separation: signature validity does not imply trust/certification

## v6.9.0 — Runtime Hardening + Performance Benchmark Infrastructure

- Runtime validation checks .csrf structural integrity (index ranges, casing, trust_tier, NaN/Inf)
- Proof index validation checks consistency (path_length, support index, VERIFIED invariants)
- Checked loaders (`load_csrf_checked`, `load_proof_index_checked`) raise structured errors on invalid artifacts
- Atomic write helpers prevent partial artifacts on interrupted writes
- Performance benchmark harness measures LOAD_CSRF, QUERY_SUBJECT/RELATION/OBJECT, PROOF_LOOKUP
- Benchmark is measurement-only — no hard timing thresholds in v6.9
- All validation failures are explicit and structured (UPPER_SNAKE_CASE codes)
- No correctness shortcuts introduced; verifier/trust invariants unchanged

## v6.10.0 — API/Server Hardening + Operational Interface

- Operational HTTP API surface alongside OpenAI-compat adapter
- Health/readiness/liveness probes (GET /health, /ready, /live)
- Unified VcseResponse contract (status, version, request_id, data, errors)
- Error responses use UPPER_SNAKE_CASE codes, no raw tracebacks
- Validation endpoints: POST /runtime/validate, /proof/validate, /pack/verify-bundle
- Query endpoint: POST /query for structured deterministic queries over .csrf
- X-Request-ID header echo support for request tracing
- /reason endpoint deferred to v6.11
- All endpoints deterministic, non-mutating, never auto-certifying

## v6.11.0 — Reason Service Extraction + API /reason Enablement

- Extracted reusable reason service (`vcse.reasoning.service`) from CLI `run_reason`
- Service accepts `ReasonServiceRequest`, returns `ReasonServiceResult` (frozen dataclasses)
- Service validates `.csrf` via `load_csrf_checked` before reasoning
- Service validates proof index via `load_proof_index_checked` when `proof_index_path` supplied
- API `/reason` endpoint functional; uses validated `.csrf` runtime artifacts
- API `/reason` no longer returns `API_UNSUPPORTED_OPERATION` for valid requests
- Reason service statuses: `REASON_COMPLETE`, `REASON_FAILED`, `REASON_RUNTIME_INVALID`, `REASON_PROOF_INVALID`
- CLI reason behavior preserved unchanged; parity verified
- No changes to verifier, trust, signature, proof index, or CMCF semantics
- false_verified_count remains 0

## v6.12.0 — Evidence Span + Deterministic Source Support Contracts

- New package `vcse.support` implementing deterministic GSR-readiness contracts
- `SourceSpan`, `CandidateClaimView`, `ActiveRelationView`, `SourceSupportDecision` models (frozen dataclasses)
- Support profiles: `SUPPORT_EXACT`, `SUPPORT_NORMALIZED`, `SUPPORT_RULE_DERIVED`, `SUPPORT_AGENT_PROPOSED`, `EXPLORATORY_SUPPORT_PROFILE`
- `evaluate_source_support()` service function — deterministic, non-mutating, never emits VERIFIED/CERTIFIED
- API `POST /support/evaluate` endpoint using unified response contract
- CLI `vcse support evaluate --claim --spans --relations [--json]`
- Doctrine enforced: GROUNDED ≠ SOURCE_SUPPORTED ≠ VERIFIED
- Proposal-Agent/LLM/embedding similarity cannot assign SOURCE_SUPPORTED
- No changes to verifier, trust, proof, runtime, signing, or CMCF semantics
- false_verified_count remains 0
- v6.12 is the VCSE-side GSR-readiness contract; GSR project files not included

## v6.13.0 — Ontology Governance Foundation

- New package `vcse.ontology` implementing deterministic ontology governance
- Lifecycle states: PROPOSED → STRUCTURALLY_VALID → IMPACT_ANALYZED → CONFLICT_CHECKED → REGRESSION_TESTED → APPROVED → STAGED → ACTIVE
- Only ACTIVE relations are authoritative for source-support evaluation
- ACTIVE relations require support_profile_id checked against supported profile registry
- PROPOSED/APPROVED/STAGED relations excluded from source-support active map
- API `POST /ontology/validate` endpoint using unified response contract
- CLI `vcse ontology validate --registry <ontology.json> [--json]`
- CLI `vcse ontology relations --registry <ontology.json> --active-only [--json]`
- Ontology statuses/reason codes are UPPER_SNAKE_CASE
- ACTIVE ontology versions are immutable
- No changes to verifier, trust, proof, runtime, signing, or CMCF semantics
- false_verified_count remains 0

## Roadmap

VCSE remains deterministic correctness infrastructure. External runtime / agent / prompt work belongs outside VCSE.

### Completed

- v6.0.0    CMCF canonical foundation
- v6.1.0    universal source intake
- v6.2.0    configurable trust profiles + retroactive trust evaluation
- v6.3.0    .csrf compiled runtime layer
- v6.4.0    proof index
- v6.5.0    conflict workflows
- v6.5.1    verifier NO_PROOF enforcement
- v6.5.2    unconditional T4/T5 proof gate
- v6.6.0    policy execution layer
- v6.7.0    signing + authenticity
- v6.8.0    signed pack distribution lifecycle
- v6.9.0    runtime hardening + performance infrastructure
- v6.10.1   API/server hardening + unified error contract
- v6.11.0   reason service + functional API /reason
- v6.12.0   deterministic source-support contracts
- v6.13.0   ontology governance foundation
- v6.14.0   candidate proposal contract (external input safety boundary)

### v6.14.0 — Candidate Proposal Contract

External systems may submit candidates only. VCSE owns canonicalization, verification, trust promotion, and certification.

- `vcse.proposal` package: models, validation, adapter, serialization.
- Forbidden authority fields (`verification_status`, `certification_status`, `trust_tier`, `authoritative_support_profile_id`) rejected, not stripped.
- Input claim status must be `PROPOSED`. All other statuses rejected.
- Unknown top-level or claim-level fields rejected.
- Payload limit: 1 MiB.
- API `POST /proposal/validate` (unified response contract).
- CLI `vcse proposal validate --proposal <file> --json`.
- 63 contract tests.
- Deferred: Ledger Event Taxonomy, Renderer Guard, external runtime project files.

### Next

- v6.15.0   Ledger Event Taxonomy
- v6.16.0   Renderer Guard + Answer Verification
- v6.17.0   Repair Contract Foundation
- v6.18.0   Integration Adapter Contracts
- v6.19.0   CLI De-Monolith
- v6.20.0   Property-Based Testing
- v6.21.0   Mutation Testing Baseline
- v6.22.0   Formal Spec Skeleton
