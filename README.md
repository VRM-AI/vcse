# VCSE

Verifier-Centered Symbolic Engine

VCSE is the verification and reasoning engine for Correctness Models (CMs).

Correctness Models are systems designed to produce outputs that are verifiably correct through explicit reasoning, validation, provenance, and controlled inference rather than probabilistic generation.

LLMs provide the creative spark.
CMs provide the logical grounding.

Developed by VelariumAI.
Hosted under the VRM-AI organization.

VCSE is not a chatbot and not a wrapper around a text model. The parser extracts
structure, memory stores state, proposers emit candidate transitions, search
explores bounded paths, verifiers judge, and the renderer explains evaluated
state.

## Doctrine

- Parser extracts structure.
- Memory stores state.
- Proposer generates transitions.
- Search explores.
- Verifier judges.
- Renderer explains.

No component predicts final text. No final answer is accepted without
verifier-backed state support and, for verified answers, a proof trace.

## Feature Coverage

- explicit claims
- provenance
- trust tiers
- deterministic inference
- conflict detection
- source adapters
- knowledge compiler
- autonomous ingest
- deterministic schema inference
- candidate pack lifecycle
- cross-pack reasoning
- global consistency checks
- SQLite runtime store
- future compiled symbolic runtime format (`.csrf`)

## Architecture

```text
Input
  -> Parser / CLI JSON loader
  -> WorldStateMemory
  -> Symbolic proposers
  -> Bounded state-transition search
  -> VerifierStack
  -> FinalStateEvaluator
  -> Deterministic renderer
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Semantic Regions (v3.2)

- Deterministic grouping by relation (default behavior unchanged)
- Optional canonical grouping for inverse-relation pairs (for example, `has_capital`/`capital_of`)
- Canonical mode is opt-in via `vcse region list --canonical`


## Install

```bash
python -m pip install -e .
```

## CLI

```bash
vcse demo logic
vcse demo arithmetic
vcse demo contradiction
vcse demo logic --search mcts
vcse ingest examples/ingestion/triples --json
vcse run examples/file.json
vcse benchmark benchmarks/simple_logic_cases.jsonl
vcse benchmark benchmarks/mixed_cases.jsonl --json
vcse benchmark benchmarks/mixed_cases.jsonl --search mcts --ts3
vcse ask "All men are mortal. Socrates is a man. Can Socrates die?" --search mcts
vcse dsl validate examples/dsl/basic_logic.json
vcse ask "Can Socrates perish?" --dsl examples/dsl/mortality.json
vcse index build --dsl examples/dsl/basic_logic.json
vcse ask "Can Socrates perish?" --dsl examples/dsl/mortality.json --index
vcse generate examples/generation/contractor_policy_spec.json
vcse gauntlet benchmarks/gauntlet/
vcse serve
vcse pack validate examples/packs/logic_basic
vcse pack install examples/packs/logic_basic
vcse pack bundle examples/packs/logic_basic --output /tmp/bundles
vcse pack verify-bundle /tmp/bundles/vrm.logic.basic.vcsepack --json
vcse pack inspect-bundle /tmp/bundles/vrm.logic.basic.vcsepack --json
vcse ask "Can Socrates die?" --pack vrm.logic.basic
vcse trust evaluate examples/trust/cross_supported_claims.jsonl
vcse trust promote examples/packs/trusted_basic
vcse ledger verify examples/packs/trusted_basic
vcse compiler validate-mapping --mapping examples/compiler/geography_mapping.json --domain domains/geography.yaml
vcse compile knowledge --source examples/knowledge/general_world_expanded.json --mapping examples/compiler/geography_mapping.json --domain domains/geography.yaml --pack-id compiled_geography --output-root examples/packs --benchmark-output benchmarks/compiled_geography_knowledge.jsonl --json
vcse adapter run --type json --source examples/knowledge/general_world_expanded.json --output /tmp/general_world_normalized.jsonl
vcse compile knowledge --adapter json --source examples/knowledge/general_world_expanded.json --mapping examples/compiler/geography_mapping.json --domain domains/geography.yaml --pack-id compiled_geography_v49 --output-root examples/packs --json
vcse pipeline run examples/pipelines/geography_compile.yaml --run-id test_geography_pipeline --json
vcse pipeline inspect test_geography_pipeline --json
vcse query --pack general_world --subject France --relation has_capital --json
vcse query --packs examples/packs --relation has_capital --object Paris --json
```

## Operational API Server (v6.12.0)

`vcse serve` starts the local HTTP API server (binds to `127.0.0.1:8000` by default).

Operational endpoints for health, readiness, runtime/proof/bundle validation, structured queries, reasoning, and source support:
- `/health` — service health status
- `/version` — VCSE and Python versions
- `/ready` — readiness probe
- `/live` — liveness probe
- `/runtime/validate` — validate `.csrf` artifact
- `/proof/validate` — validate `.proof.json` index
- `/pack/verify-bundle` — verify `.vcsepack` bundle integrity
- `/query` — structured deterministic query over `.csrf` runtime
- `/reason` — reason over `.csrf` runtime (functional in v6.11.0)
- `/support/evaluate` — deterministic source support evaluation (v6.12.0)

See [docs/API.md](docs/API.md) for response contract and examples.

## Deterministic Source Support (v6.12.0)

VCSE enforces a strict source-support boundary:

- **GROUNDED**: cited source span exists — does not imply SOURCE_SUPPORTED
- **SOURCE_SUPPORTED**: deterministic profile check passed — does not imply VERIFIED
- **VERIFIED**: verifier produced proof — does not imply CERTIFIED

Proposal-Agent/LLM judgment and embedding similarity cannot assign `SOURCE_SUPPORTED`. Active relations require a `support_profile_id`. Unknown relations return `NEEDS_ONTOLOGY`.

## CAKE — Knowledge Acquisition

VCSE 2.7.0 adds CAKE (Controlled Acquisition of Knowledge Engine), a deterministic pipeline for collecting structured knowledge from approved sources.

```bash
vcse cake validate --source examples/cake/general_world_sources.json
vcse cake run --source examples/cake/general_world_sources.json --dry-run
vcse cake run --source examples/cake/general_world_sources.json --limit 100
```

Sources: Wikidata JSON, DBpedia TTL. Allowed domains: wikidata.org, dbpedia.org. All claims pass the trust pipeline before certification.
```

