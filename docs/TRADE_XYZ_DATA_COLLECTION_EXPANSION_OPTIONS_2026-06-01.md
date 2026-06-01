<!--
作成日: 2026-06-01_17:24 JST
更新日: 2026-06-01_17:57 JST
-->

# Trade[XYZ] データ収集範囲を広げる選択肢

## 目的

`資料/dataのあつめかた.md` の調査内容をヒントに、現行Repoで現実的に増やせる
Trade[XYZ]向けデータ収集の選択肢を整理する。

この文書は、理想的なデータ基盤のナラティブではなく、現行コードに接続できる順番を決めるための実務メモである。
実装判断では、常に `src/`、`tests/`、`schemas/`、`configs/`、CLI helpを正本にする。

実装計画としては、次を優先する。

```text
plan/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md
```

この文書は選択肢の整理であり、実装時の対象ファイル・schema・tests・完了条件は上記planを正とする。

## 現在の基本方針

Trade[XYZ]バックテストで混ぜてはいけないものを先に固定する。

```text
正本:
  Hyperliquid / Trade[XYZ] 公式read-only payload

補助:
  外部real-market reference
  macro / event / session reference
  paid vendor / indexer による照合データ

禁止:
  外部providerの価格やtimestampをTrade[XYZ]のfill / mark / oracle / funding正本として扱う
  recv_ts_ms / source_ts_ms / client timestampをoracle_ts_msとして埋める
  2026-05-30以前の実データをreadinessへ戻す
  live / wallet / signing / exchange writeをこの作業に混ぜる
```

現行Repoで既にある主要収集面は次の通り。

```text
uv run sis collect-trade-xyz-quotes
uv run sis collect-trade-xyz-data-cycle
uv run sis collect-trade-xyz-real-market-reference
uv run sis collect-trade-xyz-signal-candles
uv run sis collect-trade-xyz-account-fee
uv run sis collect-trade-xyz-funding-history
uv run sis build-trade-xyz-funding-events-from-history
uv run sis build-trade-xyz-session-state
uv run sis build-trade-xyz-data-readiness
uv run sis trade-xyz-collection-status
```

`real_market_reference` は現在、次のfallback chainを持つ。

```text
yfinance -> yahooquery -> stooq
```

これは外部参照価格用であり、Trade[XYZ]の約定価格やoracle timestampの代替ではない。

## 増やせるデータ収集レイヤ

### Layer 1: 公式WebSocket recorder

最優先で増やす候補。

取るデータ:

```text
l2Book
bbo
trades
candle
activeAssetCtx
allDexsAssetCtxs
allMids
```

目的:

```text
forward truth source
quote coverage改善
raw_payload_refの強化
切断/欠損/重複の監査
fill snapshot qualityの改善
```

実装イメージ:

```text
raw/ws/trade_xyz/YYYY-MM-DD/HH/<subscription>.jsonl.zst
normalized/ws_l2_book.parquet
normalized/ws_bbo.parquet
normalized/ws_trades.parquet
manifests/ws_capture_manifest.json
manifests/ws_gap_manifest.json
```

Repoに入れるなら、まずは public CLI ではなく、内部module + focused tests から始める。
既存 `collect-trade-xyz-quotes` のraw quote形式と互換にするか、WS専用raw形式を別にするかは、最初の設計判断になる。
安全側では、WS専用rawを別保存し、normalized変換時に既存quote schemaへ寄せる。

追加調査後の実装判断:

```text
1. WS専用rawは data/raw/ws/trade_xyz/ に分離する
2. subscriptionResponse / pong / error summary は control message として分離する
3. recv_ts_ms はcollector受信時刻であり、source_ts_msやoracle_ts_msの代替にしない
4. source_ts_ms は公式payload内に time / t / T 等が存在する場合だけ入れる
5. activeAssetCtxのctxにsource timestampが無い場合は、known gapとして扱う
6. WebSocket URL / subscription / heartbeat設定は config または CLI から解決し、コード固定しない
```

