# marketlens_strategy_research_lab_migration_pack

この資料パックは、`marketlens-strike` を **Trade[XYZ] read-only / paper 前段基盤** から、戦略研究・候補生成・評価・paper昇格に強い **Strategy Research Lab** 構造へ移行するための実装契約です。

このパックは「思想メモ」ではありません。Repo担当者が、PRごとに、どのファイルを、どの順番で、どのDone条件で、何を禁止して実装するかを迷わないための資料です。

## 最重要方針

```text
今回の目的は live Bot 化ではない。
今回の目的は Strategy Research Lab 化である。

production live trading / wallet / signing / public micro live CLI は対象外。
既存Repoには破壊的変更を加えてよい。
互換性維持より、今後の戦略研究・評価・改善容易性を優先する。
```

## 採用する最終構造

```text
Strategy Research Lab
  ↓
DataSnapshotManifest
  ↓
FeatureSnapshotManifest
  ↓
StrategyExperimentSpec
  ↓
StrategySignalArtifact
  ↓
EvaluationPlan
  ↓
TrialLedger
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
  ↓
PaperObservationLedger
```

## まず読む順番

```text
1. 00_EXECUTIVE_DECISION.md
2. 01_CURRENT_REPO_CONTEXT.md
3. 02_TARGET_ARCHITECTURE.md
4. 03_NON_GOALS_AND_GUARDS.md
5. 04_TERMS_AND_BOUNDARIES.md
6. 05_SYMBOL_BINDING_CONTRACT.md
7. 06_SCHEMA_CONTRACTS.md
8. 07_IMPLEMENTATION_ROADMAP.md
9. prs/PR-MLS-SL0_STRATEGY_RESEARCH_LAB_FOUNDATION.md
```

## PR順

```text
PR-MLS-SL0 Strategy Research Lab foundation
PR-MLS-SL1 Strategy signals artifact
PR-MLS-SL2 EvaluationPlan + TrialLedger
PR-MLS-SL3 Backtest bridge fixed_horizon exit
PR-MLS-SL4 TradeCandidate + PaperCandidatePack
PR-MLS-SL5 PromotionDecision
PR-MLS-SL6 PaperIntentPreview
PR-MLS-SL7 paper-from-intents
PR-MLS-SL8 legacy signals retirement
```

## 禁止事項

```text
- production live trading を実装しない
- wallet / signing を実装しない
- public micro live CLI を出さない
- PaperIntentPreview を live order に変換しない
- OrderIntent という名前を research/paper preview 層で使わない
- bot-preview を戦略実行Botに変えない
- signals.csv を正本にしない
- QQQ signal を SymbolBinding なしで XYZ100 に流さない
- TrialLedger なしに最良結果だけ採用しない
- phase-gate-review / bot-preview を paper/live承認扱いしない
```

## 最初の実装PRのDone条件

```text
- StrategyExperimentSpec を読み込める
- SymbolBinding を検証できる
- StrategyRunProfile で live claims を禁止できる
- DataSnapshotManifest / FeatureSnapshotManifest の型がある
- StrategySignalRecord の型がある
- 既存 bot-preview のHOLD挙動は変えない
- ./scripts/check がpass
```
