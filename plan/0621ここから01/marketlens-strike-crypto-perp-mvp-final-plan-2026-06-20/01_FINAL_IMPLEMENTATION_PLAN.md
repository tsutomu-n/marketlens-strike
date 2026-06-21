<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Crypto Perp Truth-Cycle MVP 最終実装計画

## 1. 最終決定

MarketLens Strike に追加する機能は、万能な取引基盤ではなく、個人トレーダーのための `Crypto Perp Truth-Cycle MVP` である。

```text
Bitget public market observation
-> event snapshot
-> prospective decision
-> matured outcome
-> 5〜25 USD actual execution measurement
-> simulation calibration
-> cash-based decision
```

初期仮説は急騰後反落ショートだが、システムは次を同格に扱う。

```text
REVERSAL_SHORT
CONTINUATION_LONG
NO_TRADE
UNKNOWN
```

「急騰したからshort」「出来高が減ったから冷却」「fundingが高いからshort有利」という短絡は実装しない。

## 2. Goal

### 2.1 プロダクトGoal

個人が1日に短時間で、次を判断できる状態を作る。

- Bitget USDT Perpで何が急変したか。
- その時点で何が観測可能だったか。
- short、long、見送りのどれを選んだか。
- 5 / 15 / 60 / 240 / 720 / 1440分後にどうなったか。
- 5 / 10 / 25 / 50 / 100 / 250 USDなら実際にいくら残ったか。
- 実測fillとsimulationがどれだけずれたか。
- 累計入出金・手数料・fundingを含め、現金が増えたか。

### 2.2 利益Goal

主目的関数は、口座残高の一時的最大値や勝率ではない。

```text
net_cash_usd
= withdrawals
- deposits
+ current_liquidatable_equity
- trading_fees
- funding
- infrastructure_cost
```

実験ごとに次も出す。

```text
net_usd_per_event
net_usd_per_operator_hour
probability_of_positive_cash_result
probability_hit_2x_before_ruin
probability_hit_5x_before_ruin
time_to_target
time_to_ruin
largest_loss_usd
profit_concentration
```

倍率到達率だけを最大化しない。negative-EV lotteryを選ぶ恐れがあるため、cash resultを必ず併記する。

## 3. 固定前提

- 個人開発・個人利用。
- 主市場は Bitget `USDT-FUTURES`。
- Binance、Bybit、OKXは対象外。
- Hyperliquid / GRVTは後段reference候補。
- MEXCは補助reference候補。
- API keyはMVP-A/B完了後に作成可能。
- 初期総資本上限は3,000 USD。
- 初回実験予算例は300 USD。ただしconfig必須で、コードへ固定しない。
- tiny live measurementは1注文5〜25 USD。
- HFT、market making、arbitrageは行わない。
- 秒以下の速度競争をしない。
- Python 3.13、uv、Typer、Pydantic、Polarsを維持。
- 通常CIはnetworkとcredentialを要求しない。

## 4. Barrier

1. 既存repoはartifact/gateが豊富だが、実市場から学ぶまでの距離が長くなりやすい。
2. `VenueId`は現在 `trade_xyz`, `bitget_demo` が中心で、production Bitgetはcatalog-only。
3. public candleだけではfill、partial、latency、stop挙動が分からない。
4. 低流動性Perpでは出来高、OI、fundingの意味が曖昧になりやすい。
5. 人間判断は後知恵で改変されやすい。
6. 全損許容はedgeではなくrisk preferenceに過ぎない。
7. OSSを大量導入すると、検証より統合が主目的になる。
8. 旧計画は仮説中立を掲げながらshort前提fieldを含み、narrative biasがschemaへ漏れていた。

## 5. Scope

### 実装する

- Bitget public API capability probe。
- instrument / ticker / 15m candle / funding / OI snapshot。
- universeの追加・削除・状態・fee・precision差分。
- event detectorとevent card。
- 候補銘柄だけ1m / public trades / books1 / books15記録。
- 結果前のsystem/human decision ledger。
- direction-neutral outcome settlement。
- Hypothesis property tests。
- Tardis Bitget sampleを使うgolden fixture。
- pybotters比較spike。
- Freqtrade external leakage/startup differential。
- credentialed read-only account snapshot。
- order preview / idempotency / rounding。
- 明示承認された5〜25 USD tiny live measurement。
- actual cash ledgerとsimulation calibration。
- reversal / continuation / no-trade tournament。
- 既存Strategy Input Contract / Viewerへのread-only接続。

