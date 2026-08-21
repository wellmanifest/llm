# Ticket 001: Establish Subactor-first LLM project guidance

- **ID**: ticket-001
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-21

## Goal and scope

Document why portable LLM integration needs a layered contract rather than one
prompt or one transport. Establish `wellmanifest/llm` as the provider-neutral
standard while Subactor retains runtime ownership. Complete the repository
instance's project guidance and reserve its Make entrypoint.

## Acceptance criteria

- [x] AC-01: README states the layered integration decision and HOME/ADOPT
  boundary.
- [x] AC-02: README states that prompts are advisory and runtime mediation is
  required for enforcement.
- [x] AC-03: Governance and whitespace checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)

## Publication evidence

- Linux, Windows and remote lifecycle checks passed on exact head
  `ef735935e1b6345ac7216f9d1e2cd2b91bfa560a`.
- Direct Validator review approved that exact head and merged PR #5 as
  `cdcc43f6a0c894b5917f6de46f13793e408c0096`.
- Protected `main` was read back with the documentation slice and its source
  branch deleted before this closure.
