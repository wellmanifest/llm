# Ticket 014: Modularize llm_io and harden CLI symlink traversal, JSON int bounds, RFC3339 subseconds, and control chars

- **ID**: ticket-014
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-11-11 user authorized auditing, fixing bugs, modularizing, and hardening across `wellmanifest/*` standard repositories.

Extract shared `docs/tools/llm_io.py` so `schema_validators.py` and `install.py` share one SSOT regular-file reader, symlink-ancestor guard, atomic writer, and strict JSON parser; fix the CLI `os.path.abspath` symlink-traversal bypass in `conformance.main` (`sym_dir/../real`) and relative (`../sym_dir`, CWD-under-symlink) traversal; bound JSON integer digit lengths before `int()` conversion; normalize 7–9 digit RFC3339 fractional seconds in `parse_rfc3339`; reject ASCII C0/DEL control characters across request/response/workflow string fields; keep all Python modules strictly `< 500` lines; and reconcile merged `project/ticket-013/README.md` to `DONE`.

## Acceptance criteria

- [x] AC-01: Extract `docs/tools/llm_io.py`, eliminate `os.path.abspath` CLI and relative `sym_dir/..` symlink-traversal bypasses, bound JSON integer digits before `int()`, support 1..9 digit RFC3339 subseconds, reject C0/DEL control characters, and keep all Python files strictly `< 500` lines.
- [x] AC-02: Pass `ruff check --no-cache docs/tools tests`, `pytest -q -p no:cacheprovider`, `python3 docs/tools/conformance.py --all`, `./project/governance-check.sh --base origin/main`, and `wellman check`, and mark merged `project/ticket-013/README.md` `DONE`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