Example JSON input:

```json
{
  "facts": [
    {"subject": "Socrates", "relation": "is_a", "object": "Man"},
    {"subject": "Man", "relation": "is_a", "object": "Mortal"}
  ],
  "constraints": [],
  "goal": {"subject": "Socrates", "relation": "is_a", "object": "Mortal"}
}
```

## Benchmarks

Benchmark files are JSONL. Each case may include `expected_status` and
`expected_answer`.

## Structured Query (v5.8)

`vcse query` is a deterministic retrieval interface over pack claims.

- Query retrieves existing claims only; it does not mutate state.
- Query does not perform fuzzy matching, embeddings, or LLM inference.
- `ask` remains the user-facing reasoning path; `query` is structured access.

Examples:

```bash
vcse query --pack general_world --subject France --relation has_capital --json
vcse query --packs examples/packs --relation has_capital --object Paris --json
vcse query --packs examples/packs --trusted-only --subject Socrates --json
```

## Explanation Layer (v5.9.0)

VCSE v5.9.0 adds a deterministic explanation and proof-rendering layer.

- Explanations are derived from existing result rows, provenance, and proof data.
- Explanations do not generate new facts and do not run extra inference.
- `NO PROOF != VERIFIED` is enforced in explanation rendering.

Definitions:

- `result`: the retrieved or inferred claim row.
- `provenance`: source metadata attached to claims.
- `proof trace`: ordered evidence steps already present in VCSE outputs.
- `explanation`: deterministic rendered structure over result + provenance + proof trace.
- `verification_status`: explicit claim state (`VERIFIED`, `UNVERIFIED`, `FAILED`, or `UNKNOWN` where source status is absent).

Examples:

```bash
vcse query --pack general_world --subject France --relation has_capital --json --explain
vcse reason --packs examples/packs --json --explain
```

