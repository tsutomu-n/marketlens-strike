# Research Data Strategy

## Purpose

この文書は、Phase 2 Research Layer で使う research data provider、fallback、artifact contract、stop condition を定義する。

## Separation Of Concerns

Research Layer では、次の 2 種類の価格を混同しない。

1. research price
2. venue execution price

research price は signal / feature 生成用である。  
venue execution price は backtest / paper / live の execution 近似用である。

`yfinance` や `yahooquery` は research price 用であり、venue execution price の代替ではない。

## Provider Policy

### Market Data

- primary: `yfinance`
- fallback: `yahooquery`

対象の初期 universe:

- `QQQ`
- `SPY`
- `GLD`
- `^VIX`
- `UUP`
- `USDJPY=X`
- `EURUSD=X`

### Macro Data

- primary: `fredapi`
- fallback: `pandas-datareader`

対象の初期 series:

- `DGS10`
- `DGS2`
- `T10Y2Y`
- `FEDFUNDS`

### Event Data

- initial mode: CSV first
- future optional mode: external calendar provider

初期段階では、event calendar は人間が管理する CSV を正本とする。

## Artifact Policy

最低限生成すべき artifact は次のとおり。

- `data/research/market_panel.parquet`
- `data/research/macro_panel.parquet`
- `data/research/event_calendar.parquet`
- `data/research/feature_panel.parquet`
- `data/research/signals.csv`
- `data/research/research_quality_report.json`

## Polars First

Phase 2 は `Polars first` で進める。

- in-memory transform は `polars.DataFrame`
- persisted artifact は `parquet` または `csv`
- pandas は provider bridge が必要な箇所に限定する

## Fallback Rules

### Market Provider Fallback

- `yfinance` 取得失敗時のみ `yahooquery` を使う
- primary が成功しているのに fallback を混在させない
- provider 名は artifact に残す

### Macro Provider Fallback

- `fredapi` 取得失敗時のみ `pandas-datareader` を使う
- provider 名は artifact に残す
- release / vintage の扱いは report に明記する

## Fail-Closed Rules

次の場合、Research Layer は fail-closed で止める。

- required columns が不足している
- timestamp / date parse に失敗する
- symbol coverage が空になる
- event calendar の必須列が欠ける
- signals.csv が再現生成できない

## Research Quality Checks

最低限、次を report で確認可能にする。

- missing rate
- duplicate rows
- date / time range
- symbol coverage
- macro series coverage
- signal timeframe coverage
- future leak review point

## Timezone Rules

- persisted market timestamps は UTC
- event timestamps は UTC
- macro series は `date` 粒度で扱う
- JST / ET は運用 docs で補足しても、artifact の正本は UTC / date に固定する

## Future Leak Policy

Phase 2 の時点では、future leak を完全自動防止できなくてもよい。  
ただし、少なくとも review point を report に残し、release timing や event timing を曖昧なまま silent に通さない。

## Non-Goals

この段階では次を目的にしない。

- venue-native execution price estimation
- order routing
- live order automation
- paper trading state management
- optimized strategy search
