# 00. Executive Brief

## 結論

目的達成の最短ルートは、売買Botではなく `sis-venue-probe` を作ること。

```txt
Ostium / gTrade
×
QQQ・SPY・XAU
×
4時間〜3日スイング
×
短期スキャルピング禁止
×
Go/No-Go判定
```

## 採用方針

### gTrade

先に実装する。理由は以下。

- 公式Pair Listで対象ペアが確定している
  - `SPY/USD = pairIndex 86`
  - `QQQ/USD = pairIndex 87`
  - `XAU/USD = pairIndex 90`
- `@gainsnetwork/sdk` がある
- backend `/trading-variables` がある
- mark price / index price の意味が公式に分かれている
- `isIndicesOpen`, `isCommoditiesOpen` などの市場状態を取得できる

### Ostium

本命候補だが、gTradeの後にprobeする。理由は以下。

- RWA Perpとして目的に近い
- Python SDKがある
- latest price / trading hours / feeds / fee / OI caps を扱える可能性がある
- ただし、現行symbol、per-symbol fee、liquidation reference、bid/ask取得方法に未確定項目が残る

## 作るもの

```txt
sis-venue-probe
  - instrument registry generator
  - quote logger
  - cost matrix builder
  - scalping policy checker
  - trading halt checker
  - go/no-go report generator
  - backtest bridge input generator
```

## 作らないもの

```txt
- 実注文Bot
- 短期スキャルピングBot
- 高レバBot
- 個別株Bot
- ニュースLLM売買Bot
- SNS解析
```

## 実装優先順位

1. TypeScript: `@gainsnetwork/sdk` でgTrade `trading-variables` を取得・正規化
2. Python: 正規化JSONLを保存・Parquet化・DuckDB登録
3. Python: scalping policy / halt policy / cost matrix
4. Python: Go/No-Go report
5. Python: Ostium SDK probe
6. Python: backtest bridge