## CMCF and .csrf Naming (v6.x framing)

- `CMCF` = `Correctness Model Canonical Format`
- `.csrf` = `Compiled Symbolic Runtime Format`

CMCF is the canonical, deterministic claim record structure.

CMCF records are:

- deterministic
- atomic
- provenance-aware
- status-aware
- hashable
- JSON-serializable
- suitable for signing
- suitable for later compilation into `.csrf`

`.csrf` is the compiled runtime artifact derived from CMCF in v6.3.0; it is not canonical truth.

### Compiled Runtime (.csrf)

- Canonical truth remains CMCF (`cmcf_records.jsonl` / CMCF JSON).
- `.csrf` is a deterministic compiled view with flattened records and indexes:
  - `by_subject`
  - `by_relation`
  - `by_object`
- Compilation does not alter claim meaning, trust, policy, or provenance linkage.

Example:

```bash
vcse compile csrf cmcf_records.jsonl --output runtime.csrf
vcse query --csrf runtime.csrf --subject France --relation has_capital --json
vcse reason --csrf runtime.csrf --json --explain
vcse runtime inspect runtime.csrf --json
```

## Proof Indexing (v6.4.0)

## Signed Pack Distribution (v6.8.0)

- Signing proves authenticity and integrity, not correctness.
- `SIGNATURE_VALID` does not imply trusted or certified claims.
- Bundle verification is a pre-ingest/pre-use safety check.
- Manifest integrity detects tampering before import/use.

Commands:

```bash
vcse pack bundle <pack_path> --output <dir> [--key <private_key>] [--json]
vcse pack verify-bundle <bundle_path> [--key <public_key>] [--json]
vcse pack inspect-bundle <bundle_path> [--json]
```

`.proof.json` is a deterministic compiled proof index over CMCF/.csrf data:

- Indexes proof paths VCSE can already derive (no new truth).
- Provides reverse-dependency lookups (`by_support`) for impact reasoning.
- Accelerates `--explain` output without changing result/inferred counts.

```bash
vcse proof build --csrf runtime.csrf --output runtime.proof.json --json
vcse proof why <claim_id> --proof-index runtime.proof.json --json
vcse proof supports <claim_id> --proof-index runtime.proof.json --json
vcse query --csrf runtime.csrf --subject France --explain --proof-index runtime.proof.json --json
vcse reason --csrf runtime.csrf --explain --proof-index runtime.proof.json --json
```

`.proof.json` is disposable; CMCF remains canonical.

## Conflict Resolution Workflows (v6.5.0)

Conflicts become reviewable operational objects with deterministic, non-mutating
workflows backed by the proof reverse-dependency graph:

- `keep_a`, `keep_b`, `mark_disputed`, `require_review` resolution options.
- Trust-aware rationale (`recommended_by_trust`) — never auto-applied.
- Workflow reports are JSON-stable and maintainer-controlled.

```bash
vcse conflict workflow --pack mypack --proof-index runtime.proof.json --json
vcse conflict export-report --packs ./packs --proof-index runtime.proof.json --output report.json
vcse conflict impact <conflict_id> --report report.json --json
```

```bash
vcse benchmark benchmarks/simple_logic_cases.jsonl
vcse benchmark benchmarks/arithmetic_cases.jsonl
vcse benchmark benchmarks/contradiction_cases.jsonl
vcse benchmark benchmarks/mixed_cases.jsonl
vcse benchmark benchmarks/mixed_cases.jsonl --json
```

## Ingestion

VCSE can deterministically import candidate knowledge packs from local
JSON/JSONL/CSV datasets. Ingest surfaces conflicts and entity metrics, writes
candidate packs, and never auto-certifies or merges.

```bash
vcse ingest path/to/dataset --json
vcse ingest path/to/dataset
vcse ingest path/to/explicit.jsonl --json --incremental
vcse ingest path/to/explicit.jsonl --json --incremental --force
```

Incremental ingest persists local run state under `.vcse/ingest_state/` and
emits deterministic delta summaries (`DELTA_NEW`, `DELTA_CHANGED`,
`DELTA_NO_CHANGES`) so unchanged input can be skipped without silent behavior.

