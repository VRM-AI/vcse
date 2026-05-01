# No-LLM Policy

VCSE is a verification and reasoning engine for Correctness Models (CMs). It does not
use next-token prediction. It reasons by structured state transitions, bounded
search, and deterministic verification.

Core source code must not import or depend on:

- OpenAI or Anthropic SDKs
- Torch
- TensorFlow
- Transformers packages
- Autoregressive text-generation systems

Policy and architecture documentation may mention these systems only to contrast
them with VCSE's symbolic design.
