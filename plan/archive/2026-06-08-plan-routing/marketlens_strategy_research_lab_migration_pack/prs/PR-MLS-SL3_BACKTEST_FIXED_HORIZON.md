# PR-MLS-SL3 Backtest Bridge Fixed Horizon

## Goal

既存の next_row exit だけでなく、固定保有時間で評価できるようにする。

## Files To Change

```text
src/sis/backtest/bridge.py
src/sis/backtest/signals.py  # if legacy export still used
src/sis/research/strategy_lab/evaluation_runner.py
```

## Exit Models

```text
next_row
fixed_horizon
```

## fixed_horizon Behavior

```text
- signal timestamp以降のentry quoteを探す
- holding_horizon_minutes後以降の最初のquoteをexitにする
- exit quoteがなければ stale_rejected
- cost modelはholding horizonを使う
```

## Tests

```text
- fixed_horizon finds correct exit row
- missing exit increments stale_rejected
- next_row legacy mode still works during migration
```

## Done

```text
- EvaluationRunner can call bridge with fixed_horizon
- strategy_trial_report includes exit_model
```
