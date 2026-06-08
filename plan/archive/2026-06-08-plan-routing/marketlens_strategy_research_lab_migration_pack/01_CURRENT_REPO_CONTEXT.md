# 01 Current Repo Context

## 現在地

現在の `marketlens-strike` は、以下を完了済みとみなす。

```text
- Python 3.13 runtime
- legacy gTrade / Ostium archive化
- Trade[XYZ] registry builder
- Trade[XYZ] HIP-3 asset_id解決
- Trade[XYZ] quote collector
- quote normalizer
- quote diagnostics
- strict artifact validation
- phase-gate-review read-only cutover
- Alpaca provider
- real_market feature builder
- tracking layer
- venue-gated paper基盤
- micro live safety code surface
```

## 現在の正しい読み方

```text
read-only / paper前段:
- GO / 実装済み

production live trading:
- 未完了

wallet / signing:
- 未完了

public micro live CLI:
- 未公開

正式な注文候補生成surface:
- 未完成
```

## 採用して残すもの

```text
src/sis/venues/trade_xyz/
src/sis/real_market/
src/sis/tracking/
src/sis/paper/
src/sis/reports/
src/sis/ops/
src/sis/execution/  # safety surface only
configs/fee_model.trade_xyz.yaml
configs/halt_policy.yaml
schemas/quote_log_v2.schema.json
```

## 壊してよいもの

```text
src/sis/backtest/signals.py の正本扱い
src/sis/core/strategy.py の ResearchSignalStrategy中心設計
src/sis/core/execution_plan.py の汎用中間表現扱い
signals.csv をpaper主入力にすること
build-signals の単一戦略固定
```

## 既存導線

現在は概ね次の導線で動く。

```text
Trade[XYZ] quote collection
  ↓
normalize / strict validation
  ↓
real_market features
  ↓
tracking
  ↓
research signals.csv
  ↓
DecisionContext
  ↓
ResearchSignalStrategy
  ↓
RiskGate
  ↓
ExecutionPlan
  ↓
paper / ops
  ↓
micro live safety tests
```

今後はこう変える。

```text
Trade[XYZ] / real_market / tracking
  ↓
DataSnapshotManifest
  ↓
FeatureSnapshotManifest
  ↓
StrategyExperimentSpec
  ↓
StrategySignalArtifact
  ↓
EvaluationPlan / TrialLedger
  ↓
TradeCandidate
  ↓
PaperCandidatePack
  ↓
PromotionDecision
  ↓
PaperIntentPreview
  ↓
PaperBroker
```

## 開発者が混同しやすいこと

```text
READ_ONLY_GO != production live ready
phase2_entry_allowed != micro live allowed
bot-preview != order generation bot
PaperCandidatePack != paper order
PaperIntentPreview != live order
signals.csv != strategy signal source of truth
```
