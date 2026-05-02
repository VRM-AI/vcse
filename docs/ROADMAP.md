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

## Next

- v6.0 — CMCF schema/model/validation foundation
- v6.1 — universal source adapters to CMCF
- v6.2 — source trust profiles + policy-gated intake
- v6.3 — `.csrf` compiled runtime format
- v6.4 — proof indexing + trace engine
- v6.5 — conflict resolution workflows
- v6.6 — advanced policy execution engine
- v6.7 — pack signing + manifest integrity
- v6.8 — encrypted/private pack support
- v6.9 — runtime performance hardening
- v6.10 — production API/server hardening

## v7.0 Interface Layer

v7.0 introduces an interface layer with optional LLM integration:

`optional LLM interface -> structured query/intent -> VCSE execution -> verified/explained output`

VCSE remains the verifier-centered execution core.
