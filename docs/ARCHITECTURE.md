# VCSE Architecture

VCSE is a verifier-centered symbolic reasoning engine for Correctness Models (CMs). It does not
use next-token prediction. It reasons by structured state transitions, bounded
search, and deterministic verification.

Current public milestone state:
- v5.3: deterministic schema inference (mapping proposal path)
- v5.4: cross-pack reasoning + global consistency checks
- v5.8: structured deterministic query retrieval layer
- v5.9: deterministic explanation + proof rendering layer
- v6.0: CMCF schema/model/validation foundation

```text
Input JSON / CLI demo
  -> optional ingestion adapters/templates/provenance
  -> optional DSL bundle (synonyms/patterns/rules/templates)
  -> optional generation template bundle for `vcse generate`
  -> optional capability pack activation (`--pack` / `--packs`)
  -> optional trust tier evaluation + promotion policy
  -> optional immutable ledger append + verification
  -> optional symbolic index + capability retrieval (token/BM25)
  -> deterministic parser
  -> WorldStateMemory
  -> symbolic proposers
  -> search backend (Beam default, optional MCTS)
  -> verifier stack
  -> final state evaluator
  -> explanation builder (opt-in for query/reason)
  -> deterministic renderer
```

## Components

- Parser: extracts facts, constraints, and goals into typed memory objects.
- DSL: optional deterministic capability bundle for parser patterns, synonym
  rules, relation schemas, ingestion templates, proposer rules, clarification
  rules, renderer templates, and verifier stubs.
- Ingestion: adapter + template pipeline imports candidate knowledge with
  provenance and validation.
- Generation: deterministic template-based artifact construction and
  verification with bounded repair.
- Gauntlet: adversarial benchmark runner/evaluator/metrics/reporting for
  trust validation.
- API Adapter: OpenAI-compatible HTTP interface translating requests into
  deterministic ask/generate/ingest CM execution.
- Memory: stores claims, constraints, goals, symbol bindings, evidence, and
  contradiction indexes.
- Proposers: produce `Transition` objects only.
- Search:
  - BeamSearch (default): deterministic bounded frontier search.
  - MCTSSearch (optional): UCB1-guided bounded exploration.
  - Both backends are verifier-centered and return `SearchResult`.
- TS3: optional transient symbolic state-space analysis for loop, reachability,
  absorption, novelty, and contradiction-risk diagnostics.
- Symbolic Indexing: optional deterministic retrieval layer that selects
  relevant artifacts/packs using symbolic tokens and BM25-style scoring.
- Packs: installable local capability modules with manifest validation,
  dependency resolution, deterministic activation, and audit support.
- Trust: deterministic tiering, cross-source support checks, conflict scoring,
  and staleness analysis for claim lifecycle management.
- Ledger: append-only hash-chain event history plus Merkle integrity snapshots
  for tamper-evident auditing.
- Distribution: deterministic pack bundle manifest/sign/verify/inspect lifecycle
  for pre-ingest authenticity and tamper detection.
- Verifiers: judge claims, constraints, contradictions, and goal satisfaction.
- Renderer: prints evaluated state with no inference or decision logic.
- Explanation layer: deterministic node/trace models and renderers for
  query/reason outputs; consumes existing result/provenance/proof data only.
- CMCF layer: canonical deterministic record model for normalized claims
  (`Correctness Model Canonical Format`) and validation/hashing foundation.
- CAKE (v2.7.0): Controlled Acquisition of Knowledge Engine — deterministic
  acquisition frontend that fetches, snapshots, extracts, and routes structured
  claims into the normalization → trust → ledger → pack pipeline. Owns: source
  config, transport (file/HTTP), immutable snapshots, deterministic extractors.
  Delegates to existing knowledge/trust/ledger/pack systems. Boundary: `List[KnowledgeClaim]`.

## Guardrails

- Search is always bounded by depth, beam width, and node expansion limits.
- MCTS exploration is bounded by iteration count, max depth, and rollout depth.
- Final answers come only from `FinalStateEvaluator`.
- Verified answers include proof traces.
- Contradictory and unsatisfiable states are rejected as final answers.
- TS3 may diagnose and deprioritize, but may not override final-state truth.
- Ingested knowledge is never implicitly true; verifiers determine usable state.
- DSL artifacts format behavior only; verifier remains the final authority.
- Retrieval is optimization only; it may prioritize/deprioritize candidates but
  must not change truth conditions.