完了条件:

```text
1. 1 symbolで1時間以上append-only保存できる
2. reconnect後もraw_payload_refが壊れない
3. duplicate / heartbeat gap / bid-ask inversionをmanifestで確認できる
4. 既存quotes.parquetへ混入せず、変換後だけ別artifactとして読める
```

### Layer 2: 公式REST parity / metadata polling

既存REST collectorの補助能力を強くする候補。

取るデータ:

```text
metaAndAssetCtxs
fundingHistory
candleSnapshot
userFees
perpDexStatus
perpDexLimits
perpsAtOpenInterestCap
```

目的:

```text
WebSocketの欠損検査
funding eventの補助
fee/account feeの確認
OI cap / discovery bound / dex statusの状態確認
signal candleの補助
```

実装イメージ:

```text
raw/rest/trade_xyz/<endpoint>/YYYY-MM-DD.jsonl
normalized/rest_asset_ctxs.parquet
normalized/rest_funding_history.parquet
manifests/rest_parity_manifest.json
```

現行Repoには `fundingHistory`、`candleSnapshot`、`userFees` 系の流れがある。
次に増やすなら、`perpDexStatus` / `perpDexLimits` / `perpsAtOpenInterestCap` を
readinessの補助情報として保存する価値がある。

完了条件:

```text
1. 収集endpointごとにraw保存とmanifestがある
2. WS/quote snapshotと同一symbol・同一時刻帯で比較できる
3. OI cap / dex statusをentry gateの説明情報として出せる
4. REST polling結果だけでfill価格を作らない
```

### Layer 3: 外部real-market referenceの拡張

現行fallback chainの次に広げる候補。

現在:

```text
yfinance
yahooquery
stooq
```

追加候補:

```text
Alpaca:
  Repoにprovider実装あり。
  credentials必須。
  US stocks/ETFsの補助reference向き。

Alpha Vantage:
  stocks / FX / commodities / macroが取れる。
  API key必須。
  rate limitに注意。

Twelve Data:
  stocks / ETFs / forex / indices / commoditiesの候補。
  API key必須。

Massive / Polygon:
  equities referenceを強くする候補。
  paid前提。

Databento:
  Parquet / DBN / symbologyが強い候補。
  usage-based paid前提。
```

目的:

```text
underlying reference price
外部市場session中の価格変化
Trade[XYZ]とのtracking quality
regime feature
volume / volatility context
```

実装方針:

```text
1. 現行provider chainは維持する
2. credentialed providerはdefault chainに入れない
3. providerごとにraw/normalized/manifestを分ける
4. symbol mappingとsession calendarを必ずmanifestに出す
5. 欠損symbolをpass扱いしない
```

完了条件:

```text
1. mapped symbolsが全て返る
2. provider_chain / provider_attempts / unresolved_symbolsがmanifestに出る
3. row_countだけでpassにしない
4. 外部provider timestampをoracle_ts_msとして使わない
```

### Layer 4: paid historical / replay vendor

履歴不足を短縮したい場合の候補。

候補:

```text
Tardis.dev
0xArchive
QuickNode SQL Explorer
Allium
Amberdata
Kaiko
CoinAPI
```

用途:

```text
historical l2Book
historical bbo
historical trades
funding / OI / market context
official collectorとのoverlap compare
欠損調査
```

採用条件:

```text
1. Trade[XYZ] / HIP-3 / Hyperliquid該当symbolsを扱える
2. raw downloadまたはquery resultを保存できる
3. request_uri / provider / query / download_ts / sha256をmanifestに残せる
4. vendor normalized schemaと公式payloadの差分を説明できる
5. 2026-05-30以前の実データをreadinessに混ぜない
```

これは正本を置き換えるものではなく、短期的には照合・補完・欠損調査用にする。
本当に正本へ昇格する場合は、vendor license、schema差分、再現性、コストを別ADRで決める。