### 実装しない

- 自動戦略発注daemon。
- 全銘柄L2常時保存。
- maker/MM戦略。
- reference venueを先に3つ実装。
- ニュース/SNS/on-chain統合。
- market cap point-in-time DB。
- Strategy Lab v2全面移行。
- Svelte UI。
- ML/LLM optimizer。
- live scale-up。

## 6. Architecture

```text
Bitget v3 public REST
  instruments / tickers / candles / OI / funding
                 |
                 v
       Immutable raw snapshots
                 |
        +--------+---------+
        |                  |
        v                  v
 Universe diff       Broad 15m history
        |                  |
        +---------+--------+
                  v
             Event detector
       slow_74h / fast_1h / near_miss
                  |
                  v
         Event snapshot + card
                  |
       +----------+-----------+
       |                      |
       v                      v
Prospective decision    Candidate recorder
SHORT/LONG/NO_TRADE     1m/trades/books
       |                      |
       +----------+-----------+
                  v
          Outcome settlement
                  |
                  v
        Credentialed read-only
                  |
                  v
       Order preview / tiny live
                  |
                  v
   Actual fill + cash ledger + replay calibration
                  |
                  v
      Hypothesis tournament / Workbench bridge
```

## 7. Data cadence

### 全銘柄

```text
instruments: 5分
all tickers: 30秒
15m candle: bar close後5秒、直近2本を再取得
funding history: settlement後と日次補完
OI: all-symbol endpointまたはtickerで30〜60秒
```

### event候補のみ

```text
1m candle backfill: event前48時間
public trades: event後6時間、最大24時間
books1: event後6時間
books15: event後6時間
同時capture上限: 5
```

全銘柄1m常時保存は、保存量・rate limit・欠損率を実測してからoption化する。

## 8. Event definition

### 8.1 `slow_pump_74h_v1`

ユーザーの初期仮説を探索triggerとして実装する。

```text
return_74h >= 4%
recent_74h_quote_turnover / previous_74h_quote_turnover - 1 >= 15%
```

74時間は15分足296本。非重複比較には最低592本必要。warm-upを含め336時間backfillをdefaultにする。

### 8.2 `fast_pump_1h_v1`

```text
abs(return_60m) >= config floor
robust_return_z >= config threshold
turnover_percentile >= config threshold
```

median/MADを使用し、標準偏差だけに依存しない。

### 8.3 Eventは注文ではない

Event生成時のstatusは次だけ。

```text
CAPTURE_REQUESTED
CAPTURE_ACTIVE
CAPTURE_COMPLETE
INCONCLUSIVE_DATA
REJECTED_DATA_QUALITY
```

`SHORT_CANDIDATE`のような方向判断はdecision ledger側へ分離する。

## 9. Competing decisions

同一eventに対し、systemとhumanを別々に保存する。

```text
REVERSAL_SHORT
CONTINUATION_LONG
NO_TRADE
UNKNOWN
CAPTURE_ONLY
```

旧short固定schemaを禁止する。execution fieldは次のようにdirection-neutralにする。

```text
side: long | short
entry_vwap
exit_vwap
entry_book_side: ask | bid
exit_book_side: bid | ask
```

longはaskで入りbidで出る。shortはbidで入りaskで出る。

## 10. Risk philosophy

### 許容する

- 明示したexperiment budgetの市場損失。
- Pod/experimentが0になること。
- 高いvariance。
- 連敗。

### 許容しない

- lifetime budgetを超える自動追加入金。
- 同一clientOid以外のretryによる重複注文。
- account/margin/position mode不明の発注。
- cross margin。
- 既存positionがある状態のmeasurement。
- reconciliation未完了の次注文。

### Budget model

```text
capital_ceiling_usd: 3000
lifetime_experiment_budget_usd: required
measurement_notional_usd: 5..25
allow_top_up: false
max_open_positions: 1
```

Podは会計単位であり、死んだPodを除外して成績表示してはいけない。全Podのdeposit/withdrawalをcash ledgerで合算する。

## 11. Implementation tasks

### M00 — Current truth alignment and supersession

**目的**

旧巨大計画を実装入口から外し、この計画をcurrent handoffへする。

