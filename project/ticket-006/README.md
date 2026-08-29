# Ticket 006: Ignore Python test artifacts

- **ID**: ticket-006
- **Owner**: agent:grok under SESSION_EXECUTION_AUTHORIZATION
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-29

## Goal and scope

Stop Python bytecode and pytest/ruff caches from dirtying the checkout.
Declare `.gitignore` on the governance workstream so later hygiene edits have
an owner.

## Acceptance criteria

- [x] AC-01: `.gitignore` ignores `__pycache__/`, `*.py[cod]`, `.pytest_cache/`
      and `.ruff_cache/`.
- [x] AC-02: `./project/governance-check.sh --actor agent` reports `GOV-PASS`.

## Participants

- Human participant: session request to allocate gitignore tickets and clean
  leftover branches; no `user-*` file was created or modified.
- Agent participant: [ai-grok.md](ai-grok.md)
