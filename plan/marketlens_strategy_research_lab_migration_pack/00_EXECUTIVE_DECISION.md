# 00 Executive Decision

## 結論

`marketlens-strike` は、Trade[XYZ] read-only / paper 前段基盤としては十分進んでいる。次に行うべきことは live 化ではなく、戦略研究・候補生成・評価・paper昇格の責務を分離する **Strategy Research Lab** 化である。

## 採用方針

```text
採用:
- Strategy Research Lab
- StrategyExperimentSpec
- SymbolBinding
- DataSnapshotManifest
- FeatureSnapshotManifest
- StrategySignalArtifact
- EvaluationPlan
- TrialLedger
- LeakageCheckReport
- TradeCandidate
- PaperCandidatePack
- PromotionDecision
- PaperIntentPreview

後回し:
- full RegimeGraph
- full CandidateResolver
- full neutralization / MMC
- full Deflated Sharpe / PBO
- LiveOrderIntentCandidate
- public micro live CLI
- wallet / signing
```

## なぜ Strategy Lab ではなく Strategy Research Lab か

単に戦略を複数扱えるようにするだけでは足りない。複雑戦略・動的戦略・多数の試行を扱うと、最大リスクは「実装できないこと」ではなく、以下である。

```text
- 古いdataと新しいfeatureを混ぜる
- feature作成時点で未来情報が入る
- 試行回数を隠してbest resultだけ採用する
- paper-ready / live-ready を過剰主張する
- execution symbol と real market symbol を混同する
- strategy候補とpaper intentとlive orderを混同する
```

したがって、戦略ランタイムより先に、研究の再現性・データ由来・試行管理・claim guard を入れる。

## なぜ signals.csv を正本から降ろすか

`signals.csv` は薄すぎる。

不足:

```text
- strategy_id
- strategy_family
- strategy_version
- trial_id
- parameter_hash
- execution_symbol
- real_market_symbol
- feature refs
- quote refs
- tracking refs
- rank_score / tail_bucket
- block_reasons
- source_confidence / venue_quality_score
```

したがって、正本を以下へ移行する。

```text
data/research/strategy_signals.parquet
data/research/strategy_signals.jsonl
```

`signals.csv` は移行期間の legacy export とする。

## なぜ bot-preview をHOLD専用に残すか

`bot-preview` は安全surfaceであり、注文候補生成Botではない。

```text
bot-preview:
- HOLD専用
- walletなし
- signingなし
- exchange writeなし

strategy-preview:
- 戦略候補観察

build-paper-candidate-pack:
- paper候補束生成

build-paper-intent-preview:
- paper専用intent生成
```

`bot-preview` に戦略・paper intentを混ぜると、オペレーターが「Botが注文判断を始めた」と誤読する。

## なぜ PaperIntentPreview と呼ぶか

`OrderIntent` という名前は禁止する。理由は、execution側のlive注文意図と混同しやすいため。

使う:

```text
PaperIntentPreview
```

使わない:

```text
OrderIntent
order_intents_preview.json
```

## 破壊的変更の判断

現Repoはまだproduction live tradingに進んでいない。今なら互換性を捨てて正しい中間表現へ移行できる。

最初に壊すべきもの:

```text
- signals.csv 正本扱い
- ResearchSignalStrategy を本物の戦略エンジン扱いすること
- backtest bridge の next_row exit 固定
```

残すべきもの:

```text
- Trade[XYZ] collector / diagnostics / strict validation
- real_market layer
- tracking layer
- PaperBroker / paper reports
- phase-gate-review
- micro live safety code surface
- operations / audit / remediation chain
```
