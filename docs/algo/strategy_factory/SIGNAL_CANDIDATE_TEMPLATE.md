# Signal Candidate Template

1候補1枚で使うテンプレートです。未記入項目がある候補は、原則としてbacktestへ進めません。

```md
# Signal Candidate: <SIG-ID> <name>

## Status

- status: idea | specified | data-ready | backtest-ready | backtested | paper-observing | rejected | archived
- owner:
- created:
- updated:
- next_gate:
- duplicate_key:
- reviewer:
- evidence_paths:
- promotion_blockers:

## Hypothesis

- one_sentence_hypothesis:
- archetype: trend | pullback | breakout | mean-reversion | volatility | regime | cross-asset | event
- market:
- symbol_universe:
- timeframe:
- holding_horizon:
- side: long | short | both

## Signal Contract

- required_inputs:
- required_input_sources:
- trigger:
- invalidation:
- no_trade_conditions:
- signal_output_columns:
  - ts_signal
  - symbol
  - side
  - timeframe
  - reason
  - score
  - invalidation_price

## Baseline

- baseline_name:
- baseline_logic:
- why_fair:

## Data Readiness

- historical_available:
- paper_available:
- observed_at_available:
- known_missingness:
- leakage_risks:
- timezone_policy:
- data_delay_policy:

## Pre-backtest Score

| item | score 0-3 | note |
|---|---:|---|
| clarity | | |
| data availability | | |
| timing correctness | | |
| invalidation | | |
| baseline | | |
| simplicity | | |
| total | | |

## Reject Rules

- reject_if:
- taxonomy_codes:
- evidence_required:

## Backtest Review

- trade_count:
- net_return_after_cost:
- max_drawdown:
- average_adverse_excursion:
- worst_trade:
- cost_x2_result:
- slippage_x2_result:
- parameter_neighborhood:
- skipped_signal_review:

## Paper Review

- paper_window:
- fills_count:
- skipped_count:
- paper_backtest_gap:
- unexplained_gap:
- promotion_blockers:

## Decision Log

- YYYY-MM-DD:
```

## Required Defaults

- `next_gate` must be one of the workflow states in `FACTORY_WORKFLOW.md`.
- `duplicate_key` should be `<archetype>:<universe>:<timeframe>:<trigger-family>`.
- `taxonomy_codes` should come from `SIGNAL_REJECT_REASON_TAXONOMY.md`.
- `evidence_paths` should point to reports, logs, scorecards, or source notes when available.
- `promotion_blockers` should be empty before moving to the next gate.
