# Ticket 007: Declare that returned evidence spends the same context budget it explains

- **ID**: ticket-007
- **Status**: DONE
- **Workflow state**: DONE
- **Owner**: founder

## Goal and scope

Prompt text is read twice: by the model as an instruction, and by the runtime as
the query that decides which knowledge, artifacts and sources become context.
`limits.maxContextBytes` bounds the second reading, so every concrete reference
added for the first spends part of it.

The two readings pull hardest in opposite directions exactly when a failure is
explained back to the model. The diagnostic a model can act on is the one naming
exact paths and identifiers, and that is also the one that exhausts the budget
first.

Measured in a Subactor deployment on 2026-09-09, two comparable repairs failed
in opposite ways within the same hour:

- one carried a bare error code, kept its budget, and repeated the identical
  failure until its retry budget was exhausted;
- the other carried the full list of eight rejected paths, could have acted on
  it, and never reached a model turn — those eight references exhausted a
  context selection that, measured separately, would have resolved to zero
  files.

Neither could win. No component owned the conflict, because the budget lives in
one runtime, the prompt is assembled in another, and the bound on diagnostics
was tuned for log readability in a third.

## What this adds

Two invariants in the machine-policy layer, which the architecture already says
fixes limits:

- `llm-evidence-by-reference` — evidence too large to spend on a prompt is
  written where the model can read it and named once, so nothing is truncated
  to fit. Scaffolding for a single turn is removed when that turn ends.
- `llm-budget-single-owner` — one declared budget governs a request; a limit
  tuned without reference to it is not a budget.

`limits.maxInlineEvidenceBytes` makes the first one machine-readable.

## A defect found while adding it

Removing a required limit from the profile still passed `make check`.
Conformance named individual fields by hand and never validated the profile
against its own schema, so any key added to the schema stayed unenforced until
someone remembered to add a matching check — the precise failure this
repository exists to prevent in adopters.

It now asserts every schema-required key is present. Deliberately a subset of
JSON Schema: CI installs no dependencies, and presence is the part a
hand-written check forgets.

## Non-goals

No new repository. The problem is an unowned contract, not a location, and a
separate repository would move the seam while adding another adoption surface —
measured elsewhere in this fleet as 30 instances carrying another repository's
identity and a standard publishing seven revisions in one day.

Extraction becomes worth reconsidering once two independent implementations
honour this contract.

## Acceptance criteria

- [x] AC-01: The architecture states that prompt text is read twice and that
      returned evidence spends the declared context budget.
- [x] AC-02: `maxInlineEvidenceBytes` is declared, required, and bounded.
- [x] AC-03: Conformance rejects a profile missing any schema-required key,
      verified by removing one and by removing a pre-existing one.

Validation: `make check`.

## Tracking boundary

This directory contains the minimal reviewed intent. Executable code, research
scripts and tests belong in ordinary source directories.
