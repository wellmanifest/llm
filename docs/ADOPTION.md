# Adoption

## Minimum integration

1. Expose Subactor operations through MCP when available and preserve HTTPS,
   CLI or immutable-file fallbacks with identical envelopes.
2. Install one host adapter plus the self-contained `.wellmanifest/` profile
   and schema bundle with the reference installer. Existing instruction files
   are appended to, never overwritten.
3. Configure SubLLM routes and credentials in Subactor runtime, not in the
   profile or host instructions.
4. Run `python3 docs/tools/conformance.py --all` in CI.
5. Require deterministic gates and trusted merge evidence independently of
   model output.

Dry-run all host targets:

```sh
python3 docs/tools/install.py --host all --target .
```

Install only Codex and the machine profile into another repository:

```sh
python3 docs/tools/install.py --host codex --target ../consumer --apply
```

If an installed `.wellmanifest/` contract already differs, installation fails
closed. Review the version change and use `--replace-profile` with `--apply`
only when replacement of the complete contract bundle is authorized. An
existing marked adapter block is idempotent.

## Host behavior

Adapters are bootstrap hints, not enforcement boundaries. A capable runtime
should inject or discover the profile before model invocation, expose only
bounded operations, and reject requests that violate sequence, authority or
limits. Hosts that cannot read a conventional instruction file should inject
`docs/adapters/SUBACTOR.md` as their system/project context.

The standard deliberately does not require one model. The same installation
works when SubLLM policy changes provider or model, provided receipts record
the actual route and deterministic validation remains authoritative.
