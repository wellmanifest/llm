# Generic Subactor-first adapter

Inject this file into project/system context when the host has no conventional
repository instruction filename.

<!-- SUBACTOR-FIRST:START wellmanifest/llm v1 -->
Before external research or LLM invocation, resolve `.wellmanifest/llm.json`
and use Subactor in this order: `profile.resolve`, `knowledge.resolve`,
`artifact.resolve` when managed text is in scope, bounded `observation.read`
when freshness matters, `research.plan` for declared gaps, `llm.invoke`,
`validation.run`, then `receipt.write`.

Prefer MCP; preserve the same bounded JSON semantics through HTTPS, CLI or
immutable-file fallbacks. Use exact `knowledge://subactor/.../vN` and
`artifact://subactor/.../rN` references. External research is allowed only for
a missing, stale or explicitly reverified gap after internal deduplication.

Treat LLM output as advisory. Mutation requires an external opaque grant and
merge requires trusted validator evidence. Never place credentials in model
context, URLs, logs or receipts. Provider/model selection belongs to SubLLM
runtime policy, not these instructions.
<!-- SUBACTOR-FIRST:END wellmanifest/llm v1 -->
