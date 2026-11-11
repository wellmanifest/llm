# Ticket 009: Harden LLM conformance validator and transactional installer

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

Close fail-open validation gaps, crash vectors, and partial-write installer
hazards in `docs/tools/conformance.py` and `docs/tools/install.py`, add
dependency-free request/response contract validators in
`docs/tools/schema_validators.py`, and publish `pyproject.toml` so `ruff` and
governed `pytest` run cleanly.

## Acceptance criteria

- [x] AC-01: Reject duplicate JSON object keys, non-dict nested profile
      sections, unknown closed-schema properties, boolean-for-int limit
      bypasses, and inverted `END ... START` marker pairs.
- [x] AC-02: Enforce `models/request.schema.json` and
      `models/response.schema.json` (including `grantRef` and `gap`
      conditionals) via `conformance.py --request` / `--response`.
- [x] AC-03: Make `docs/tools/install.py` transactional (all plans validated
      before any write) and reject symlinked intermediate directories or
      non-regular targets.
- [x] AC-04: Pass `ruff check`, `make check`,
      `./project/governance-check.sh --base origin/main`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
