# 03. OSS / SDK Selection

## 採用スタック

| 分類 | 採用 | 目的 |
|---|---|---|
| gTrade | `@gainsnetwork/sdk` | tradingVariables正規化、fees、pair/collateral取得 |
| Ostium | `ostium-python-sdk` | feed, price, fee, OI cap, history取得 |
| Python package管理 | `uv` | Python環境固定 |
| CLI | `Typer` | コマンド実装 |
| 表示 | `Rich` | CLI table/report |
| ログ | `loguru` | 監査ログ |
| 型/設定 | `pydantic`, `pydantic-settings` | schema固定 |
| HTTP | `httpx` | REST取得 |
| WS | `websockets` | pricing/event stream取得 |
| カレンダー | `exchange_calendars` | XNYS session判定 |
| DataFrame | `Polars` | Parquet処理・集計 |
| DB | `DuckDB` | ad-hoc集計・report |
| 保存 | JSONL + Parquet | raw保存と正規化保存 |
| 研究価格 | `yfinance`, `yahooquery`, `pandas-datareader` | QQQ/SPY/GLD/VIX/金利取得 |

## Phase 1で使わないもの

| 候補 | 判断 | 理由 |
|---|---|---|
| OpenBB | Phase 2 | 強力だが初期MVPには重い |
| vectorbt | Phase 2補助 | venue-native executionを自前実装する必要がある |
| backtesting.py | Phase 2補助 | mark/index/session/cost/gap/liquidationを扱いにくい |
| ML系 | 不採用 | 目的から遠い |

## gTradeはTypeScript sidecarを使う

PythonでgTrade payloadを直接parseするより、`@gainsnetwork/sdk` を使うTypeScript sidecarで正規化し、Python側がJSONLを読む構成が近道。

```txt
TypeScript:
  - fetch /trading-variables
  - transformGlobalTradingVariables
  - pair/collateral/fee/spreadP抽出
  - JSONL出力

Python:
  - JSONL保存・検証
  - Parquet変換
  - DuckDB集計
  - Go/No-Go判定
  - Backtest bridge
```

## OstiumはPython SDKを使う

OstiumはPython SDKを使って以下をprobeする。

```txt
- feed / pair一覧
- latest price
- trading hours
- rolling / rollover fee
- OI caps
- opening fee
- position / order history schema
```

実注文は初期対象外。