- Structured query is deterministic claim retrieval only and does not trigger
  broad inference or mutate packs/runtime stores.
- Explanation rendering does not fabricate proof/provenance and does not alter
  result count or reasoning semantics.
- `.csrf` (`Compiled Symbolic Runtime Format`) is the v6.3.0 compiled runtime
  artifact derived from CMCF and does not replace canonical JSONL/CMCF truth.
- Generated artifacts are accepted only after deterministic evaluation.

## Universal Source Intake (v6.1)

New deterministic source intake stack:

- `intake.source`: source reference metadata
- `intake.fetch`: local/URL fetch and cache (`.vcse/source_cache`)
- `intake.detect`: extension/content-type/sniff format detection
- `intake.router`: adapter + profile routing
- `adapters.*`: JSON/JSONL/CSV/HTML table row extraction
- `profiles.*`: deterministic row-to-CMCF mapping
- `cmcf.normalize`: orchestration + CMCF validation

Design constraints:

- deterministic only
- provenance attached on every CMCF record
- lifecycle `candidate`, verification `UNVERIFIED`, certification `NOT_CERTIFIED`
- unknown formats are rejected (no silent guessing)

## Trust Profile Layer (v6.2)

Added deterministic trust profile subsystem:

- `trust.profile`: profile/rule dataclasses
- `trust.profile_loader`: JSON schema validation and deterministic load
- `trust.profile_engine`: deterministic evaluation and self-certification gates
- `trust.profile_result`: immutable decision/assessment outputs
- `trust.profile_diff`: retroactive profile-to-profile decision diffing

Runtime behavior:

- Evaluates immutable CMCF records into derived trust decisions
- Does not mutate canonical CMCF by default
- Supports retroactive recomputation and auditability

## Compiled Runtime Layer (v6.3)

- `runtime.compiler`: deterministic CMCF -> CSRF compilation.
- `runtime.serialize`: stable JSON `.csrf` save/load (`sort_keys`, compact separators, UTF-8, no NaN/Inf).
- `runtime.loader`: runtime loading from `.csrf`, CMCF JSON/JSONL, or pack directories.
- `runtime.index`: subject/relation/object index lookup helpers.

Design constraints:

- CMCF remains canonical source of truth.
- CSRF remains fully reproducible from CMCF.
- No semantic transformation or trust/policy mutation during compile.

## Proof Index Layer (v6.4)

- `proof.model`: `ProofStep`, `ProofPath`, `ProofIndex` dataclasses.
- `proof.compiler`: deterministic compilation of proof paths from CSRF and from
  reasoning records (`derived_from` + `proofs`).
- `proof.index`: builder that emits ordered `ProofIndex` and reverse-dependency
  maps (`by_result`, `by_support`, `by_subject`, `by_relation`, `by_object`).
- `proof.serialize`: deterministic JSON (`.proof.json`) save/load.
- `proof.loader`: file-based load and `load_or_build_proof_index` helper.
- `proof.explain`: `select_best_proof` + `proof_path_to_explanation_trace`.

Design constraints:

- Proof index is derived; it never creates new truth.
- Zero-proof results are never promoted to `VERIFIED`.
- Proof ordering is deterministic: verification status, path length, trust tier,
  lexicographic `proof_id`.
- `.proof.json` is disposable and rebuildable from CMCF/.csrf.

## Signed Pack Distribution (v6.8)

- `distribution.bundle`: deterministic `<pack_id>.vcsepack` creation.
- `distribution.manifest`: canonical bundle manifest and content hashing.
- `distribution.verify`: manifest hash validation + optional Ed25519 signature verification.
- `distribution.inspect`: non-mutating bundle status inspection.

Design constraints:

- Signing/authenticity is separate from claim correctness and trust promotion.
- Signature validity does not bypass trust profiles or policy execution.
- No network key lookup and no private key storage in repository.

## Conflict Resolution Workflows (v6.5)

