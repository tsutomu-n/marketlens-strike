# 07 Implementation Roadmap

## PR-MLS-SL0 Strategy Research Lab Foundation

作るもの:

```text
src/sis/research/strategy_lab/
  __init__.py
  specs.py
  signal_registry.py
  signal_frame.py
  run_profile.py
  reports.py

src/sis/research_protocol/
  data_snapshot.py
  feature_snapshot.py
  leakage.py
```

目的:

```text
- StrategyExperimentSpec
- SymbolBinding
- StrategyRunProfile
- DataSnapshotManifest
- FeatureSnapshotManifest
- StrategySignalRecord
```

## PR-MLS-SL1 Strategy Signals Artifact

作るもの:

```text
strategy_signals.parquet
strategy_signals.jsonl
signals.csv legacy export
SignalGeneratorRegistry
```

変更:

```text
build-signalsを複数strategy対応
qqq_trend_rates_vixをregistry化
execution_symbol / real_market_symbol分離
```

## PR-MLS-SL2 EvaluationPlan + TrialLedger

作るもの:

```text
EvaluationPlan
TrialRecord
TrialLedger
LeakageCheckReport
EvaluationRunner
```

出力:

```text
data/research/trial_ledger.jsonl
data/reports/strategy_trial_report.md
```

## PR-MLS-SL3 Backtest Bridge Fixed Horizon

追加:

```text
exit_model:
- next_row
- fixed_horizon
```

## PR-MLS-SL4 TradeCandidate + PaperCandidatePack

追加:

```text
TradeCandidate
PaperCandidatePack
selected / rejected / no_signal / blocked preservation
rank_score / tail_bucket
claim flags
```

## PR-MLS-SL5 PromotionDecision

追加:

```text
PromotionDecision
human approval artifact
paper昇格前の承認
```

## PR-MLS-SL6 PaperIntentPreview

追加:

```text
PaperIntentPreview
valid_until
source refs
requires_revalidation
paper_only
```

## PR-MLS-SL7 paper-from-intents

追加:

```text
paper-from-intents CLI
PaperBroker revalidation
PaperObservationLedger
```

## PR-MLS-SL8 Legacy Signals Retirement

移行:

```text
ResearchSignalStrategy legacy化
signals.csv active path削除
paper pathをpaper_intent_previewへ移行
```

## 実装順の理由

```text
1. 型とmanifestを先に作る
2. signal artifact正本を作る
3. 評価とtrial記録を作る
4. backtestのexitだけ最小拡張する
5. candidateとpaper候補束を作る
6. promotion decisionで人間判断を入れる
7. paper intentへ進む
8. 最後に旧pathを落とす
```