### Layer 5: macro / event / calendar

戦略評価に必要になるが、fill simulation正本ではない候補。

取るデータ:

```text
FOMC calendar
CPI / NFP / major macro event calendar
Treasury yields
VIX
DXY or UUP
sector ETF
earnings calendar
split / dividend / corporate actions
holiday calendar
external market session
```

用途:

```text
regime_riskguard_trend
qqq_trend_rates_vix
session filter
event blackout
reference market regime
```

現行Repoでは、まず `real_market_reference` と基本regime symbolsを強化するのが先。
event calendarは、戦略側が使う段階になってから入れる。

### Layer 6: OSS integration / sidecar

`資料/dataをあつめるときのOSS.md` から取り込むべき観点。
OSSはデータ権利やTrade[XYZ]固有仕様を解決しない。役割は、取得、整形、比較、staging、
schema drift検知、sidecar provider化である。

最重要の境界:

```text
既存 TradeXyzClient:
  維持する。
  Trade[XYZ] / Hyperliquid公式read-only payloadのcanonical collector。

hyperliquid-python-sdk:
  置き換えではなく、probe / regression oracle。
  既存clientとのpayload差分検証に使う。

ccxt:
  external cross-check。
  OHLCV / ticker / orderbook snapshot / trades を比較用に取る。
  data/raw/quotes/trade_xyz には混ぜない。

dlt:
  sourceではなくstaging層。
  外部sourceやsidecar dataのincremental loading / schema drift検知に使う。
  既存 normalize_quotes() は置き換えない。

alpaca-py:
  既存Alpaca providerを公式SDK化する候補。
  credentials / plan / data rights 前提。

databento-python / Massive client:
  paid reference sidecar。
  高品質historical reference用で、Trade[XYZ] venue-native正本ではない。

OpenBB:
  research sidecarのみ。
  core dependencyにはしない。

cryptofeed:
  CEX regime reference用。
  Trade[XYZ]代替にはしない。
```

実装候補:

```text
src/sis/integrations/hyperliquid_sdk_probe/
src/sis/integrations/ccxt_reference/
src/sis/integrations/dlt_staging/
src/sis/real_market/providers/alpaca_official.py
src/sis/real_market/providers/databento.py
src/sis/real_market/providers/massive.py
```

保存先:

```text
data/external/ccxt/
data/external/alpaca/
data/external/databento/
data/external/massive/
data/staging/dlt/
data/manifests/external_reference_*.json
```

採用順:

```text
1. hyperliquid-python-sdk probe
2. ccxt_reference
3. dlt_staging
4. alpaca-py provider
5. databento-python / Massive paid sidecar
6. OpenBB sidecar
7. cryptofeed CEX sidecar
```

この順にする理由は、既存collectorを壊さずに、比較・検証・staging・外部referenceを
段階的に増やせるからである。

## 優先順位

### Phase A: すぐ進める

```text
1. 現行collectorを継続して30日coverageを作る
2. real_market_referenceを yfinance -> yahooquery -> stooq で再取得する
3. fundingHistory + oracle quote近傍結合を確認する
4. session_state_manifest を確認する
5. trade-xyz-collection-status でfail/known_gapを読む
```

理由:

```text
既存コードで動く
no secret
no paid vendor
readinessに直結する
```

### Phase B: 次に実装する価値が高い

```text
1. 公式WebSocket recorder
2. REST parity manifest
3. OI cap / dex status / perpDex limits collector
4. external reference providerのoptional adapter追加
5. hyperliquid-python-sdk probe
6. ccxt_reference
7. dlt_staging
```

理由:

```text
今より収集範囲が明確に増える
公式payload中心でprovenanceが強い
Trade[XYZ] backtestの誤読防止に効く
```

### Phase C: 予算・必要性が出たら検証する

