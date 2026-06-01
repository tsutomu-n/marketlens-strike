結論：**ある。ただし「GitHub OSSだけで実データ問題が解決する」わけではない。Repoで使うなら、主役は `hyperliquid-python-sdk` ではなく、今ある `TradeXyzClient` を維持しつつ、補助として `dlt` / `ccxt` / `alpaca-py` / 必要なら `databento-python` を段階導入するのが現実的です。**

## 主案

### Goal

`marketlens-strike` の実データ収集で必要なのは、単に価格を取ることではなく、次の流れを壊さないことです。

```text
raw payload
→ normalized quotes.parquet
→ schema / manifest / coverage / readiness
→ backtest smoke
→ 実務BT判定
```

現行Repoはすでに `httpx`, `polars`, `duckdb`, `pyarrow`, `yfinance`, `yahooquery`, `fredapi`, `pandas-datareader` を持っています。つまり、最低限のHTTP取得・Parquet化・DuckDB処理・無料系real market reference取得の土台はあります。

また、現行の `TradeXyzClient` は `https://api.hyperliquid.xyz` を直接叩き、`allMids`, `metaAndAssetCtxs`, `l2Book`, `fundingHistory`, `userFees`, `candleSnapshot` まで持っています。   

なので、**いきなり大きなOSSに置き換えるべきではありません。**

主案はこれです。

```text
1. Trade[XYZ] venue canonical:
   既存 TradeXyzClient を維持

2. Venue API互換・追加確認:
   hyperliquid-python-sdk を参考実装 / regression oracle として使う

3. 外部価格・クロスチェック:
   ccxt を secondary source として使う

4. real market reference:
   まず既存 yfinance / yahooquery / Alpaca provider を使う
   必要なら alpaca-py を正式SDKとして採用

5. ETL / staging:
   dlt を optional integration として使う

6. 有料・高品質 historical:
   必要なら databento-python / Massive client を sidecar provider として使う
```

## 候補OSS

### 1. `hyperliquid-dex/hyperliquid-python-sdk`

**用途:** Trade[XYZ] / Hyperliquid系APIの公式SDK参照。
**採用判断:** 直接依存にするより、まずは adapter比較・payload差分検証に使うのがよいです。

このSDKは Hyperliquid API trading 用のPython SDKで、README上も `Info` を使ったユーザー状態取得例があります。([GitHub][1])
ただし、あなたのRepoにはすでに `TradeXyzClient` があり、必要なread-only endpointの多くは実装済みです。置き換えると、既存の `raw_payload_ref`、schema、manifest、readinessとの接続を壊す可能性があります。

**Repoでの使い方:**

```text
src/sis/integrations/hyperliquid_sdk_probe/
```

に限定し、同じsymbol・同じ時刻で、既存clientとSDKのresponse差分を記録する。

**メリット:**

```text
API仕様変更の検知
payload解釈ミスの検出
既存clientのregression test補助
```

**注意:** canonical collectorにはしない。canonicalは今の `TradeXyzClient` のまま。

---

### 2. `ccxt/ccxt`

**用途:** 外部取引所・Hyperliquid互換データのクロスチェック。
**採用判断:** secondary sourceとして有用。canonicalにはしない。

CCXTは100以上の暗号資産取引所に接続でき、market dataの保存・分析・backtest用途へのアクセスを提供すると説明されています。([GitHub][2])
GitHub上の対応一覧には `hyperliquid` が含まれています。([GitHub][2])
また、READMEには `fetchOHLCV` や `fetchOrderBook`, `fetchTicker` の例もあります。([GitHub][2])

**Repoでの使い方:**

```text
src/sis/integrations/ccxt_reference/
  collect_ccxt_ohlcv.py
  collect_ccxt_orderbook_snapshot.py
  compare_with_trade_xyz_quotes.py
```

**取るデータ:**

```text
OHLCV
ticker
orderbook top-of-book
trades if available
```

**メリット:**

```text
Trade[XYZ] quoteが異常なときの外部比較
価格乖離・stale検知
同一symbol相当のsanity check
```

**弱点:**

```text
HIP-3固有の fee_mode / oracle provenance / oi_cap / discovery_bound までは期待しない
raw payloadの意味がRepo現行schemaと一致しない
CCXT経由データを実務BTのcanonicalにすると監査性が下がる
```

**結論:** `ccxt` は **検証用・比較用**。`data/raw/quotes/trade_xyz/` に混ぜない。別pathに置く。