See [docs/INGESTION.md](docs/INGESTION.md) and
[docs/CAPABILITY_PACKS.md](docs/CAPABILITY_PACKS.md).

Automated pipeline docs: [docs/AUTOMATED_PACK_ECOSYSTEM.md](docs/AUTOMATED_PACK_ECOSYSTEM.md).

## Quick Start — Dataset Conversion + Ingest

VCSE conversion is explicit and mapping-driven. The mapping declares which source
fields become `subject`, `relation`, and `object` rows, so output is
deterministic and auditable. VCSE v5.3 adds deterministic schema inference with
mapping proposals that remain reviewable and reproducible.

1. Convert sample dataset into explicit triples:

```bash
python scripts/convert_to_explicit.py
```

2. Ingest generated data:

```bash
vcse ingest datasets/processed/countries_explicit.jsonl --json
```

3. Inspect candidate packs:

```bash
vcse pack index --dirs examples/packs
vcse pack validate <pack_id>
vcse pack review <pack_id>
```

## Automatic Ingestion (v5.3)

`vcse ingest` can now infer schema and propose deterministic mappings for raw
JSON/JSONL/CSV datasets. No fuzzy matching is used; mapping is rule-based and
reproducible. Generated mappings are saved to:

`.vcse/mappings/<dataset_hash>.json`

Example:

```bash
vcse ingest datasets/raw/countries.json --auto-approve
```

If `--auto-approve` is omitted and a raw schema needs mapping, VCSE writes the
mapping artifact and exits that file with an approval-required error so you can
inspect and reuse the mapping.

## Cross-Pack Reasoning + Global Consistency (v5.4)

VCSE v5.4 reasons across multiple active packs while preserving deterministic
verification and global consistency checks. Cross-pack retrieval does not change
truth conditions; verifiers remain authoritative.

## DSL

VCSE includes a deterministic Rule/Template DSL for loading capabilities without
changing Python core modules. DSL bundles are explicit and command-scoped.

```bash
vcse dsl validate examples/dsl/basic_logic.json
vcse dsl compile examples/dsl/basic_logic.json
vcse ask "All men are mortal. Socrates is a man. Can Socrates die?" --dsl examples/dsl/basic_logic.json
vcse ingest path/to/dataset --json
```

See [docs/DSL.md](docs/DSL.md).

## Verified Generation

VCSE 1.7.0 adds deterministic, verifier-centered generation from explicit specs
and templates. Generation is construction plus verification.

- No free-form creative generation
- No LLM/neural dependencies
- Missing required fields return `NEEDS_CLARIFICATION`
- Artifacts include provenance and verification status

```bash
vcse generate examples/generation/contractor_policy_spec.json
vcse generate examples/generation/incomplete_policy_spec.json
vcse generate examples/generation/contractor_policy_spec.json --debug
vcse generate examples/generation/contractor_policy_spec.json --index
```

See [docs/GENERATION.md](docs/GENERATION.md).

## Gauntlet

VCSE 1.8.0 adds the Gauntlet adversarial benchmark suite for trust and
robustness evaluation across ask/generate/ingest flows.

Critical policy:

- Incorrect `VERIFIED` is a critical failure.
- `INCONCLUSIVE` is acceptable.
- No silent case skipping.

```bash
vcse gauntlet benchmarks/gauntlet/
vcse gauntlet benchmarks/gauntlet/ --json
vcse gauntlet benchmarks/gauntlet/ --search mcts --ts3 --index
```

See [docs/GAUNTLET.md](docs/GAUNTLET.md).

## API Usage

VCSE 1.9.0 provides an OpenAI-compatible API adapter while preserving verifier
semantics.

```bash
vcse serve
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"vcse-vrm-1.9","messages":[{"role":"user","content":"All men are mortal. Socrates is a man. Can Socrates die?"}]}'
```

See [docs/API.md](docs/API.md).

## Capability Packs

VCSE 2.2.0 adds installable capability packs for modular Correctness Model extension.

- Validate before install
- Local registry and local dependency resolution
- Deterministic activation per command
- No arbitrary code execution

