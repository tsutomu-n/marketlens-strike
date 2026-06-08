# PR-MLS-SL0 Strategy Research Lab Foundation

## Goal

Strategy Research Labの型と安全境界を作る。既存runtime挙動は変えない。

## Files To Add

```text
src/sis/research/strategy_lab/__init__.py
src/sis/research/strategy_lab/specs.py
src/sis/research/strategy_lab/signal_registry.py
src/sis/research/strategy_lab/signal_frame.py
src/sis/research/strategy_lab/run_profile.py
src/sis/research/strategy_lab/reports.py

src/sis/research_protocol/__init__.py
src/sis/research_protocol/data_snapshot.py
src/sis/research_protocol/feature_snapshot.py
src/sis/research_protocol/leakage.py
```

## Models

Implement:

```text
SymbolBinding
StrategyExperimentSpec
StrategyRunProfile
DataSnapshotManifest
FeatureSnapshotManifest
StrategySignalRecord
LeakageCheckReport
```

## Guards

```text
- live claims are forbidden
- exchange_write_allowed=false for strategy_lab profile
- wallet_required=false
- execution_symbol and real_market_symbol required
```

## Tests

```text
tests/test_strategy_lab_specs.py
tests/test_strategy_lab_signal_registry.py
tests/test_strategy_run_profile.py
tests/test_data_snapshot_manifest.py
tests/test_feature_snapshot_manifest.py
```

## Done

```text
- models validate
- strategy run profile rejects live claims
- unknown signal generator fails closed
- ./scripts/check pass
- existing bot-preview output unchanged
```
