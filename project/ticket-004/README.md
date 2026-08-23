# Ticket 004: Publish README and Make verification entrypoints

- **ID**: ticket-004
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-21

## Goal and scope

Publish the final landing page and safe Make entrypoints for the already
integrated v1 profile, protocol, adapters, installer and conformance checker.

## Acceptance criteria

- [x] AC-01: README links every normative contract and gives dry-run and apply
  examples.
- [x] AC-02: `make check`, `make governance` and `make verify` pass.
- [x] AC-03: `make install` refuses to write without `CONFIRM_APPLY=1`.
- [x] AC-04: Managed governance and whitespace checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
