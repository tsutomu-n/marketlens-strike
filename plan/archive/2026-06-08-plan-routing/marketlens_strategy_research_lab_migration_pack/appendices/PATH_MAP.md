# Path Map

## New Paths

```text
src/sis/research/strategy_lab/
src/sis/research_protocol/
configs/strategies/
configs/evaluation/
schemas/strategy_experiment_spec.v1.schema.json
schemas/strategy_signal.v1.schema.json
schemas/trial_record.v1.schema.json
schemas/trade_candidate.v1.schema.json
schemas/paper_candidate_pack.v1.schema.json
schemas/promotion_decision.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
```

## Existing Paths To Keep

```text
src/sis/venues/trade_xyz/
src/sis/real_market/
src/sis/tracking/
src/sis/paper/
src/sis/reports/
src/sis/ops/
```

## Paths To Retire Later

```text
src/sis/backtest/signals.py
src/sis/core/strategy.py  # ResearchSignalStrategy
signals.csv active dependency
```
