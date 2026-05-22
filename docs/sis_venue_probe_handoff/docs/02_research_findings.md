# 02. Research Findings

## gTrade

### Pair mapping

公式Pair Listで以下を確認済み。

```txt
SPY/USD = pairIndex 86
QQQ/USD = pairIndex 87
XAU/USD = pairIndex 90
```

注意:

- pairIndexはコントラクト直接操作時に有用
- すべてのpairがすべてのchain/collateralで使えるわけではない
- feed anomalyやunderlying eventなどで一時的にdisableされる可能性がある

### Backend / SDK

gTrade backendは以下の形式。

```txt
backend-<network>.gains.trade
例: https://backend-arbitrum.gains.trade
```

主要endpoint:

```txt
GET /trading-variables
GET /open-trades
GET /open-trades/<address>
GET /user-trading-variables/<address>
GET /personal-trading-history-table/<address>
GET /trading-history-24h
```

`@gainsnetwork/sdk` には `transformGlobalTradingVariables` があり、`/trading-variables` のpayloadをSDK形式へ変換できる。

### Price semantics

gTradeはmarkとindexを分ける。

```txt
mark price:
  - execution
  - TP/SL
  - limit/stop
  - PnL

index price:
  - liquidation
```

### Session

Indices:

```txt
Mon-Fri 09:30-16:00 ET
閉場中はopen/close/edit不可
ポジションは残る
ギャップでstop lossが保証されず、清算リスクがある
```

XAU/commodities:

```txt
Sunday 18:00 ET open
Mon-Thuは17:00-18:00 ET maintenance break
Friday 17:00 ET close
```

### Cost

公式仕様として初期モデルに入れる値:

```txt
SPY/QQQ:
  open_fee = 0.05% = 5 bps
  close_fee = 0.05% = 5 bps
  spread = live probe from spreadP

XAU:
  open_fee = 5 bps
  close_fee = 5 bps
  fixed_spread = 0.01% = 1 bp
  holding/borrowing = live probe
```

## Ostium

### SDK/API

Ostium Python SDKは以下の用途に使える。

- feed一覧取得
- latest price取得
- Trade/Order作成
- 部分決済
- TP/SL設定
- open trades / orders / order history取得
- funding/rollover fee計算
- OI caps取得

### RWA oracle

OstiumはRWA向けに、以下を価格レポートmetadataとして扱う設計。

- market hours
- bid/ask
- order book depth
- market open gap

### Dynamic spread

Ostiumにはdynamic spreadの考え方がある。短期の一方向フロー、薄い市場、サイズによる実行コスト変化を考慮する必要がある。

### 未確定項目

Ostiumは以下を実API/SDK probeで確定する。

```txt
- US500/SPX相当の現行symbol
- NDX/Nasdaq相当の現行symbol
- XAU/Gold相当の現行symbol
- per-symbol opening fee
- bid/ask取得可否
- dynamic spread対象有無
- liquidation reference price
- close during market closed の可否
```

## 参考URL

- gTrade Pair List: https://docs.gains.trade/gtrade-leveraged-trading/pair-list
- gTrade Backend: https://docs.gains.trade/developer/integrators/backend
- gTrade Mark + Index: https://docs.gains.trade/developer/integrators/guides/mark-+-index-introduction
- gTrade Fees & Spread: https://docs.gains.trade/gtrade-leveraged-trading/fees-and-spread
- gTrade Indices: https://docs.gains.trade/gtrade-leveraged-trading/asset-classes/indices
- gTrade Commodities: https://docs.gains.trade/gtrade-leveraged-trading/asset-classes/commodities
- Gains SDK: https://github.com/GainsNetwork-org/sdk
- Ostium API & SDK: https://ostium-labs.gitbook.io/ostium-docs/developer/api-and-sdk
- Ostium Price Oracle: https://ostium-labs.gitbook.io/ostium-docs/supporting-infrastructure/price-oracle
- Ostium Dynamic Spreads: https://www.ostium.com/blog/dynamic-spreads
- Ostium Python SDK: https://github.com/0xOstium/ostium-python-sdk
