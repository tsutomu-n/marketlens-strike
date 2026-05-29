# 02 Target Architecture

## Target Flow

```text
Data Collection
  Trade[XYZ] quotes
  real_market bars/features
  tracking records
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

## Layer Responsibilities

### 1. Data Collection

責務:

```text
- Trade[XYZ] quote collection
- real_market collection
- tracking collection
- raw / normalized保存
```

責務外:

```text
- 戦略判断
- paper昇格
- live判断
```

### 2. DataSnapshotManifest

責務:

```text
- どのquote / feature / tracking / phase gateで研究したか固定
- データ範囲、symbol universe、hashを記録
```

### 3. FeatureSnapshotManifest

責務:

```text
- どのfeature configでfeatureを作ったか固定
- feature生成時点のリーク検査を可能にする
```

### 4. StrategyExperimentSpec

責務:

```text
- どの戦略仮説を、どのパラメータ、どのデータ、どの評価計画で試すか定義
```

### 5. StrategySignalArtifact

責務:

```text
- 戦略が出したsignalの正本
- signals.csvではなく parquet/jsonl
- execution_symbol / real_market_symbol を分離
```

### 6. EvaluationPlan / TrialLedger

責務:

```text
- split / purge / embargo / era_unit / cost stress を定義
- すべてのtrialを記録
- best resultだけを残さない
```

### 7. TradeCandidate

責務:

```text
- signalから作った取引候補
- まだpaper orderでもlive orderでもない
```

### 8. PaperCandidatePack

責務:

```text
- paperに進める候補束
- selected / rejected / blocked / no_signal を全部残す
```

### 9. PromotionDecision

責務:

```text
- 人間の昇格判断
- phase-gate-reviewやbot-previewをpaper承認扱いしない
```

### 10. PaperIntentPreview

責務:

```text
- paper用の仮注文意図
- requires_revalidation=true
- live変換禁止
```

### 11. PaperBroker

責務:

```text
- PaperIntentPreviewを最新quote / tracking / fee / session / riskで再検査
- paper order/fill/observationを生成
```

## Future Layers

後続で追加するが、最初のPRには入れない。

```text
- full RegimeGraph
- full CandidateResolver
- full neutralization / exposure engine
- full Deflated Sharpe / PBO
- LiveOrderIntentCandidate
- public micro live CLI
```
