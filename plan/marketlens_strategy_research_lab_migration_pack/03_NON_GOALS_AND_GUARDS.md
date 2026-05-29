# 03 Non-Goals And Guards

## Non-Goals

今回の移行でやらないこと。

```text
- production live trading
- wallet / signing
- exchange write
- public micro live CLI
- Alpacaでの売買
- Lighter統合
- CEX統合
- HFT / MM / arbitrage
- 完全なML workflow engine化
- online learning
- full neutralization / MMC
- full DSR / PBO
```

## Hard Guards

全artifactで維持する。

```text
live_order_submitted=false
wallet_used=false
exchange_write_used=false
paper_ready_claimed=false  # PromotionDecisionまで原則false
live_ready_claimed=false
```

## Naming Guards

禁止:

```text
OrderIntent
order_intents_preview.json
```

使用:

```text
PaperIntentPreview
paper_intent_preview.json
```

## Surface Guards

```text
bot-preview:
- HOLD専用
- 注文候補生成をしない

strategy-preview:
- 戦略候補を観察する

build-paper-candidate-pack:
- paper候補束を作る

build-paper-intent-preview:
- paper専用intent previewを作る

paper-from-intents:
- paper実行用
```

## Claim Guards

以下は初期PRでは常にfalse。

```text
profitability_claimed
paper_ready_claimed
tiny_live_ready_claimed
live_ready_claimed
```

trueにできるのはPromotionDecision以降。ただしlive_readyはproduction live validationまで禁止。

## Data Guards

```text
- DataSnapshotManifestなしのtrialは禁止
- FeatureSnapshotManifestなしのtrialは少なくともwarning
- strategy signalは strategy_signals.parquet/jsonl を正本にする
- signals.csvはlegacy export
- feature_ts > signal_ts はfail
- quote_ts > signal_ts はfail
- purge_minutes / embargo_minutes 未設定はfail
```
