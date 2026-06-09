<!--
作成日: 2026-05-30_11:09 JST
更新日: 2026-06-09_16:13 JST
-->

# Paper Promotion And Intent Spec

この文書は、Strategy Lab の候補を paper-only の仮注文意図へ進める時の仕様です。

## Promotion の基本原則

Promotion は「paper observation に進める人間判断」です。live trading 許可ではありません。

```text
PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents revalidation
```

## PaperCandidatePack

`PaperCandidatePack` は candidate の束です。

保持するもの:

- all candidates
- selected candidate IDs
- rejected candidate IDs
- selection policy
- reason codes
- block reasons
- evaluation / data / feature lineage

保持しないもの:

- live order
- wallet
- signing material
- exchange write permission
- profitability proof
- paper-ready proof
- live-ready proof

現行 validation:

- `selected_candidate_ids` と `rejected_candidate_ids` は `candidates` 内の ID だけを参照する。
- candidate ID、selected ID、rejected ID は重複できない。selected / rejected の同時指定も拒否される。
- selected candidate は `status="candidate"`、空の `block_reasons`、venue-suitable でなければならない。
- NDX/QQQ family の `trade_xyz` proxy は research/backtest artifact として残せるが、現行 paper candidate には選べない。

## PromotionDecision

`PromotionDecision` は `PaperIntentPreview` 生成前に必要な判断 artifact です。

decision:

- `promote`: selected candidate から paper intent preview を作ってよい。
- `hold`: まだ進めない。通常は evidence 不足、判断保留、観測待ち。
- `reject`: paper observation に進めない。

`promote` の最低条件:

- `required_evidence` がすべて `observed_evidence` に含まれる。
- `approval_reasons` が空ではない。
- `live_ready_claimed=false`。
- `wallet_used=false`。
- `exchange_write_used=false`。

`hold` / `reject` の最低条件:

- `rejection_reasons` が空ではない。

現行 CLI:

```bash
uv run sis promotion-decision --decision hold
uv run sis promotion-decision --decision reject
uv run sis promotion-decision --decision promote
```

注意:

- default は `hold`。
- `promote` は required evidence が揃っていないと model validation で止まる。

## PaperIntentPreview

`PaperIntentPreview` は paper runner へ渡す仮注文意図です。

必須の安全 guard:

```text
requires_revalidation=true
paper_only=true
live_conversion_allowed=false
live_order_submitted=false
wallet_used=false
exchange_write_used=false
```

venue suitability guard:

- `PaperIntentPreview` は `paper_intent` stage の suitability を model validation で再確認する。
- NDX/QQQ family の `trade_xyz` paper intent は `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION` で拒否される。
- NDX/QQQ family の `bitget_demo` paper intent は asset universe mismatch で拒否される。
- `bitget_futures` と `hyperliquid_perp` は current `VenueId` ではなく、この artifact schema にも入れない。

action:

- `enter`
- `exit`
- `reduce`
- `skip`

side:

- `long`
- `short`
- `none`

order style:

- `paper_taker`
- `paper_maker`
- `skip`

price reference:

- `best_bid`
- `best_ask`
- `mid`
- `mark`
- `oracle`

## PaperIntentPreview と live order の違い

| Aspect | PaperIntentPreview | Live order |
|---|---|---|
| destination | paper runner | exchange adapter |
| write permission | none | exchange write |
| wallet | never | required in live |
| signing | none | required in live |
| conversion | live conversion prohibited | n/a |
| revalidation | required | required but separate live path |
| artifact path | `data/bot/paper_intent_preview.json` | not implemented as Strategy Lab output |

`PaperIntentPreview` を `OrderIntent` と呼ばないでください。現行 Strategy Lab の名前は意図的に preview です。

## paper-from-intents

Command:

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

主な処理:

1. `PaperIntentPreview` を Pydantic model で検証する。
2. `data/normalized/quotes.parquet` から latest quote を読む。
3. `valid_until` が過ぎていれば block する。
4. latest quote が無ければ block する。
5. `DecisionContext` / `ExecutionPlan` へ paper runner 内部で bridge する。
6. `PaperBroker` で fee / halt policy / paper validation を通す。
7. paper order / fill / position を書く。
8. observation ledger に結果を書く。

block reason:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

NDX/QQQ family の raw JSON を直接 `--intents-path` に置いても、手順 1 の model validation で同じ venue suitability guard に掛かる。これは generated `PaperIntentPreview` を迂回した paper 実行を防ぐための境界です。

出力:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

## Internal legacy bridge

`paper-from-intents` の内部では `DecisionContext` と `ExecutionPlan` が使われます。これは paper runner の既存内部 bridge であり、Strategy Lab の現行設計正本ではありません。

設計上の正本:

- Strategy side: `StrategySignalRecord`, `TradeCandidate`, `PaperIntentPreview`
- Paper runner internal bridge: `DecisionContext`, `ExecutionPlan`

新しい Strategy Lab 文書や戦略設計では、`DecisionContext` / `ExecutionPlan` を入口にしないでください。

## Promotion review checklist

Promotion 前:

- `PaperCandidatePack` の selected / rejected ID が candidates 内に存在する。
- selected candidate は `status="candidate"`、`block_reasons` が空、venue-suitable である。
- `data_snapshot_id` と `feature_snapshot_id` が追える。
- `required_evidence` が明確。
- `approval_reasons` が人間レビューとして読める。

Preview 生成後:

- `PaperIntentPreview` の `valid_until` が短すぎず長すぎない。
- `requires_revalidation=true`。
- `paper_only=true`。
- `live_conversion_allowed=false`。
- `wallet_used=false`。
- `exchange_write_used=false`。
- paper observation ledger に live write が記録されていない。