```text
1. Tardis / 0xArchive / QuickNode / Allium の小規模PoC
2. Massive / Databento の外部reference PoC
3. Alpaca live smoke with credentials
4. Alpha Vantage / Twelve Data の低頻度reference PoC
5. alpaca-py / databento-python / Massive client の正式provider化
```

理由:

```text
cost / terms / API key / schema差分がある
最初から本線に入れると複雑になる
ただし履歴不足とreference欠損には効く
```

### Phase D: 今は避ける

```text
Web scraping
crowdsourced telemetry
partner data sharing
node運用
MT5 / CFD reference統合
```

理由:

```text
法務・運用・責任境界が重い
Trade[XYZ]純粋BT v0.1.xの目的から外れる
```

## 判断表

| 選択肢 | 今より増えるデータ | 実装摩擦 | コスト | 推奨 |
|---|---|---:|---:|---|
| 公式WS recorder | BBO, trades, active ctx, streaming L2 | 中 | 低 | 最優先 |
| REST parity拡張 | dex status, OI cap, limits, funding補助 | 低〜中 | 低 | 高 |
| yfinance/yahooquery/stooq | 外部日足reference | 実装済み | 低 | 継続 |
| Alpaca | US equity reference | 中 | credential | 任意 |
| Alpha Vantage / Twelve Data | FX, macro, commodities補助 | 中 | key/rate limit | 任意 |
| Massive / Databento | 高品質reference | 中 | paid | 必要時 |
| Tardis / 0xArchive | historical/replay補完 | 中 | paid/key | 必要時 |
| QuickNode / Allium | indexer照合 | 中 | paid/key | 調査用 |
| official S3 archive | historical L2/asset_ctxs | 中 | AWS requester-pays | 補助 |
| hyperliquid-python-sdk | 既存clientとの差分検証 | 低〜中 | 低 | probe |
| ccxt | 外部OHLCV/ticker/orderbook比較 | 中 | 低 | cross-check |
| dlt | staging/schema drift/incremental | 中 | 低 | optional |
| OpenBB | provider横断調査 | 高 | 低〜中 | sidecarのみ |
| cryptofeed | CEX regime WebSocket | 中 | 低 | Trade[XYZ]外部補助 |
| scraping | 見かけ上は広い | 高 | 不安定 | 非推奨 |

## 実装するときの必須ルール

```text
1. source tierをmanifestに残す
2. provider名、request_uri、query、download_ts、sha256を残す
3. raw_payload_refなしのnormalizedだけを正本にしない
4. external referenceをTrade[XYZ] venue-native priceと同じ列意味にしない
5. signal fields と fill snapshot fields を混ぜない
6. fundingはquote rowではなくfunding eventとして扱う
7. oracle timestampはpayloadに独立fieldがある場合だけ採用する
8. readinessはrow_countだけでpassにしない
9. OSS clientを入れてもデータ利用権やvendor termsは別途確認する
10. OSS由来のexternal dataはdata/externalまたはdata/stagingへ分離する
```

## 次の実装候補

最も現実的な次の実装候補は、公式WebSocket recorderの小さい版である。

最小仕様:

```text
対象:
  1 symbol

subscription:
  bbo
  trades
  activeAssetCtx

保存:
  append-only JSONL
  raw_payload_ref
  recv_ts_ms
  connection_id
  payload_sha256

manifest:
  row_count
  first_recv_ts
  last_recv_ts
  reconnect_count
  gap_count
  duplicate_count
  missing_symbol_count
```

完了条件:

```text
1. 1時間のread-only収集ができる
2. rawとmanifestが残る
3. 既存quotes.parquetへ勝手に混入しない
4. normalized変換の前にsource tierを確認できる
5. trade-xyz-collection-status と将来つなげる余地がある
```

この実装ができると、現在の1分polling中心の収集より、Trade[XYZ]の市場状態を細かく観測できる。
ただし、これはbackfillではない。過去不足を急いで埋める用途なら、paid vendorの小規模PoCを別タスクにする。
