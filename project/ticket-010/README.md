# Ticket 010: Add standalone pytest conformance and installer regression suite

- **ID**: ticket-010
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

Add a standalone dependency-free regression test suite in
`tests/test_llm_conformance.py` exercising `docs/tools/conformance.py`,
`docs/tools/schema_validators.py`, and transactional `docs/tools/install.py`
under both `pytest` and `python3 -m unittest`, and mark merged `ticket-009`
closed (`DONE`).

## Acceptance criteria

- [x] AC-01: Cover bundled conformance checks, strict duplicate-key JSON
      parsing, marker-pair validation, `llm-request/v1` and `llm-response/v1`
      schema/conditional validation, and closed-profile edge cases.
- [x] AC-02: Cover installer dry-run safety, idempotence, transactional
      all-or-nothing rollback on conflict, clean marker-span append, and
      symlinked root/intermediate directory rejection.
- [x] AC-03: Pass `pytest -q`, `ruff check`, `make check`,
      `./project/governance-check.sh --base origin/main`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