```text
data/external/ccxt/
```

---

### 3. `dlt-hub/dlt`

**用途:** 実データ収集後のstaging、schema drift検知、DuckDB/Parquet投入。
**採用判断:** かなり相性がよい。直接sourceではなく、ETL層に使う。

`dlt` はオープンソースのPython data loading libraryで、REST API、SQL、cloud storage、Python data structuresなどから抽出し、schema inference、normalization、incremental loading、schema/data contractsを扱えると説明されています。Python 3.9〜3.14対応とも記載されています。([GitHub][3])

現行RepoはPython 3.13で、DuckDB / PyArrow / Polarsを使っています。
そのため、`dlt` はRepoの思想に合います。

**Repoでの使い方:**

```text
src/sis/integrations/dlt_staging/
  pipeline.py
  sources/
    trade_xyz_raw_jsonl.py
    ccxt_reference.py
    alpaca_reference.py
```

**置き場所:**

```text
data/staging/dlt/
data/external/*
```

**メリット:**

```text
rawからstagingへの再現性
incremental cursor管理
schema driftの検出
DuckDB出力との相性
```

**注意:** 既存の `normalize_quotes()` を置き換えない。まずは外部データ・補助データ用。

---

### 4. `alpacahq/alpaca-py`

**用途:** real market reference。AAPL, NVDA, SPY/QQQ相当などの株式・ETF参照価格。
**採用判断:** 既存Alpaca providerを強くするなら候補。

`alpaca-py` は Alpaca API の公式Python SDKで、REST / WebSocket / SSE endpointsを通じてmarket data streamや投資アプリ構築に使えると説明されています。Market Data APIでは live / historical data for stocks, crypto, options にアクセスできると記載されています。([GitHub][4])

現行RepoはすでにAlpaca providerを持つ前提で、`pyproject.toml` には `yfinance`, `yahooquery`, `fredapi`, `pandas-datareader` も入っています。
したがって、Alpacaは「無料系が欠損したときの正式reference provider」として使うのが妥当です。

**Repoでの使い方:**

```text
src/sis/real_market/providers/alpaca_official.py
```

**取るデータ:**

```text
stock bars
ETF bars
crypto bars if needed
latest quote / latest trade if plan allows
```

**メリット:**

```text
real_market_reference fail の解消候補
yfinance欠損時の代替
公式SDKなので保守しやすい
```

**注意:** API key、plan、取得可能範囲、再配布条件を確認する。GitHub OSSはclientであって、データ権利そのものではありません。

---

### 5. `databento/databento-python`

**用途:** 有料でもよい場合の高品質historical market data。
**採用判断:** 「30日待たずに実務BT用の参照データが必要」なら現実的候補。ただしTrade[XYZ] venueそのものの代替ではない。

Databento公式Python clientは live / historical data、MBO、MBP、top of book、OHLCV、last saleなど複数schema、normalized schema、point-in-time instrument definitions、market replay、batch downloadを提供すると説明されています。([GitHub][5])
API keyが必要とも記載されています。([GitHub][5])

**Repoでの使い方:**

```text
src/sis/real_market/providers/databento.py
```

**用途:**

```text
米国株・ETF・先物などの参照価格
SP500 / NASDAQ / related futures reference
execution-independent benchmark
```

**メリット:**

```text
historical coverageを短縮できる
point-in-time定義が強い
高頻度・order book系に拡張できる
```

**弱点:**

```text
有料・API key前提
Trade[XYZ]固有のoracle / fee / funding / OI capは埋まらない
データライセンス管理が必要
```

---

### 6. `massive-com/client-python` formerly Polygon.io

**用途:** 株式・ETF・指数系reference。
**採用判断:** Alpacaで足りなければ候補。

Massive.com、旧Polygon.ioのPython clientは REST / WebSocket API 用の公式clientで、Python 3.9以上、free tierには制限があり、大きいデータ要件ではsubscription plan確認が推奨されています。([GitHub][6])

**Repoでの使い方:**

```text
src/sis/real_market/providers/massive.py
```

**メリット:**

```text
AAPL / NVDA / MSFT / SPY / QQQ 相当のreference取得
REST + WebSocket
historical bars
```

**注意:** こちらもclientはOSSでも、データ利用はplan・規約・rate limit次第。

---

### 7. `OpenBB-finance/OpenBB`

**用途:** exploratory research / reference source aggregation。
**採用判断:** core dependencyにはしない。sidecarなら可。

