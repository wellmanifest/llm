# Ticket 016: Extend wellmanifest/llm with bounded small-model decision slice budget

- **ID**: ticket-016
- **Owner**: agent:antigravity (`SESSION_EXECUTION_AUTHORIZATION`)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-21

## Goal and scope

Extend `wellmanifest/llm` (`models/llm-profile.schema.json`, `models/subactor-first.v1.json`,
`docs/tools/conformance.py`, `docs/ARCHITECTURE.md`, and `docs/tools/test_decision_slice_budget.py`)
with the backward-compatible `limits.maxDecisionSliceBytes` budget (`128..1024`, default `600`)
and normative `llm-decision-slice-budget` rule for fast small-model decision roles (`roles.decision`,
e.g. `d1:3b`), aligned with `wellmanifest/logs`'s `urtlog-bridge-profile/v1`.

## Acceptance criteria

- [ ] AC-01: `models/llm-profile.schema.json` accepts optional `limits.maxDecisionSliceBytes`
      (`128..1024`) while keeping existing v1 profiles without that field valid;
      `models/subactor-first.v1.json` sets `"maxDecisionSliceBytes": 600`.
- [ ] AC-02: `docs/tools/conformance.py` enforces integer bounds `128..1024` and
      `maxDecisionSliceBytes <= maxInlineEvidenceBytes <= maxContextBytes` when present,
      and adversarial tests in `docs/tools/test_decision_slice_budget.py` pass.
- [ ] AC-03: `docs/ARCHITECTURE.md` documents `llm-decision-slice-budget` with the
      2026-11-21 live `d1:3b` A/B/C evidence and cross-references `wellmanifest/logs`.
- [ ] AC-04: `make verify` and unit tests pass cleanly with zero regressions.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
