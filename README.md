# wellmanifest/llm

Provider-neutral standard for making an LLM host use Subactor first for
knowledge, managed artifacts, bounded live state, research gaps, model routing
and validation receipts.

## The decision

Use all integration layers together, not one magic prompt or one mandatory
transport:

1. A host bootstrap file makes the behavior discoverable at session start.
2. A versioned JSON profile and schemas make the contract machine-readable.
3. A semantic operation protocol works through MCP first, with bounded HTTPS,
   CLI and immutable-file fallbacks.
4. Subactor runtime mediates tools, credentials, authority and LLM routing.
5. Deterministic conformance and secret-free receipts prove what happened.

A prompt is useful guidance, but it is not an authority boundary. A host that
must guarantee Subactor-first behavior needs runtime mediation and conformance,
even when its underlying model or provider changes.

## Ownership

This repository is `HOME wellmanifest`, `SHAPE domain_pack`. It owns the
portable standard. Product services, CLIs, daemons, knowledge, artifact lookup,
live observation and SubLLM routing remain `HOME subactor`. Consumers `ADOPT
wellmanifest/llm`; they do not move Subactor runtime into wellmanifest.

The normative schemas, profile, adapters and reference checks are delivered as
a separate integration slice under the repository's protected publication
process.
