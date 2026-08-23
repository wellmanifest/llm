# Ticket 002: Add governed CI checks for llm standard

- **ID**: ticket-002
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-21

## Goal and scope

Add the repository-instance CI workflow required by the adopted governance
declaration. Run the managed governance gate on Linux and Windows so published
check names are `test` and `windows-governance`.

## Acceptance criteria

- [x] AC-01: CI publishes the two declared required check names.
- [x] AC-02: Linux and Windows entrypoints run their managed governance gates.
- [x] AC-03: Local governance and whitespace checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
