<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:21 JST
-->

# Decision

## Decision Summary

Use the Grok source only as a prompt-quality and planning-quality checklist.
Do not use it as a repository architecture plan.

Accepted:

- read the repository before planning
- define goal, constraints, and done conditions
- make AI plans testable and handoff-ready
- challenge idealized architecture narratives
- keep implementation incremental

Rejected for this repo slice:

- `src/strat_tool` package creation
- `research/experiments` as the main research split
- `strategy/active` and `strategy/archive` as the new strategy structure
- VectorBT as the default backtester
- broad structure migration before a concrete implementation blocker exists

Adapted:

- Strategy separation must preserve Strategy Lab artifacts and schema contracts.
- Research validation ideas must map to NDX Layer 2.x and Strategy Lab gates.
- Architecture improvements should be expressed as narrow boundary-hardening
  tasks.

## Recommended Next Plan

Create a separate plan for a future Layer 2.5 research-only export contract.

That future plan should answer:

- What exact Layer 2.4 decision allows export?
- What artifact is exported to Strategy Lab?
- What schema validates the export?
- How is export kept research-only?
- Which tests prove no paper or live path is connected?

## Decision Boundary

Do not implement Layer 2.5 in this Grok adoption review. This package is a
decision memo and handoff plan only.