OpenBBは、proprietary / licensed / public data sourcesを統合し、Python、Workspace、Excel、MCP、REST APIなどへ出すOpen Data Platformと説明されています。([GitHub][7])
一方で、READMEには AGPLv3 license と、データの正確性を保証しない旨のdisclaimerがあります。([GitHub][7])
また、Workspace連携説明では Python 3.9.21〜3.12 環境が前提と記載されています。([GitHub][7])

現行RepoはPython 3.13固定です。
したがって、OpenBBを本体依存に入れるのは避けた方がよいです。

**使うなら:**

```text
tools/openbb_sidecar/
  pyproject.toml  # Python 3.12
  export_reference_data.py
```

**メリット:**

```text
調査用途には便利
複数providerの比較が楽
```

**弱点:**

```text
AGPLv3
Python 3.13本体と噛み合いにくい
production data contractには重い
```

---

### 8. `bmoscon/cryptofeed`

**用途:** Binance / OKX / Bybit などCEXのWebSocket reference。
**採用判断:** Trade[XYZ]本体には不要。外部crypto referenceならあり。

`cryptofeed` は複数暗号資産取引所のWebSocket feedを扱い、trades、book updates、ticker updatesなどを標準化してcallbackへ返すと説明されています。([GitHub][8])
ただし、現在確認できる `cryptofeed/exchanges/__init__.py` の対応exchange一覧には Hyperliquid は見当たりません。Binance、Bybit、OKX、Deribit、dYdXなどはあります。([GitHub][9])

**Repoでの使い方:**

```text
data/external/cryptofeed/
```

**用途:**

```text
BTC / ETH / crypto market regime reference
外部CEXの流動性・volatility proxy
```

**注意:** Trade[XYZ] venue dataの代替にはしない。

---

## 実務上の採用順位

| 優先 | OSS                          | 用途                                   | Repoでの位置づけ           |
| -: | ---------------------------- | ------------------------------------ | -------------------- |
|  1 | 既存 `TradeXyzClient`          | canonical Trade[XYZ] raw取得           | 維持                   |
|  2 | `dlt-hub/dlt`                | staging / schema drift / incremental | optional integration |
|  3 | `ccxt/ccxt`                  | external cross-check / OHLCV比較       | secondary source     |
|  4 | `alpacahq/alpaca-py`         | real market reference                | provider強化           |
|  5 | `databento/databento-python` | paid historical reference            | sidecar provider     |
|  6 | `massive-com/client-python`  | stock / ETF reference                | sidecar provider     |
|  7 | `hyperliquid-python-sdk`     | API互換確認 / SDK差分検証                    | probe用途              |
|  8 | `OpenBB`                     | research aggregation                 | sidecarのみ            |
|  9 | `cryptofeed`                 | CEX WebSocket reference              | Trade[XYZ]外部補助       |

## 重要な現実

OSSでできることは **取得・整形・検証・保存** です。
OSSだけでは、次の問題は解決しません。

```text
過去30日分のTrade[XYZ] L2 quoteを作る
oracle timestamp provenanceを捏造せずに埋める
real market referenceの利用権を保証する
有料データのライセンス制約を消す
```

ただし、Hyperliquid API自体には `candleSnapshot` があり、公式docsでは「直近5000 candlesまで」「1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M」をサポートするとされています。([Hyperliquid Docs][10])
つまり、**signal candle backfill** はある程度可能です。

一方で、`l2Book` はRESTでは最大20 levels per sideです。([Hyperliquid Docs][10])
これは、過去のfull L2 replayやmicrostructure backtestを復元するものではありません。

WebSocketでは `allMids`, `candle`, `l2Book`, `trades`, `activeAssetCtx`, `allDexsAssetCtxs` などを購読できます。([Hyperliquid Docs][11]) ([Hyperliquid Docs][11]) ([Hyperliquid Docs][11])
これは今後の継続収集には有効です。

## 使い分け

### すぐ実装するなら

```text
dlt + ccxt
```

理由は、既存collectorを壊さず、外部比較とstagingだけ足せるからです。

**構成:**

```text
src/sis/integrations/
  dlt_staging/
  ccxt_reference/

data/external/
  ccxt/
  dlt/

data/manifests/
  external_reference_manifest.json
```

### real market referenceを本気で安定させるなら

```text
alpaca-py
```

既存のAlpaca providerを公式SDK化する。
ただし、認証情報とplanに依存します。

### 30日待たずにhistorical品質を上げるなら