**変更ファイル**

```text
docs/strategy_research_lab/README.md
docs/NEXT_DIRECTION_CURRENT.md
docs/CURRENT_STATE.md
scripts/check_current_docs.py
plan/README.md
```

**実装**

- 旧planをhistorical/supersededとして明記。
- current docsから本計画へリンク。
- runtime値、pass count、artifact timestampをdocsへ固定しない。

**テスト**

```bash
uv run python scripts/check_current_docs.py
./scripts/check
```

**完了条件**

- coderが旧CP-00〜10をcurrent instructionと誤読しない。
- current docsとplan routingに矛盾がない。

---

### M01 — Domain foundation, config, CLI and property testing

**目的**

public data MVPの最小domainと設定を作る。

**新規ファイル**

```text
src/sis/crypto_perp/__init__.py
src/sis/crypto_perp/config.py
src/sis/crypto_perp/models.py
src/sis/crypto_perp/io.py
src/sis/crypto_perp/clock.py
src/sis/crypto_perp/reason_codes.py
src/sis/commands/crypto_perp.py
configs/crypto_perp/bitget_personal_edge_lab.yaml
schemas/crypto_perp_lab_config.v1.schema.json
tests/crypto_perp/__init__.py
tests/crypto_perp/test_config.py
tests/crypto_perp/property/test_common_invariants.py
```

**変更ファイル**

```text
src/sis/cli.py
pyproject.toml
uv.lock
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
```

**実装**

- `hypothesis`をdev dependencyへ追加。
- Pydantic `extra="forbid"`。
- UTC aware datetimeのみ。
- network default deny。
- live/write boundaryはfalse固定。
- command registrationは実装済みcommandだけ。

**最初のCLI**

```text
crypto-perp-config-validate
crypto-perp-probe
crypto-perp-refresh
crypto-perp-watchdeck
```

**完了条件**

- valid configがPydantic/JSON Schema双方を通る。
- unknown field、naive datetime、negative interval、boundary trueを拒否。
- `scripts/check_cli_catalog.py`が通る。

---

### M02 — Bitget public probe and immutable raw snapshots

**目的**

API keyなしで、実際に使えるendpoint・rate limit・response shapeを記録する。

**新規ファイル**

```text
src/sis/crypto_perp/bitget/__init__.py
src/sis/crypto_perp/bitget/client.py
src/sis/crypto_perp/bitget/public_api.py
src/sis/crypto_perp/bitget/normalizers.py
src/sis/crypto_perp/bitget/probe.py
src/sis/crypto_perp/raw_store.py
schemas/crypto_perp_provider_probe.v1.schema.json
tests/crypto_perp/test_bitget_client.py
tests/crypto_perp/test_bitget_normalizers.py
tests/crypto_perp/test_provider_probe.py
tests/fixtures/crypto_perp/bitget/public/*.json
```

**endpoint**

```text
GET /api/v3/market/instruments
GET /api/v3/market/tickers
GET /api/v3/market/candles
GET /api/v3/market/open-interest
GET /api/v3/market/history-fund-rate
GET public server time endpoint
```

**実装**

- `httpx.AsyncClient`、transport injection。
- 429/5xx/timeoutのみbounded retry。
- malformed JSON/shape driftはretryで隠さない。
- request params、status、latency、received_at、raw hashを保存。
- Bitget candle docsの「up to 1000」と「Maximum 100」の矛盾を`documentation_anomalies`へ保存し、probe実測を採用。
- `SIS_ALLOW_PUBLIC_NETWORK=1`かつ`--network`両方が無ければ接続しない。

