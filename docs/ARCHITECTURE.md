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

## Evidence spends the budget it explains

Prompt text is read twice. The model reads it as an instruction, and the runtime
reads the same text to decide which knowledge, artifacts and sources to resolve
into context. `limits.maxContextBytes` bounds the result of the second reading,
so every concrete reference added for the benefit of the first reading spends
part of it.

This matters most when a failure is explained back to the model. A diagnostic
that names the exact paths, artifacts or identifiers involved is the one a model
can act on — and is also the one that consumes the budget fastest. The two
readings therefore pull in opposite directions, and a runtime that satisfies
neither ends up serving a model that either cannot act or is never reached.

Measured in a Subactor deployment on 2026-09-09: two comparable repairs failed
in opposite ways within the same hour. One carried a bare error code, kept its
budget and repeated the identical failure until its retry budget was exhausted.
The other carried the full list of eight rejected paths, could have acted on it,
and never reached a model turn because those eight references exhausted the
context selection — which, measured separately, would have resolved to nothing
at all.

Two rules follow.

`llm-evidence-by-reference`
: Evidence too large to spend on a prompt is written where the model can read
  it and named once. A durable reference costs one entry and delivers the whole
  finding, so nothing is truncated to fit. Scaffolding written for a single turn
  is removed once that turn ends, because a runtime that measures changed state
  will otherwise read the explanation as part of the work.

`llm-budget-single-owner`
: One declared budget governs a request. A component that bounds evidence for
  readability, a component that assembles the prompt and a component that
  selects context are all spending `limits.maxContextBytes`, and a limit tuned
  in one of them without reference to that declaration is not a budget. Where a
  runtime enforces its own separate ceiling, it states the relationship to the
  declared one rather than competing with it.

External provenance URLs are evidence, not runtime dependencies. Durable
assumptions use versioned `knowledge://subactor/.../vN` references; managed
text uses `artifact://subactor/.../rN` references.
