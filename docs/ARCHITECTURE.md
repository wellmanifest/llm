# Architecture

`wellmanifest/llm` is a portable domain pack. It does not implement an LLM
gateway, knowledge service, credential broker or agent daemon. Those runtime
responsibilities remain in Subactor.

## Five cooperating layers

1. **Host bootstrap** — the host-specific instruction file is read at session
   start and points the agent to `.wellmanifest/llm.json`.
2. **Machine policy** — the versioned profile fixes operation order, limits,
   authority and secret handling without choosing a provider.
3. **Semantic protocol** — the same request and response envelopes cross MCP,
   HTTPS, CLI or immutable-file transports.
4. **Runtime mediation** — Subactor resolves knowledge, artifacts, current
   state, declared research gaps, credentials and SubLLM routes outside model
   authority.
5. **Evidence** — deterministic validation and redacted receipts establish
   what was resolved, invoked and accepted.

No single layer is sufficient. Host text makes behavior natural but cannot
enforce it. JSON is deterministic but is not automatically discovered. MCP is
the preferred tool transport but does not itself define authority. Runtime
mediation enforces policy, while conformance detects drift.

## Ownership and authority

- `HOME wellmanifest`, `SHAPE domain_pack`: schemas, protocol, adapters and
  conformance rules in this repository.
- `runtimeOwner subactor`: product services, CLI/daemons, knowledge, artifact
  lookup, live observation, credential leases, SubLLM routes and receipts.
- The LLM is advisory. It may propose a mutation but cannot create its own
  grant or trusted merge evidence.
- A provider/model name is runtime policy. Replacing GLM, OpenAI, Anthropic or
  a local model does not change this standard if the envelopes and invariants
  remain conformant.

## Data flow

The host discovers the profile, then Subactor resolves internal context before
the selected model is invoked. A managed textual artifact is resolved through
its immutable artifact revision before editing. Fresh state is obtained through
a bounded read-only observation. Missing or stale knowledge is sent to
`research.plan`; only an `internet-research` gap authorizes targeted external
research after deduplication. Validation runs after model output, and a
secret-free receipt closes the operation.

External provenance URLs are evidence, not runtime dependencies. Durable
assumptions use versioned `knowledge://subactor/.../vN` references; managed
text uses `artifact://subactor/.../rN` references.
