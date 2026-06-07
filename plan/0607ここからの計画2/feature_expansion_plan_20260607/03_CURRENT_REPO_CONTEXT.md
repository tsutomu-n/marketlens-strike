<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 03 Current Repo Context

## 参照したRepo前提

この計画は、`marketlens-strike` の現在構造に合わせる。

重要な現行境界:

```text
- 現在の開発主軸は backtest-first / venue-neutral。
- Trade[XYZ] は実装済み主要venueだが、当面の注文口主軸ではない。
- Strategy Lab は研究、候補生成、評価、paper昇格判断までの surface。
- live order surface ではない。
- data/research/strategy_signals.parquet が Strategy Lab の canonical signal artifact。
- data/research/signals.csv は legacy export。
- PaperIntentPreview は paper-only。
- wallet / signing / exchange write / production live trading は範囲外。
```

## 既存Strategy Lab artifact chain

既存の後段はすでにある。

```text
StrategyExperimentSpec
  -> StrategySignalRecord rows in data/research/strategy_signals.parquet
  -> StrategySignalManifest
  -> EvaluationPlan
  -> TrialRecord / TrialLedger
  -> TradeCandidate
  -> PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents revalidation
  -> paper orders/fills/positions only
```

今回の2.2実装は、このchainの前段に置く。

```text
Research Hypothesis Intake
  -> Seed Registry
  -> Variable Inventory
  -> Causal Roles
  -> Temporal Availability
  -> Core DAG
  -> later: StrategyExperimentSpec reference
```

今回のPhaseでは StrategyExperimentSpec へもまだ接続しない。

## 既存ファイルで参照するもの

実装者は次を読む。

```text
AGENTS.md
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md
docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md
src/sis/commands/research.py
src/sis/research/strategy_lab/
src/sis/research_protocol/
schemas/strategy_signal.v1.schema.json
schemas/data_snapshot_manifest.v1.schema.json
schemas/feature_snapshot_manifest.v1.schema.json
scripts/check_current_docs.py
```

## 既存設計との接続方針

```text
2.2 artifact:
  Strategy Labより前に置く。

DAG id:
  将来 StrategyExperimentSpec / TrialRecord / reports から参照できるようにする。

JSON Schema:
  既存方針に合わせ、薄いinteroperability guardとする。

Pydantic model:
  詳細validationの正本にする。

CLI:
  既存の src/sis/commands/research.py に最小追加する。
  ただしPhase AはCLIなしでよい。
```

## 実装上の注意

```text
- data/ は runtime/generated state。計画やテストで必要な出力は生成物として扱う。
- docs を追加する場合は東京時間metadata headerを付ける。
- New / heavily edited Python files は 800 lines以下にする。
- 既存 Strategy Lab の paper/live guardを緩めない。
- signals.csv を正本にしない。
```