- `conflict.workflow`: `ConflictRef`, `ConflictImpact`, `ResolutionOption`,
  `ConflictWorkflowReport`, deterministic `conflict_id` hashing, conflict-to-ref
  conversion, and claim annotation helpers.
- `conflict.impact`: `analyze_conflict_impact` walks the proof reverse-dependency
  graph; falls back to direct-only impact when no proof index is supplied.
- `conflict.resolution`: deterministic option generator emitting `keep_a`,
  `keep_b`, `mark_disputed`, `require_review` with trust-aware rationale.
- `conflict.report`: `build_conflict_workflow_report` orchestrates analysis and
  yields a sorted, serialisable report.

Design constraints:

- No conflict is ever auto-resolved.
- Trust-tier comparisons appear in option rationale only as
  `recommended_by_trust`; nothing is selected automatically.
- Existing `ConflictDetector` outputs and CMCF/.csrf data are never mutated.

## Runtime Hardening and Performance Benchmarking (v6.9.0)

### Runtime Validation (`vcse.runtime.validate`)

`validate_csrf_index(index)` checks structural invariants of a compiled `.csrf` file:
- Index positions in `by_subject/relation/object` are in-range and non-duplicate
- Every record appears in all three indexes
- `trust_tier >= 0`, `verification_status` is UPPER_SNAKE_CASE, no NaN/Inf values

### Proof Index Validation (`vcse.proof.validate`)

`validate_proof_index(index)` checks proof index consistency:
- VERIFIED proofs must have `path_length >= 1` and at least one supporting claim
- All index positions are in-range and non-duplicate
- Required fields (`proof_id`, `result_claim_id`) are present

### Atomic Writes (`vcse.runtime.atomic`)

`atomic_write_text/bytes` writes via a temp sibling file + `os.replace`, preventing partial artifacts on interrupted writes.

### Checked Loaders (`vcse.runtime.hardening`)

`load_csrf_checked` and `load_proof_index_checked` load and validate artifacts, raising `RuntimeArtifactError` on structural failures. Do not silently repair invalid indexes.

### Performance Benchmark (`vcse.perf.benchmark`)

`run_runtime_benchmark(csrf_path, ...)` measures LOAD_CSRF, QUERY_SUBJECT/RELATION/OBJECT, PROOF_LOOKUP operations. Returns a `BenchmarkReport` with per-operation `elapsed_ms`. No hard timing thresholds — v6.9 establishes measurement infrastructure only.

## Operational API Layer (v6.11.0)

- `api.server`: HTTP server binds to `127.0.0.1:8000` by default.
- `api.endpoints`: health, version, readiness, liveness, runtime/proof/bundle validation, structured query, reason.
- `api.response`: unified `VcseResponse` contract with `status`, `version`, `request_id`, `data`, `errors`.
- `api.errors`: machine-readable UPPER_SNAKE_CASE error codes, no raw tracebacks.
- `api.xheader`: `X-Request-ID` echo support for request tracing.

### Reason Service (`vcse.reasoning.service`)

Introduced in v6.11.0. Extracted from `cli.run_reason` to provide a reusable, testable service layer.

- `ReasonServiceRequest`: frozen dataclass — `csrf_path`, `proof_index_path`, `trusted_only`, `explain`, `max_results`.
- `ReasonServiceResult`: frozen dataclass — `status`, `inferred_count`, `inferred_claims`, `explanations`, `issues`.
- `run_reason_service()`: loads and validates `.csrf` via `load_csrf_checked`, optionally validates proof index,
  applies policy, invokes `cross_pack_reason`, returns structured result.
- Statuses: `REASON_COMPLETE`, `REASON_FAILED`, `REASON_RUNTIME_INVALID`, `REASON_PROOF_INVALID`.
- Does not mutate artifacts, does not write files, does not alter verifier or trust semantics.

Design constraints:

- Never auto-certifies or bypasses verifier/trust.
- No remote key lookup, no LLM logic.
- Signature validity ≠ truth (structural integrity only).
- All responses deterministic and non-mutating.

### Source Support Package (`vcse.support`) — v6.12.0

Deterministic GSR-readiness contracts. Does not implement GSR project files.

