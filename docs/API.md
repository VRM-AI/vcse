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
`.csrf` is a future compiled runtime format derived from CMCF and is not the canonical truth layer.

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
