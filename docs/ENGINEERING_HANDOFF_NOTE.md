# Engineering Handoff Note

## Purpose

This note explains how to use `marketlens_strike_engineering_handoff.zip` with the current `marketlens-strike` repository.

The ZIP is **not** a clean-slate implementation specification.
It is a **next-phase engineering plan based on the current repository**.

If the ZIP and the repository appear to differ, do not assume the ZIP is describing an empty or unimplemented codebase.

## Current Repository Status

The current repository already contains most of Phase 1 implementation work.

Implemented or largely implemented already:

- venue evidence collection scaffolding
- gTrade sidecars
- Ostium sidecars
- quote normalization
- cost matrix generation
- quote diagnostics
- Go/No-Go reporting
- EvidenceCard generation
- signal CSV compatible backtest bridge
- strict artifact validation

Not yet complete operationally:

- live evidence quality confirmation
- final Phase 1 gate clearance
- Phase 2 research layer implementation
- Phase 3 and later trading-system layers

## How To Read The ZIP

Read the ZIP as:

1. a roadmap for the next implementation layers
2. a task board for what still needs to be built
3. a target architecture description
4. a planning artifact that assumes the current repository already exists

Do **not** read the ZIP as:

1. a proof that nothing is implemented yet
2. a fresh repo bootstrap specification
3. a replacement for current repository code

## Source Of Truth Order

When there is any mismatch, use the following precedence.

1. Current repository code
2. `docs/ACCEPTANCE_AUDIT.md`
3. `docs/IMPLEMENTATION_STATUS.md`
4. `docs/CURRENT_PHASE_STATUS_AND_NEXT_GATE.md`
5. `docs/PHASE2_COMPLETION_DEFINITION.md`
6. `marketlens_strike_engineering_handoff.zip`

The ZIP is guidance for what comes next.
The repository is the source of truth for what exists now.

## Immediate Operational Status

As of the current repo state, this project must still be treated as **operationally in Phase 1**.

Reason:

- live evidence quality is not yet confirmed
- current Go/No-Go remains conditional
- Phase 2 entry gate is not yet open

This means:

- docs work may continue
- planning work may continue
- task decomposition may continue
- but Phase 2 implementation should not be treated as officially started

## Immediate Priority Before Phase 2

Before starting Phase 2 implementation, complete the following in this order:

1. `P1-003` collect live evidence
2. `P1-005` review diagnose output
3. `P1-004` validate artifacts with `--strict`
4. refresh Go/No-Go
5. refresh EvidenceCard

This order matters because schema and artifact existence alone are not enough.
The repository must also confirm that live evidence quality is acceptable.

## Phase 2 Entry Rule

Proceed to Phase 2 only if the Phase 1 recheck leads to one of the following:

- `GO`
- `CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST`

Do **not** proceed to Phase 2 if the decision remains one of the following:

- `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- `NO_GO_STALE`
- `NO_GO_SESSION`
- `NO_GO_COST`
- any equivalent live-evidence-quality blocker

## What This Note Does Not Define

This document does **not** define what it means for Phase 2 to be complete.

For that, use:

- `docs/PHASE2_COMPLETION_DEFINITION.md`

This note only defines:

- how to interpret the ZIP
- how to interpret current repo state
- when it is acceptable to enter Phase 2

## Recommended Review Order For Engineers

An engineer receiving the ZIP and this repository should read in this order:

1. `README.md`
2. `docs/ACCEPTANCE_AUDIT.md`
3. `docs/IMPLEMENTATION_STATUS.md`
4. `docs/CURRENT_PHASE_STATUS_AND_NEXT_GATE.md`
5. this document
6. `docs/PHASE2_COMPLETION_DEFINITION.md`
7. the ZIP contents and `TASK_BOARD.csv`

## One-Line Summary For External Handoff

Use the following summary when sharing the ZIP with an engineer:

```txt
This ZIP is a next-phase plan based on the current marketlens-strike repository. It is not a clean-slate implementation spec. The repository already contains most of Phase 1 and a signal-CSV-compatible backtest bridge. Before Phase 2 begins, complete P1-003 live evidence collection, P1-005 diagnose review, and P1-004 strict artifact validation, then recheck Go/No-Go.
```

