<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:21 JST
-->

# Risk And Narrative Audit

## Main Narrative Risk

The risky narrative is:

```text
If we define a clean architecture early, the project will naturally become easier to finish.
```

For this repository, that is incomplete. The repo already has active boundaries,
schemas, CLI commands, and gates. A new architecture skeleton can create drift if
it bypasses existing contracts.

## Concrete Risks

- Creating `src/strat_tool` would split or rename the active package without an
  import, packaging, CLI, and docs migration plan.
- Moving research code out of `src/sis/research` would confuse active
  implementation code with disposable experiments.
- Adding `strategy/active` and `strategy/archive` would create a second strategy
  registry beside Strategy Lab artifacts.
- Making VectorBT primary would add a dependency and semantic mismatch before a
  concrete backtest gap is identified.
- Generic phase plans can hide the current highest-value next boundary: Layer
  2.4 to future Strategy Lab research-only export.
- Numerai concepts can be overfit into the project if they are used as branding
  rather than mapped to concrete validation checks.

## Missing Checks To Avoid

Any future architecture plan must check:

- `pyproject.toml`
- `uv run sis --help`
- `docs/CURRENT_STATE.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/research/ndx/README.md`
- `docs/backtest/README.md`
- `docs/strategy_research_lab/README.md`
- relevant schemas and Pydantic models

## Better Framing

Use this framing instead:

```text
Do not build a new skeleton.
Tighten the next missing contract inside the existing skeleton.
```

The near-term candidate is a future Layer 2.5 contract that turns an approved
NDX residual validation result into a research-only Strategy Lab export without
paper or live execution.

