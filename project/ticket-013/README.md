# Ticket 013: Harden LLM deep absolute symlink ancestors, response UTF-8 surrogates, and install target checks

- **ID**: ticket-013
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-11-11 user authorized auditing, fixing bugs, and hardening across `wellmanifest/*` standard repositories.

Reject deep absolute-path symlink ancestors in `schema_validators.read_regular_utf8` and `install.main`, reject lone UTF-16 surrogates across `validate_response_document` string fields (`gap.query`, `results[i].mediaType`, `results[i].summary`, `receipt.route`, `receipt.model`) and `install.atomic_write`, keep all modules strictly `< 500` lines, expand `docs/tools/test_llm_hardening.py`, and reconcile merged `project/ticket-012/README.md` to `DONE`.

## Acceptance criteria

- [x] AC-01: `read_regular_utf8` and `install.main` reject nested absolute-path symlink ancestors, and `validate_response_document` and `atomic_write` reject lone UTF-16 surrogates while keeping all Python files strictly `< 500` lines.
- [x] AC-02: Pass `ruff check --no-cache docs/tools tests`, `pytest -q -p no:cacheprovider`, `python3 docs/tools/conformance.py --all`, `./project/governance-check.sh --base origin/main`, and `wellman check`, and mark merged `project/ticket-012/README.md` `DONE`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