```text
databento-python or Massive client
```

ただし、これは「OSS導入」ではなく「有料・規約付きデータソース導入」です。
GitHub OSSはclientでしかありません。

### やらない方がいいこと

```text
OpenBBをcore dependencyに入れる
cryptofeedでTrade[XYZ]を置き換える
CCXTデータをcanonical Trade[XYZ] quoteとして扱う
hyperliquid-python-sdkで既存collectorを丸ごと置換する
```

## 推奨アーキテクチャ

```text
canonical venue data:
  data/raw/quotes/trade_xyz/*.jsonl
  └─ existing TradeXyzClient

venue candle backfill:
  data/raw/candles/trade_xyz/*.jsonl
  └─ existing TradeXyzClient.candle_snapshot()

external reference:
  data/external/ccxt/*.jsonl
  data/external/alpaca/*.parquet
  data/external/databento/*.parquet

staging:
  data/staging/dlt/*.duckdb
  data/staging/dlt/*.parquet

manifest:
  data/manifests/trade_xyz_*.json
  data/manifests/external_reference_*.json
```

## トレードオフ

| 方針                        | 速度 | コスト | リスク |                               効果 |
| ------------------------- | -: | --: | --: | -------------------------------: |
| 既存collector継続             |  低 |   低 |   低 |                 canonical品質が最も高い |
| `candleSnapshot` backfill |  高 |   低 |   中 |         signal評価は早く進むがL2実行BTには弱い |
| `ccxt` cross-check        |  中 |   低 |   中 |              外部比較に強いがcanonical不可 |
| `alpaca-py`               |  中 |   中 |   中 |          real market reference改善 |
| `databento` / `Massive`   |  高 |   高 |   中 |           historical reference改善 |
| `OpenBB` sidecar          |  中 | 低〜中 | 中〜高 |                   調査は速いがcoreには重い |
| `cryptofeed`              |  中 |   低 |   中 | CEX referenceには有効、Trade[XYZ]代替不可 |

## 次の一手

1. **`ccxt_reference` を追加する**
   `fetchOHLCV`, `fetchTicker`, `fetchOrderBook` を取り、`data/external/ccxt/` に保存。Trade[XYZ] canonicalとは混ぜない。

2. **`TradeXyzClient.candle_snapshot()` を使った `collect-trade-xyz-candles` を追加する**
   直近5000 candles制約をmanifestに記録し、`signal_only=true`, `not_l2_execution_data=true` を明示する。

3. **`dlt_staging` を optional integration として追加する**
   外部sourceだけを対象にして、既存 `normalize_quotes()` は置き換えない。

これが最も実務的です。
「今のcollectorを壊さず、足りない参照データだけを外から補う」構成になります。

17:8:43.(06/01)

[1]: https://github.com/hyperliquid-dex/hyperliquid-python-sdk "GitHub - hyperliquid-dex/hyperliquid-python-sdk: SDK for Hyperliquid API trading with Python. · GitHub"
[2]: https://github.com/ccxt/ccxt "GitHub - ccxt/ccxt: A cryptocurrency trading API with more than 100 exchanges in JavaScript / TypeScript / Python / C# / PHP / Go / Java · GitHub"
[3]: https://github.com/dlt-hub/dlt "GitHub - dlt-hub/dlt: data load tool (dlt) is an open source Python library that makes data loading easy ️ · GitHub"
[4]: https://github.com/alpacahq/alpaca-py "GitHub - alpacahq/alpaca-py: The Official Python SDK for Alpaca API · GitHub"
[5]: https://github.com/databento/databento-python "GitHub - databento/databento-python: The official Python client library for Databento · GitHub"
[6]: https://github.com/polygon-io/client-python "GitHub - massive-com/client-python: The official Python client library for the Massive.com REST and WebSocket API. · GitHub"
[7]: https://github.com/OpenBB-finance/OpenBB "GitHub - OpenBB-finance/OpenBB: Financial data platform for analysts, quants and AI agents. · GitHub"
[8]: https://github.com/bmoscon/cryptofeed "GitHub - bmoscon/cryptofeed: Cryptocurrency Exchange Websocket Data Feed Handler · GitHub"
[9]: https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/exchanges/__init__.py "cryptofeed/cryptofeed/exchanges/__init__.py at master · bmoscon/cryptofeed · GitHub"
[10]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint "Info endpoint | Hyperliquid Docs"
[11]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions "Subscriptions | Hyperliquid Docs"
