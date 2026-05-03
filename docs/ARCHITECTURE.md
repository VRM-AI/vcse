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
