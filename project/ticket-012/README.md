# Ticket 012: Harden LLM inode identity, JSON overflow/surrogates, URI colons, and closed schemas

- **ID**: ticket-012
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

Harden `docs/tools/schema_validators.py`, `docs/tools/conformance.py`, and
`docs/tools/install.py` with `lstat`+`fstat` `(st_dev, st_ino)` regular-file
identity and ancestor symlink checks, `max_bytes` positive integer bounds,
`10**400` integer overflow and lone UTF-16 surrogate rejection in strict JSON
and `request.intent`, `\A...\Z` regex anchors, colon-delimited URI traversal
rejection, iterative depth-bounded schema validation and closed object schema
checks, and mark merged `ticket-011` `DONE`.

## Acceptance criteria

- [x] AC-01: Enforce `lstat`+`fstat` `(st_dev, st_ino)` identity, ancestor
      symlink rejection, and `max_bytes` integer bounds in `read_regular_utf8`
      and `atomic_write`, reject `10**400` integer overflow and lone UTF-16
      surrogates in strict JSON and `request.intent`, anchor regexes with
      `\A...\Z`, block colon-delimited `..` URI segments, and enforce iterative
      depth-bounded closed object schema validation.
- [x] AC-02: Pass `ruff check --no-cache`, `pytest -q -p no:cacheprovider`,
      `python3 docs/tools/conformance.py --all`,
      `./project/governance-check.sh --base origin/main`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
