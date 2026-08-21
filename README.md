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

## Subactor-first order

`profile.resolve` → `knowledge.resolve` → `artifact.resolve` when managed text
is in scope → bounded `observation.read` when freshness matters →
`research.plan` for declared gaps → `llm.invoke` → `validation.run` →
`receipt.write`.

The provider and model are selected by SubLLM runtime policy. The standard
therefore continues to work when a route changes, as long as the operation
envelopes, authority rules and receipts remain conformant.

## Quick start

Verify this checkout:

```sh
make verify
```

Preview Codex adoption in another repository without writing:

```sh
make install-dry-run HOST=codex TARGET=../consumer
```

Apply only after reviewing the preview:

```sh
make install HOST=codex TARGET=../consumer CONFIRM_APPLY=1
```

The installer appends a marked block to existing host instructions and copies
a self-contained `.wellmanifest/` profile/schema bundle. It refuses differing
installed contracts unless replacement is explicitly authorized.

## Contract map

- [Architecture](docs/ARCHITECTURE.md) — layers, ownership and authority.
- [Protocol](docs/PROTOCOL.md) — ordered operations and transport negotiation.
- [Adoption](docs/ADOPTION.md) — host setup and safe installation.
- [Reference profile](models/subactor-first.v1.json) and
  [profile schema](models/llm-profile.schema.json).
- [Request schema](models/request.schema.json) and
  [response schema](models/response.schema.json).
- [Host adapters](docs/adapters) and [reference tools](docs/tools).
