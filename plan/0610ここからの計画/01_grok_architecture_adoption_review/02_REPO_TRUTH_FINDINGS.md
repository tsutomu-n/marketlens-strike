<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:31 JST
-->

# Repo Truth Findings

## Current Package Boundary

`marketlens-strike` is already a Python `src` layout project.

Confirmed current package:

```text
src/sis
```

`pyproject.toml` builds the package from:

```text
packages = ["src/sis"]
```

Therefore a new `src/strat_tool` package is not a neutral cleanup. It would be a
package rename or parallel package introduction and requires a separate
migration plan.

## Current Product Boundary

Current project description:

```text
Trade[XYZ] research, Strategy Lab authoring, paper operations, and read-only safety gates
```

Current development is backtest-first and venue-neutral. Trade[XYZ] remains an
implemented venue and future order-entry candidate, but it is not the current
default execution axis.

## Current Subsystem Boundary

Current architecture already separates these implementation surfaces:

- `src/sis/research/strategy_lab`
- `src/sis/research/dag`
- `src/sis/research/ndx`
- `src/sis/backtest/engine`
- `src/sis/backtest/trade_xyz`
- `src/sis/paper`
- `src/sis/execution`
- `src/sis/venues`
- `src/sis/commands`

The source proposal's generic `research/experiments` split does not match this
active implementation structure.

## Current Strategy Boundary

The current Strategy Lab flow is:

```text
StrategyExperimentSpec
  -> StrategySignalRecord
  -> EvaluationPlan
  -> TrialRecord / TrialLedger
  -> TradeCandidate
  -> PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents
```

This flow is more specific than a generic `Strategy Protocol` plus
`active/archive` directory split. Any strategy reorganization must preserve this
artifact flow.

## Current Backtest Boundary

Current backtest surfaces are:

- Trade[XYZ] pure backtest v0.1 Python API
- Strategy Authoring fixed-horizon backtest
- legacy `build-backtest` bridge

VectorBT is not a current dependency. Making it the primary backtester is an
architecture and dependency decision, not a cleanup task.

## Current Research Boundary

NDX Layer 2.2, 2.3, and 2.4 are local research gates. Layer 2.4 currently stops
at `REVISE_2_3` for insufficient validation sample and era count. It does not
export Strategy Lab artifacts.

The likely next implementation axis is a narrow Layer 2.5 research-only export
contract, not broad repository restructuring.

