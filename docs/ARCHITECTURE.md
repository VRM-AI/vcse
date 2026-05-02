# VCSE Architecture

VCSE is a verifier-centered symbolic reasoning engine for Correctness Models (CMs). It does not
use next-token prediction. It reasons by structured state transitions, bounded
search, and deterministic verification.

Current public milestone state:
- v5.3: deterministic schema inference (mapping proposal path)
- v5.4: cross-pack reasoning + global consistency checks
- v5.8: structured deterministic query retrieval layer
- v5.9: deterministic explanation + proof rendering layer

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
- Generated artifacts are accepted only after deterministic evaluation.