```bash
vcse pack validate examples/packs/logic_basic
vcse pack install examples/packs/logic_basic
vcse pack list
vcse ask "Can Socrates perish?" --packs vrm.logic.basic,vrm.mortality.basic --index
```

See [docs/PACKS.md](docs/PACKS.md).

## Trust and Ledger

VCSE 2.3.0 adds trust tiering and immutable ledger support for auditable
knowledge certification.

- Ingest broadly, certify selectively
- Conflicted/stale knowledge is quarantined, not deleted
- Ledger is append-only and tamper-evident
- SHA-256 hash chain + Merkle pack integrity snapshots
- This is not a blockchain network

```bash
vcse trust evaluate examples/trust/cross_supported_claims.jsonl
vcse trust promote examples/packs/trusted_basic
vcse trust stats examples/packs/trusted_basic
vcse ledger verify examples/packs/trusted_basic --strict
```

See [docs/TRUST.md](docs/TRUST.md) and [docs/LEDGER.md](docs/LEDGER.md).

## Symbolic Indexing

VCSE 1.6.0 adds an optional deterministic symbolic index for capability
retrieval. It uses tokenized symbolic features with BM25-style scoring over DSL
artifacts and capability packs.

- No embeddings
- No neural dependencies
- CPU-only deterministic ranking
- Retrieval suggests candidates; verifier remains final authority

Indexing is opt-in and default behavior is unchanged.

```bash
vcse index build --dsl examples/dsl/basic_logic.json
vcse index stats --dsl examples/dsl/basic_logic.json
vcse ask "Can Socrates perish?" --dsl examples/dsl/mortality.json --index
vcse benchmark benchmarks/mixed_cases.jsonl --search mcts --ts3 --index
```

Metrics include status accuracy, answer accuracy, status rates, runtime, nodes
expanded, search depth, and proof trace length.

## Versioning

VCSE 1.1.0 adds the interaction layer. VCSE 1.0.0 was the first stable release. See [docs/VERSIONING.md](docs/VERSIONING.md).

## Improvement Methodology

VCSE is improved through benchmark-driven iteration, rule expansion, verifier
expansion, heuristic tuning, and failure analysis. It is not trained on text.

See [docs/TRAINING.md](docs/TRAINING.md).

## Strict Policy

Core implementation is CPU-only and must not add text-model dependencies. See
[docs/NO_LLM_POLICY.md](docs/NO_LLM_POLICY.md).

## Limitations

- Current parser is a structured JSON loader, not a broad natural-language
  parser.
- Current reasoning domains are small: transitive relations, equality conflicts,
  and simple numeric constraints.
- Search uses Beam Search; richer strategies are future work.
- Search backend is configurable:
  - BeamSearch (default deterministic bounded search)
  - MCTSSearch (optional exploration backend with verifier-centered scoring)
- TS3 is an optional state-space analysis layer for loop/stagnation/absorption diagnostics.
- DSL is optional and deterministic; built-ins remain active when no bundle is loaded.
- Symbolic indexing is optional and deterministic; when disabled, VCSE uses full
  bundle behavior exactly as before.
- Solver-backed proposals are optional and skipped when the external solver
  package is unavailable.

## Roadmap To 1.0.0

VCSE 1.0.0 is released. Future work tracked in docs/ROADMAP.md.

## Development

```bash
python -m pytest
```

## Production Use

```bash
python -m pip install -e .
vcse serve
vcse serve --host 0.0.0.0 --port 8000
```

```bash
docker build -t vcse .
docker run -p 8000:8000 vcse
```

