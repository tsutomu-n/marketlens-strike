# Test Matrix

## SL0

```text
StrategyExperimentSpec parses
SymbolBinding validates
missing SymbolBinding fails
StrategyRunProfile forbids live claims
DataSnapshotManifest requires paths
FeatureSnapshotManifest requires input_data_snapshot_id
```

## SL1

```text
strategy_signals.parquet/jsonl written
signals.csv legacy export only
execution_symbol and real_market_symbol required
unknown generator fails closed
```

## SL2

```text
TrialLedger appends all trials
parameter_hash stable
selected trial does not hide failed trials
claim flags default false
missing data_snapshot_id fails
```

## SL3

```text
fixed_horizon exit selects correct exit row
missing exit increments stale_rejected
next_row mode remains until legacy retirement
```

## SL4

```text
blocked/no_signal candidates retained
selected/rejected ids consistent
claim flags false
```

## SL5

```text
PromotionDecision required before PaperIntentPreview
phase-gate-review not accepted as approval
bot-preview not accepted as approval
```

## SL6

```text
PaperIntentPreview valid_until required or explicit None
requires_revalidation true
live_conversion_allowed false
```

## SL7

```text
PaperBroker revalidates latest quote/tracking
expired intent blocks
latest quote missing blocks
exchange_write_used false
```
