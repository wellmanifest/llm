# Ticket 003: Publish Subactor-first LLM protocol and adapters

- **ID**: ticket-003
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-21

## Goal and scope

Publish the versioned provider-neutral contract that makes Subactor-first
behavior portable across LLM hosts. Include strict JSON schemas, the ordered
operation protocol, six host adapters, a safe installer and dependency-free
conformance checks.

## Acceptance criteria

- [x] AC-01: The profile fixes the Subactor-first operation order while keeping
  provider/model selection outside the standard.
- [x] AC-02: Profile, request and response JSON document families have strict
  schemas and a conforming reference profile.
- [x] AC-03: Codex, Claude, Gemini, Cursor, Copilot and generic adapters carry
  the same marked normative block.
- [x] AC-04: The installer is dry-run by default, preserves existing host
  instructions and refuses profile replacement unless explicitly allowed.
- [x] AC-05: Dependency-free conformance and installer smoke checks pass.
- [x] AC-06: Managed governance and whitespace checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
