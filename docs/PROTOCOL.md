# Subactor-first protocol v1

The normative order is the eight-entry `workflow` in
`models/subactor-first.v1.json`. A host may skip only a step whose profile says
`required: false` and whose `when` predicate does not apply.

## Ordered operations

1. `profile.resolve` — discover and validate `.wellmanifest/llm.json`.
2. `knowledge.resolve` — resolve exact internal knowledge versions before
   Internet sources.
3. `artifact.resolve` — before reading or changing documentation, JSON,
   schemas or DSL, resolve format, schema, version source and validation
   receipt.
4. `observation.read` — when freshness matters, perform a bounded safe
   read-only observation.
5. `research.plan` — ask Subactor for declared gaps. `live-observation` remains
   internal; `internet-research` returns a targeted query and internal versions
   that must be deduplicated first.
6. `llm.invoke` — invoke a route selected by SubLLM policy. The provider and
   model are receipt fields, never authority.
7. `validation.run` — apply deterministic schema, test and policy gates. Model
   findings remain advisory.
8. `receipt.write` — record immutable context references, selected route/model,
   transport, timing and grant reference without secret values.

## Transport negotiation

Prefer MCP when the host supports tool discovery and bounded structured calls.
Fallback in order to HTTPS, CLI and immutable files. Every transport carries
the same `wellmanifest.llm-request/v1` and `wellmanifest.llm-response/v1`
semantics; a fallback may not broaden limits or authority.

Transport discovery is deployment-specific. Endpoint URLs, socket names and
CLI locations belong in Subactor runtime configuration, not the portable
profile. Tokens never appear in URLs or envelopes.

## Request example

```json
{
  "schema": "wellmanifest.llm-request/v1",
  "requestId": "req:01JEXAMPLE0001",
  "operation": "knowledge.resolve",
  "intent": {"query": "current LLM routing policy"},
  "limits": {"maxItems": 8, "maxBytes": 65536, "timeoutSeconds": 30},
  "authority": "read-only",
  "contextRefs": []
}
```

## Failure and gap behavior

- `denied` means the requested authority or grant was unavailable. The model
  must not reinterpret it as permission.
- `gap` must include the research method, bounded query and versioned entries
  to deduplicate.
- `error` is terminal for that operation unless runtime policy explicitly
  permits a retry. A paid request is never silently replayed through another
  provider.
- A mutation request requires an opaque `grant://` reference. The referenced
  secret or capability is resolved outside model context.
