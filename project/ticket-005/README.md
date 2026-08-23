# Ticket 005: Adopt new-project standard 0.18.6

- **ID**: ticket-005
- **Owner**: agent:gemini under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-23

## Goal and scope

Adopt published `wellmanifest/new-project` 0.18.6 into `wellmanifest/llm` in one atomic transaction through `create_adoption_lock.py`.
Brings the host-agnostic contract (CLAUDE.md, GEMINI.md, Cursor rule, pre-commit hook, agent-hosts.json validator) and `governance / enforce` CI job.

## Acceptance criteria

- [x] AC-01: `python3 .governance/agent_host_check.py --root .` → `GOV-AGENT-HOST-PASS` after `./scripts/install-agent-hosts.sh`.
- [x] AC-02: `./project/governance-check.sh --actor agent` → `GOV-PASS`, all managed digests match lock.
- [x] AC-03: `make check` passes; domain contracts unaffected.

## Publication evidence

- Pull request: `wellmanifest/llm#12`
- Frozen and approved head: `3e821c0584ff0b5d9949a0ccb88e511eb967b748`
- Merge commit: `5032d0c24e7a1337c0718c7993d65e3c7823302a`
- Validator approval: review `5002463558`, run `32641726625`.

## Participants

- Human participant: authorized via active session.
- Agent participant: [ai-gemini.md](ai-gemini.md)