See [docs/CONFIG.md](docs/CONFIG.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for runtime settings and deployment notes.

## Knowledge Automation

VCSE can build deterministic knowledge packs from local JSON, JSONL, CSV, and structured text sources.

```bash
vcse knowledge validate examples/ingestion/simple_claims.json
vcse knowledge build examples/ingestion/simple_claims.json --pack test_pack
vcse pack install ./test_pack
vcse pack list
```

See [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) for the source, validation, conflict, and pack format.

## Inverse Inference

VCSE v3.3.0 adds deterministic inverse-relation inference as a read-only query fallback.

- Uses ontology inverse definitions only (example: `has_capital -> capital_of`)
- Checks explicit claims first, then inferred inverses
- Does not write inferred claims into packs

Inspect inferred inverse claims:

```bash
vcse infer inverse --pack general_world
```

## Transitive Location Inference

VCSE v3.4.0 adds bounded two-hop transitive inference for location/containment.

- Approved chains only:
  - `located_in_country + part_of -> located_in_region`
  - `located_in_country + located_in_region -> located_in_region`
- Max inference depth is fixed at 2
- Explicit claims still win over inferred claims
- Inferred claims are runtime-only and non-persistent

Inspect inferred transitive claims:

```bash
vcse infer transitive --pack general_world
```

## Inference Explanations

VCSE v3.5.0 adds deterministic explanation rendering for inferred answers.

- Explanations are derived only from explicit claim provenance used by inference
- No new inference rules are added
- Reasoning behavior and correctness remain unchanged
- Explanations are runtime-only and non-persistent
- Explicit claim answers remain unchanged

Example:

```bash
vcse ask "What continent is Paris in?" --pack general_world
```

Output:

```text
Paris is in the Europe region because:
- Paris is in France.
- France is part of Europe.
```

Disable explanation output for inferred answers:

```bash
vcse ask "What continent is Paris in?" --pack general_world --no-explain

# Opt-in planned shard-aware execution (v4.6 pilot)
vcse ask "What is the capital of France?" --pack general_world --planned
vcse benchmark coverage --pack general_world --planned --json
```

## Universal Source Intake (v6.1.0)

VCSE now includes a deterministic universal source intake path to normalize heterogeneous sources into CMCF.

Supported sources:

- local JSON / JSONL / CSV / HTML table
- local directory
- HTTP/HTTPS URL returning JSON / JSONL / CSV / HTML table

Pipeline:

`source -> resolve/fetch -> detect -> adapter -> rows -> profile -> CMCF -> validate -> candidate pack`

CLI:

```bash
vcse ingest <source> --cmcf
vcse ingest <source> --cmcf --profile historical_events
vcse ingest <source> --cmcf --limit 100 --dry-run --json
```

Behavior rules:

- URL sources always use universal intake.
- Local sources use legacy ingest by default; pass `--cmcf` for universal intake.
- Output is candidate-only (`lifecycle_status=candidate`, `verification_status=UNVERIFIED`, `certification_status=NOT_CERTIFIED`).
- Deterministic only. No NLP/LLM extraction, no fuzzy matching, no auto-certification.

## Configurable Trust Profiles (v6.2.0)

VCSE v6.2.0 adds deterministic, policy-driven Trust Profiles for retroactive trust assessment over CMCF records.

- CMCF records remain immutable facts-as-ingested.
- Trust Profiles are maintainer policy.
- Trust Assessments are derived outputs.
- Candidate data remains usable but labeled.
- Self-certification is explicit and fully gated.
- No profile match defaults to `candidate` unless the profile changes `default_action`.

Examples:

```bash
vcse trust profile inspect examples/trust_profiles/default_candidate_profile.json --json
vcse trust profile apply examples/trust_profiles/historical_events_candidate_profile.json --cmcf events.cmcf.jsonl --json
vcse trust profile diff old.json new.json --cmcf records.cmcf.jsonl --json
```

## Runtime Hardening and Performance Benchmarking (v6.9.0)

VCSE v6.9.0 adds operational hardening around compiled runtime artifacts:

```sh
# Validate a compiled runtime index
vcse runtime validate path/to/runtime.csrf --json

# Validate a proof index
vcse proof validate path/to/proofs.proof.json --json

# Measure runtime performance (no hard thresholds)
vcse perf benchmark --csrf runtime.csrf --proof-index proofs.proof.json --iterations 3 --json
```

Validation catches: out-of-range indexes, duplicate positions, invalid trust tiers, lowercase status casing, and NaN/Inf values. Checked loaders raise `RuntimeArtifactError` on structural failures — no silent fallbacks.