- `SourceSpan`: cited source span (source_id, source_span_id, text, optional metadata).
- `CandidateClaimView`: lightweight adapter for support checks (not a CMCF record replacement).
- `ActiveRelationView`: minimal active relation view with mandatory `support_profile_id`.
- `SourceSupportDecision`: decision result (final_status, reason_code, supported, source_span_ids).
- `evaluate_source_support()`: deterministic service — never emits VERIFIED or CERTIFIED.
- Profiles: `SUPPORT_EXACT` (literal), `SUPPORT_NORMALIZED` (NFC/casefold/whitespace), `SUPPORT_RULE_DERIVED` (skeleton), `SUPPORT_AGENT_PROPOSED` (→ EXPLORATORY only), `EXPLORATORY_SUPPORT_PROFILE` (→ EXPLORATORY only).

Doctrine:
- GROUNDED (span exists) ≠ SOURCE_SUPPORTED.
- SOURCE_SUPPORTED requires active relation + valid profile + deterministic check passing.
- Proposal-Agent / LLM / embedding similarity cannot assign SOURCE_SUPPORTED.
- Unknown relations → NEEDS_ONTOLOGY. Missing profile → INVALID_ONTOLOGY_RELATION.

### Ontology Package (`vcse.ontology`) — v6.13.0

Deterministic ontology governance layer. Separates lifecycle management from source-support evaluation.

- `model`: `OntologyRelation`, `OntologyEntityType`, `OntologyClaimType`, `OntologyRegistry`, lifecycle state constants (PROPOSED, STRUCTURALLY_VALID, IMPACT_ANALYZED, CONFLICT_CHECKED, REGRESSION_TESTED, APPROVED, STAGED, ACTIVE, and side states).
- `lifecycle`: transition validation, `is_active()`, `is_authoritative_for_source_support()`.
- `registry`: `active_relation_view_from_ontology_relation()`, `relation_map_for_source_support()` — builds source-support map from ACTIVE relations only.
- `validate`: `validate_ontology_registry()`, `validate_ontology_relation()`, `validate_active_relation_requirements()` — UPPER_SNAKE_CASE issue codes.
- `serialize`: deterministic JSON serialization of ontology registries.

Design constraints:

- Only ACTIVE relations are authoritative for source-support evaluation.
- PROPOSED, APPROVED, STAGED are not ACTIVE — excluded from source-support map.
- ACTIVE relations require a valid `support_profile_id`.
- Ontology versions are immutable once ACTIVE.
- API `/ontology/validate` endpoint uses unified response contract.
- CLI `vcse ontology validate` and `vcse ontology relations` commands are command-native JSON (not API-wrapped).

### Candidate Proposal Package (`vcse.proposal`) — v6.14.0

External input safety boundary. Enforces the Candidate Proposal Contract.

- `model`: machine constants (`CANDIDATE_PROPOSAL`, `FACTUAL_CLAIM_PACK`, `PROPOSED`, `CANDIDATE_ACCEPTED`, etc.) and frozen dataclasses (`CandidateClaimProposal`, `CandidateProposal`, `CandidateProposalValidationResult`, `CandidateProposalAdapterResult`).
- `validate`: `validate_candidate_proposal_dict()`, `load_and_validate_candidate_proposal_json()` — structural validation only; never calls verifier, trust promoter, or source-support service.
- `adapter`: `proposal_to_candidate_claim_views()` — converts valid proposals to candidate views; output remains `CANDIDATE_ACCEPTED`, never VERIFIED or SOURCE_SUPPORTED.
- `serialize`: deterministic JSON serialization with `sort_keys=True, allow_nan=False`.

Core invariants:
- External callers submit candidate material only. VCSE owns canonicalization, verification, trust promotion, and certification.
- `CANDIDATE_ACCEPTED` ≠ VERIFIED, CERTIFIED, or SOURCE_SUPPORTED.
- Input claim `status` must be `PROPOSED`. Any other value is rejected.
- Forbidden authority fields (`verification_status`, `certification_status`, `trust_tier`, `authoritative_support_profile_id`) are **rejected**, not silently stripped.
- Unknown top-level or claim-level fields are rejected.
- Payload limit: 1 MiB.
- API `POST /proposal/validate` and CLI `vcse proposal validate` use command-native JSON (CLI not API-wrapped).
