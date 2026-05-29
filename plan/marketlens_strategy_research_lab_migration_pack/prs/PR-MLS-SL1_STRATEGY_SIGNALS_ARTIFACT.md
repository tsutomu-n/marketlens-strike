# PR-MLS-SL1 Strategy Signals Artifact

## Goal

`signals.csv`を正本から降ろし、`strategy_signals.parquet/jsonl`を正本にする。

## Files To Change

```text
src/sis/research/signal_builder.py
src/sis/commands/research.py
src/sis/research/strategy_lab/signal_registry.py
src/sis/research/strategy_lab/signal_frame.py
```

## Required Behavior

```text
- build-signals は複数strategy対応
- qqq_trend_rates_vix はgenerator registryの1要素
- strategy_signals.parquet/jsonlを出す
- signals.csvはlegacy export
- execution_symbol / real_market_symbolを必須にする
```

## Artifacts

```text
data/research/strategy_signals.parquet
data/research/strategy_signals.jsonl
data/research/signals.csv  # legacy export only
data/reports/strategy_signals_preview.md
```

## Tests

```text
- build_signals writes strategy_signals parquet/jsonl
- signals.csv is marked legacy export
- XYZ100 uses real_market_symbol QQQ through SymbolBinding
- missing SymbolBinding fails
```

## Done

```text
uv run sis build-signals
uv run pytest tests/test_strategy_lab_signal_registry.py tests/test_research_signals_artifact.py -q
```
