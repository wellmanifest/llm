# Ticket 011: Harden LLM strict JSON, regular-file IO, URI traversal, and unhashable guards

- **ID**: ticket-011
- **Owner**: tom
- **Status**: DONE
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

Harden `docs/tools/schema_validators.py`, `docs/tools/conformance.py`, and
`docs/tools/install.py` against symlink/FIFO/oversized file reads, non-finite
or deeply nested JSON payloads, URI path traversal segments, unhashable enum
containers, and non-string object keys, add adversarial regression tests in
`docs/tools/test_llm_hardening.py`, and mark merged `ticket-010` `DONE`.

## Acceptance criteria

- [x] AC-01: Enforce `O_NOFOLLOW | O_NONBLOCK` 4 MiB regular-file UTF-8 reads,
      preserve leaf symlink paths in CLI invocations so symlinks are refused,
      reject `NaN`/`Infinity`/`1e999` and `> 64` JSON nesting, block `.` / `..`
      / `//` / `\` / control-char URI segments, and guard unhashable enum and
      non-string dict keys without `TypeError`.
- [x] AC-02: Pass `ruff check docs/tools tests`, `pytest -q`,
      `python3 -m unittest`, `make check`,
      `./project/governance-check.sh --base origin/main`, and `wellman check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