**CLI**

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe   --config configs/crypto_perp/bitget_personal_edge_lab.yaml   --network
```

**完了条件**

- CIはfixtureのみ。
- public probeはcredentialを参照しない。
- error responseも診断artifactへ残す。

---

### M03 — Universe diff, ticker snapshot and broad 15m history

**目的**

銘柄集合とscreening historyをpoint-in-timeで残す。

**新規ファイル**

```text
src/sis/crypto_perp/universe.py
src/sis/crypto_perp/heartbeat.py
src/sis/crypto_perp/bars.py
src/sis/crypto_perp/quality.py
schemas/crypto_perp_universe_snapshot.v1.schema.json
schemas/crypto_perp_market_snapshot.v1.schema.json
tests/crypto_perp/test_universe.py
tests/crypto_perp/test_heartbeat.py
tests/crypto_perp/test_bars.py
tests/crypto_perp/test_quality.py
```

**実装**

- instrumentsはimmutable snapshot。
- added/removed/status_changed/metadata_changedを検出。
- status, offTime, limitOpenTime, fee, precision, minOrderAmount, leverage, funding intervalを追跡。
- `online`以外はactionable false。
- current universeだけで過去を再構成しない。
- 15m market/mark/index candleを別source_typeで保存。
- current open barをcanonicalに入れない。
- 直近2本を再取得しrevisionを検知。
- missing barをforward-fillしない。
- OI unit不明は`unknown`。

**完了条件**

- 追加/削除/状態/fee/precision変更のfixture testが通る。
- gap、duplicate、invalid OHLC、negative volumeはevent engineへ流れない。

---

### M04 — Event capture and event card (MVP-A)

**目的**

検出時点の情報を凍結し、人が短時間で読めるevent cardを作る。

**新規ファイル**

```text
src/sis/crypto_perp/features.py
src/sis/crypto_perp/events.py
src/sis/crypto_perp/event_card.py
src/sis/crypto_perp/rendering.py
schemas/crypto_perp_event.v1.schema.json
tests/crypto_perp/test_features.py
tests/crypto_perp/test_events.py
tests/crypto_perp/test_event_card.py
```

**実装**

- `slow_pump_74h_v1`, `fast_pump_1h_v1`, `near_miss_v1`。
- market context: BTC, ETH, cross-sectional median, breadth。
- event IDはdeterministic。
- `information_cutoff_at`より後を読まない。
- event cardはprice、turnover、spread、OI、funding、listing age、data gapsを表示。
- 方向は決定しない。
- local outboxへalert。
- alert capとdedupe。

**CLI**

```bash
uv run sis crypto-perp-refresh --through events
uv run sis crypto-perp-watchdeck --top 20
```

**完了条件**

- future data mutationでevent featureが変わらない。
- price/volume二変数だけでshort actionを出さない。
- HTML escape testが通る。

---

### M05 — Candidate-only high-resolution recorder

**目的**

候補にだけ1m/trade/bookを集め、time orderingとfillabilityを観測する。

**新規ファイル**

```text
src/sis/crypto_perp/recorder.py
src/sis/crypto_perp/ws_protocol.py
src/sis/crypto_perp/book.py
src/sis/crypto_perp/segments.py
schemas/crypto_perp_capture_manifest.v1.schema.json
tests/crypto_perp/test_recorder.py
tests/crypto_perp/test_ws_protocol.py
tests/crypto_perp/test_book.py
tests/crypto_perp/test_segments.py
```

**実装**

- native `websockets` backend。
- `trade`, `books1`, `books15`。
- raw messageをnormalize前にgzip JSONLへ保存。
- ping 30秒、pong timeout、bounded reconnect。
- 50 channels/connection未満をdefault。
- books full diffを使う場合はseq/checksum検証。books1/5/15 snapshot modeは受信時点とsource tsを保存。
- checksum failure/gap後のbookは無効化しresync。
- SIGTERMでatomic close。
- max concurrent capture=5。

**完了条件**

- disconnect/gap/checksum/restart fixture test。
- gapをfillability successにしない。
- 10分network smokeと24h soak reportを作れる。

---

### M06 — Prospective decision and outcome ledger (MVP-B)

**目的**

判断を結果より前に固定し、short/long/no-tradeを方向中立に比較する。

**新規ファイル**

```text
src/sis/crypto_perp/decisions.py
src/sis/crypto_perp/outcomes.py
schemas/crypto_perp_decision.v1.schema.json
schemas/crypto_perp_outcome.v1.schema.json
tests/crypto_perp/test_decisions.py
tests/crypto_perp/test_outcomes.py
tests/crypto_perp/property/test_decision_time.py
```

**実装**

- system_decisionとhuman_decisionを分離。
- human action: short/long/no-trade/unknown/capture-only。
- review_seconds、reason tags、source event hash。
- overwrite禁止。修正はreplacement chain。
- outcome horizons: 5m,15m,1h,4h,12h,24h。
- raw return、directional return、MFE、MAE、high-first/low-first/ambiguous。
- 1m不足でstop/take両方hitならoptimisticに解決しない。
- market-adjusted resultとnear-miss比較。

**完了条件**

- decision_atがoutcome evidenceより後ならreject。
- short固定fieldがない。
- 未成熟outcomeを集計しない。

---

### M07 — Validation accelerator pack

**目的**

外部の実装とデータで、MarketLens固有バグを早く潰す。

**新規ファイル**

```text
tools/oss_spikes/pybotters_bitget/README.md
tools/oss_spikes/pybotters_bitget/pyproject.toml
tools/oss_spikes/pybotters_bitget/recorder.py
tools/external_validation/freqtrade/README.md
tools/external_validation/freqtrade/compose.yaml
tools/external_validation/freqtrade/export_marketlens_data.py
scripts/download_tardis_bitget_fixture.py
docs/references/crypto_perp/OSS_ADOPTION_DECISIONS.md
docs/references/crypto_perp/HUMMINGBOT_BITGET_CONNECTOR_NOTES.md
docs/references/crypto_perp/COMPETITION_PROTOCOL.md
tests/fixtures/crypto_perp/tardis/PROVENANCE.md
tests/crypto_perp/test_tardis_golden.py
```

**実装**

- Hypothesis propertiesをM01〜M06へ追加。
- Tardis sampleからtrade/book/ticker golden fixtureを生成。
- native WSとpybottersを24h比較。pybottersは`<2.0`別workspace。
- Freqtradeは別container。lookahead/recursive differentialだけ。
- Hummingbot Bitget connectorからendpoint/rate limit/order stateを照合し、公式docsとの差をnotesに残す。
- GPLコードをMarketLensへコピー/importしない。

**完了条件**

- OSS採用/不採用decision artifactがある。
- external validator失敗でMarketLens coreが起動不能にならない。

---

### M08 — Credentialed read-only and order preview

**目的**

書き込み前にaccount reality、fee、mode、position、open orderを確認する。

**新規ファイル**

```text
src/sis/crypto_perp/bitget/auth.py
src/sis/crypto_perp/bitget/account.py
src/sis/crypto_perp/order_preview.py
src/sis/crypto_perp/idempotency.py
schemas/crypto_perp_account_snapshot.v1.schema.json
schemas/crypto_perp_order_preview.v1.schema.json
tests/crypto_perp/test_bitget_auth.py
tests/crypto_perp/test_account_snapshot.py
tests/crypto_perp/test_order_preview.py
tests/crypto_perp/property/test_rounding.py
```

**実装**

- credentialはenvのみ。artifact/logへ出さない。
- account assets、account info、fee、positions、open ordersをread-only取得。
- API permissionはmanual checklistも保存。
- order previewはsymbol/side/qty/notional/precision/minimum/margin/leverageを算出。
- isolated marginを必須。
- existing position/open orderがあればmeasurement blocked。
- deterministic clientOid。32文字制約を満たす。
- previewはwriteしない。

**CLI**

```text
crypto-perp-account-probe
crypto-perp-order-preview
```

**完了条件**

- secret redaction test。
- qty/price rounding property test。
- previewから注文は発生しない。

---

### M09 — Tiny live execution calibration (MVP-C)

**目的**

5〜25 USDを市場調査費として使い、actual fill/fee/latency/closeを測る。

**前提**

- ユーザーの別明示承認。
- 専用risk budget。
- 出金不可API key。
- IP制限。
- isolated margin。
- open position/orderなし。
- M08 PASS。

**新規ファイル**

```text
src/sis/crypto_perp/tiny_live.py
src/sis/crypto_perp/reconciliation.py
src/sis/commands/crypto_perp_live.py
configs/crypto_perp/tiny_live_measurement.yaml
schemas/crypto_perp_live_measurement.v1.schema.json
tests/crypto_perp/test_tiny_live.py
tests/crypto_perp/test_reconciliation.py
tests/crypto_perp/property/test_order_state_machine.py
```

**実装**

- strategy auto-entryではなくoperator-confirmed one-shot measurement。
- `SIS_ENABLE_TINY_LIVE_MEASUREMENT=1`。
- config `enabled=true`。
- CLI `--confirm-live`と確認phrase。
- notional 5〜25 USD。
- max open position 1。
- order create timeout時は同じclientOidでqueryし、盲目的再送しない。
- entry後にposition/fill/feeをquery。
- exitはreduceOnly。
- close失敗時は新規entryを永久blockし、人間対応を要求。
- entry/exit/fee/rejection/latencyをimmutable artifactへ保存。

**CLI**

```text
crypto-perp-live-measure
crypto-perp-live-reconcile
crypto-perp-live-close
```

**完了条件**

- mocked order state machine全経路PASS。
- 1回のmanual canaryでentryからflat reconciliationまでartifactが揃う。
- M09成功は自動戦略運用許可ではない。

---

### M10 — Actual cash ledger and replay calibration

**目的**

simulationではなく実現現金で評価する。

**新規ファイル**

```text
src/sis/crypto_perp/cash_ledger.py
src/sis/crypto_perp/replay.py
src/sis/crypto_perp/calibration.py
schemas/crypto_perp_cash_ledger.v1.schema.json
schemas/crypto_perp_execution_replay.v1.schema.json
tests/crypto_perp/test_cash_ledger.py
tests/crypto_perp/test_replay.py
tests/crypto_perp/test_calibration.py
```

**実装**

- deposits/withdrawals/realized PnL/fee/funding/infra costを分離。
- all experiments/podsを合算。
- 5/10/25/50/100/250 USD、5/15/30/60秒latency grid。
- direction-neutral entry/exit VWAP。
- depth不足はUNFILLABLE。
- observed actual fillとreplay差をbias tableへ。
- actual fill数が少ない間はcalibration confidenceをLOW。

**完了条件**

- cash equationがhand calculation fixtureと一致。
- dead podを除外できない。
- actualとsimulatedの差を隠さない。

---

### M11 — Hypothesis tournament and Workbench bridge

**目的**

反落物語を競合仮説で倒し、既存Workbenchへevidenceを渡す。

**新規ファイル**

```text
src/sis/crypto_perp/tournament.py
src/sis/crypto_perp/workbench_bridge.py
schemas/crypto_perp_tournament_report.v1.schema.json
tests/crypto_perp/test_tournament.py
tests/crypto_perp/test_workbench_bridge.py
```

**変更候補**

```text
src/sis/strategy_workbench_viewer/
docs/strategy_workbench_viewer/README.md
docs/CURRENT_STATE.md
docs/IMPLEMENTED_SURFACES.md
docs/NEXT_DIRECTION_CURRENT.md
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
scripts/check_current_docs.py
```

**実装**

- reversal short / continuation long / no-tradeを同じevent setで比較。
- near miss、market-adjusted baseline。
- actual cash resultをprimary。
- largest loss、profit concentration、operator time。
- insufficient dataは`INCONCLUSIVE_DATA`。
- data snapshotを既存Strategy Input Contractへexport。
- ViewerはJSON/Markdown summaryを読むだけ。
- production Bitget venue schema wideningは、この時点でも必要性がなければしない。

**decision**

```text
KEEP_MEASURING
FREEZE_CONFIRMATORY_RULE
REVISE_EVENT_DETECTOR
REJECT_REVERSAL
REJECT_CONTINUATION
REJECT_EVENT_FAMILY
INCONCLUSIVE_DATA
```

**完了条件**

- winnerだけでなく全branchとno-tradeを報告。
- `FREEZE_CONFIRMATORY_RULE`はlive permissionではない。
- existing Workbench regression PASS。

## 12. Task completion order

```text
M00 -> M01 -> M02 -> M03 -> M04
                         |
                         v
                        M05 -> M06 -> M07
                                      |
                                      v
                                     M08
                                      |
                         explicit user approval
                                      |
                                      v
                                     M09 -> M10 -> M11
```

M07のHypothesis/Tardisは可能な範囲で前倒ししてよい。M09だけは承認なしで実行しない。

## 13. Definition of Done

ソフトウェア完成:

- M00〜M11のcode/schema/tests/docsが実装。
- M09はコードとmock testが完成し、実ネットワーク実行は承認状態に従う。
- eventからdecision、outcome、actual fill、cash ledgerまでhashで追跡可能。
- public network default deny。
- write pathは別command・別config・別env flag。
- no secret in artifact/log。
- Trade[XYZ]、NDX、既存Strategy Labの回帰なし。
- `./scripts/check` PASS。

利益仮説完成とは別である。全branchが負なら、`REJECT_EVENT_FAMILY`を再現可能に出せることが正しい完成である。
