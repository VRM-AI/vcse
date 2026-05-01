# VCSE Roadmap

## Current System State (v5.4.0)

Completed milestones:
- v5.0: pack system
- v5.1: identity + conflict detection
- v5.2: ingest system
- v5.3: schema inference (deterministic mapping proposal)
- v5.4: cross-pack reasoning + global consistency

## Roadmap (Planned)

### v5.5 - Certification + Trust Gating
- pack certification states (`candidate -> verified -> trusted`)
- trust threshold enforcement
- manual + rule-based promotion

### v5.6 - Policy Enforcement Layer
- rule-based reasoning constraints
- forbidden inference prevention
- domain policy packs

### v5.7 - Incremental Ingest & Delta Updates
- partial dataset updates
- diff-based pack updates
- deterministic re-ingest

### v5.8 - Query Interface (Read API)
- structured query interface
- subject/relation/object retrieval
- deterministic query paths

### v5.9 - Explanation Layer
- human-readable reasoning traces
- proof chain rendering
- explainable outputs

### v5.10 - Pack Composition System
- pack dependency graphs
- reusable pack modules
- controlled composition

### v5.11 - Domain Specialization Packs
- geography, logic, policy, and related domains
- domain-specific constraints
- validation packs

### v5.12 - Multi-hop Reasoning Optimization
- deeper inference chains
- deterministic pruning strategies

### v5.13 - Conflict Resolution Workflows (Manual Only)
- structured review system
- human-in-the-loop conflict resolution

### v5.14 - Provenance Indexing
- fast lookup of provenance chains
- reverse-trace queries

### v5.15 - Runtime Performance Layer
- deterministic caching
- faster graph traversal

### v5.16 - Streaming Inference
- large dataset reasoning without full load
- chunk-based evaluation

### v5.17 - Pack Versioning System
- semantic pack versions
- compatibility rules

### v5.18 - Validation Engine Hardening
- stricter validation rules
- schema enforcement upgrades

### v5.19 - Trust Propagation Refinement
- deterministic multi-source trust handling
- tiered trust policies

### v5.20 - Global Consistency Enforcement
- system-wide invariant checks
- contradiction detection across all packs

## v6.x Framing (High Level)

`.csrf` = Compiled Symbolic Runtime Format.

Purpose:
- binary runtime for Correctness Models (CMs)
- CPU-first execution
- explicit indexing
- zero-copy access

Rules:
- JSONL remains canonical truth.
- `.csrf` is a compiled runtime artifact.
- compilation must be reversible.
- `.csrf` must support indexed lookup, provenance, proof traces, and explanation rendering.
- this section is framing only; no implementation is introduced here.
