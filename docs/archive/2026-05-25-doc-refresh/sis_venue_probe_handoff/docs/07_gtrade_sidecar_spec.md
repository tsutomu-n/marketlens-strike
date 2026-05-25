# 07. gTrade Sidecar Spec

## 目的

`@gainsnetwork/sdk` を使ってgTradeの `/trading-variables` を取得・正規化し、Python側へJSONLで渡す。

## 対象

```txt
SPY/USD = pairIndex 86
QQQ/USD = pairIndex 87
XAU/USD = pairIndex 90
```

## 入力

- backend URL: `https://backend-arbitrum.gains.trade`
- endpoint: `GET /trading-variables`
- SDK: `@gainsnetwork/sdk`

## 出力

```txt
data/raw/sidecar/gtrade/YYYY-MM-DD.jsonl
```

1行1snapshot。

## 出力schema

```json
{
  "ts_client": "2026-05-21T00:00:00.000Z",
  "venue": "gtrade",
  "backend": "https://backend-arbitrum.gains.trade",
  "pairs": [
    {
      "canonical_symbol": "QQQ",
      "venue_symbol": "QQQ/USD",
      "pair_index": 87,
      "spreadP_raw": "...",
      "fee_index": "...",
      "group_index": "...",
      "max_leverage": "...",
      "one_percent_depth_above_usd": null,
      "one_percent_depth_below_usd": null,
      "oi_long_usd": null,
      "oi_short_usd": null
    }
  ],
  "market_status": {
    "isForexOpen": true,
    "isStocksOpen": false,
    "isIndicesOpen": true,
    "isCommoditiesOpen": true
  },
  "raw_payload_sha256": "..."
}
```

## 実装手順

1. `npm install @gainsnetwork/sdk zod tsx typescript`
2. `fetch(backendUrl + '/trading-variables')`
3. `transformGlobalTradingVariables(payload)`
4. `globalTradingVariables.pairs[pairIndex]` で対象ペアを抽出
5. `pairInfos`, `collaterals`, `fees` からspread/fee/OI/depthを抽出
6. JSONLへemit

## 注意

- すべてのpairがすべてのchain/collateralで使えるわけではない
- `allTrades` は廃止予定・移行に注意
- SDK versionをlockする
- raw payload hashを必ず保存する
- Python側ではsidecar出力を信用しすぎず、schema validationする
