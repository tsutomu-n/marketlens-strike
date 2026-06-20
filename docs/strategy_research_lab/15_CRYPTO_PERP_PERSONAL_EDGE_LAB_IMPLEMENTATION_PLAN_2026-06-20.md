<!--
作成日: 2026-06-20_16:35 JST
更新日: 2026-06-20_16:35 JST
-->

# Crypto Perp Personal Edge Lab Implementation Plan

## 結論

この計画で `marketlens-strike` に追加するのは、万能な暗号資産データ基盤でも、機関投資家向けのクオンツ研究所でもない。

追加するものは、**個人トレーダーが 25 / 50 / 100 / 250 USD の小口で実際に触れる Crypto Perp のイベントを発見し、見送り、前向き記録、執行再生、絶対損益評価まで一貫して行う `Crypto Perp Personal Edge Lab`** である。

最初の主データ源は Bitget USDT Perpetual の public REST / WebSocket とする。API key、wallet、signing、exchange write は最初の完成条件に含めない。Bitget account API は public-only vertical slice が安定した後の read-only 拡張とする。

最初の研究仮説は急騰後の反落ショートだが、実装はその結論を前提にしない。同じ event に対して次の競合仮説を必ず保存する。

```text
REVERSAL_SHORT
CONTINUATION
NO_TRADE
```

この計画で最優先する順番は次である。

```text
1. Bitget public data heartbeat と universe 差分を動かす
2. 15m screening で event を広く記録する
3. 候補だけ 1m / public trade / BBO / depth を高解像度収集する
4. 人間判断を outcome より前に記録する
5. 25 / 50 / 100 / 250 USD の執行再生と net USD を出す
6. matched control と競合仮説で、反落物語を反証する
7. 既存 Strategy Operations Workbench へ evidence artifact として接続する
8. public-only が安定した後だけ credentialed read-only を検討する
```

全面的な `market_data` 抽象化、全銘柄の常時 L2 保存、Strategy Lab v2 全面移行、Svelte UI、live order は先に作らない。必要性が実データで証明された箇所だけ広げる。

---

## 1. 目的

### 1.1 ソフトウェア目的

Bitget USDT Perp の public data だけで、次を再現可能にする。

```text
instrument / ticker / candle / funding / OI の取得
  -> point-in-time universe snapshot
  -> event detection
  -> candidate high-resolution capture
  -> human review
  -> forward outcome settlement
  -> execution replay by notional
  -> discovery report
  -> existing Workbench evidence bridge
```

### 1.2 トレード研究目的

大規模資金には容量が小さく、発生頻度が低く、銘柄差が大きく、手作業の文脈確認が必要だが、個人の小口なら経済価値が残る event を探す。

主指標は Sharpe や CAGR だけではなく、次とする。

```text
net_pnl_usd_by_notional
tradeable_rate_by_notional
max_adverse_excursion_usd
max_favorable_excursion_usd
alert_to_fill_drift_bps
operator_seconds_per_event
net_usd_per_operator_hour
veto_save_rate
veto_missed_winner_rate
top_1_loss_share_of_total_profit
```

### 1.3 初期仮説

初期 event family は次の二つを実装する。

```text
slow_pump_74h_v1
  user-defined seed:
  return_74h >= +4%
  and recent_74h_quote_turnover / previous_74h_quote_turnover - 1 >= +15%

fast_pump_1h_v1
  short-horizon anomaly detector:
  absolute return floor
  and symbol-local robust return anomaly
  and symbol-local turnover anomaly
```

これらは entry rule ではない。高解像度記録を開始する discovery trigger である。

---

## 2. 固定制約

### 2.1 プロジェクト制約

- 個人開発、個人利用のみ。
- 初期運用資金上限は 3,000 USD。
- 最初の想定 notional grid は 25 / 50 / 100 / 250 USD。
- 対象商品は Crypto Perpetual Futures。
- Binance、Bybit、OKX は対象外。
- CEX の主候補は Bitget。
- Hyperliquid / GRVT は reference venue 候補。
- MEXC は補助 reference。execution fee は account / API 経路で差異があり得るため、観測できるまで execution assumption に使わない。
- HFT、market making、arbitrage は実装しない。
- 1秒以下の競争を目的にしない。
- Python 3.13 と `uv` を維持する。
- public data first。credentialed read-only は後段。exchange write は別計画。

### 2.2 安全境界

全 artifact に次を固定する。

```text
permits_live_order: false
live_conversion_allowed: false
wallet_used: false
signing_used: false
exchange_write_used: false
live_order_submitted: false
```

### 2.3 費用前提

Bitget の標準評価は instrument metadata の fee を優先し、欠損時だけ設定 fallback を使う。

```text
priority 1: credentialed account fee snapshot（後段）
priority 2: public instrument makerFeeRate / takerFeeRate
priority 3: config fallback
```

初期 fallback:

```text
Bitget maker: 0.02% one way
Bitget taker: 0.06% one way
primary scenario: taker entry + taker exit = 0.12% round trip
```

Hyperliquid / GRVT / MEXC の fee は reference report には残すが、Bitget event の primary result を他 venue の安い fee で救済しない。

---

## 3. 非目的

この計画では次を完成扱いにしない。

- 収益保証、alpha proof。
- 自動注文、live order、wallet、signing、exchange write。
- maker rebate を利益源にする戦略。
- queue priority replay。
- 全銘柄・全期間の tick / L2 完全履歴。
- ニュース、SNS、token unlock、on-chain 全面収集。
- 厳密な時価総額 point-in-time database。
- Binance / Bybit / OKX adapter。
- 汎用 cross-asset market data platform。
- Strategy Lab v1 artifact の即時削除。
- SvelteKit UI。

---

## 4. 現行 repo との接続判断

### 4.1 再利用するもの

| 現行 surface | 再利用方法 |
|---|---|
| `src/sis/cli.py` | `register_crypto_perp_commands(app)` を追加する |
| `src/sis/settings.py` | `SIS_DATA_DIR` と log level のみ再利用。収集政策は YAML config に置く |
| `src/sis/ops/alerts.py` | local notification outbox に候補 alert を書く |
| `src/sis/strategy_inputs/` | data snapshot を Strategy Input Contract で検査する |
| `src/sis/research/strategy_lab/trial_ledger.py` | confirmatory trial 以降の試行記録に接続する |
| `src/sis/strategy_case_lite/` | event lab の discovery report を Strategy Case の source artifact として後段接続する |
| `src/sis/strategy_workbench_viewer/` | JSON / Markdown summary を表示する。Parquet を直接 scan させない |
| `src/sis/backtest/artifact_io.py` | hash / JSON artifact helper を可能な範囲で再利用する |
| `filelock` | segment writer と checkpoint の排他に使う |
| `httpx`, `tenacity` | Bitget REST client に使う |
| `websockets` | candidate-only WS recorder に使う |
| `polars`, `pyarrow`, `duckdb` | normalization、Parquet、local analysis に使う |
| `rich` | watchdeck CLI 表示に使う |

### 4.2 再利用しないもの

- `src/sis/storage/jsonl_store.py` は低頻度 artifact 用で、圧縮、rotation、atomic close、checkpoint がない。高頻度 raw feed writer には使わない。
- `src/sis/venues/trade_xyz/` を generic crypto-perp adapter として継承しない。
- fixture-only の `venue-read-only-probe` を network probe として拡張しない。別 command / schema にする。
- `strategy_authoring_spec.v1` を public data heartbeat の前提にしない。
- `VenueId` を最初の PR で無理に拡張しない。data collection artifact と execution permission を分離した後に migration する。

### 4.3 破壊的変更の扱い

破壊的変更は CP-09 で限定的に行う。

```text
read: v1 + v2
write: v2
v1 files: historical immutable
```

最初の operational value が出る CP-01〜CP-08 は、既存 Strategy Lab schema widening に依存させない。

---

## 5. 理想的ナラティブを排除する設計

### 5.1 禁止する短絡

```text
price pump -> short
volume increase -> buying heat
volume decrease -> exhaustion
OI increase -> new longs
high funding -> safe short
thin market -> individual edge
small notional -> always fillable
backtest profit -> paper candidate
maker rebate -> executable profit
current listings -> historical universe
```

### 5.2 強制する反証

各 event で必ず次を並行評価する。

1. `REVERSAL_SHORT`: 反落を取る。
2. `CONTINUATION`: 反落せず上昇継続する。
3. `NO_TRADE`: コスト、板、材料、状態不明で触らない。
4. `MATCHED_CONTROL`: 同時刻・同 liquidity band の非 event 銘柄。
5. `NEAR_MISS`: trigger の 80〜100% に達したが発火しなかった銘柄。

これにより、閾値を超えたものだけ見て物語を作る selection bias を減らす。

### 5.3 人間判断も検証対象にする

人間 veto は正解扱いしない。outcome より前に記録し、後から次を比較する。

```text
all system events
human accepted shadow events
human rejected events
human watch-only events
```

---

## 6. Target architecture

```text
Bitget Public REST
  instruments / tickers / candles / funding / OI
          |
          v
Broad Market Heartbeat
  low-cost all-symbol snapshots
          |
          +--> Universe Snapshot / Diff
          |
          +--> 15m Screening Store
                         |
                         v
                  Event Detector
             slow_74h / fast_1h / near_miss
                         |
                         v
                   Event Artifact
                         |
             +-----------+------------+
             |                        |
             v                        v
   Candidate High-Res Capture     Watchdeck / Alert
   1m / trades / books1 / depth      Human review
             |                        |
             +-----------+------------+
                         v
                  Outcome Settlement
                         |
                         v
                Execution Replay Grid
              25 / 50 / 100 / 250 USD
              5 / 15 / 30 / 60 sec latency
                         |
                         v
                   Discovery Report
                         |
                         v
          Strategy Input / Review / Case / Viewer bridge
```

### 6.1 Collection tiers

#### Tier A: 全銘柄の低コスト heartbeat

常時対象:

```text
instruments: configurable, default 300 seconds
all tickers: configurable, default 30 seconds
finalized 15m market candle: eligible universe
funding history: settlement後または日次補完
OI / mark / index / funding: ticker snapshot由来を優先
```

#### Tier B: 候補銘柄の高解像度 capture

Event 発火時だけ:

```text
1m market / mark / index candle backfill: default 48h
public trade WS
books1 WS
books15 または books5 WS
capture duration: default 6h, max 24h
max concurrent candidate captures: default 5
```

#### Tier C: reference venue

CP-10 以降。Bitget vertical slice が安定するまで実装しない。

```text
Hyperliquid: market context / lead-lag reference
GRVT: market context / fee / sequence-rich forward reference
MEXC: price confirmation only
```

### 6.2 1m と 15m の判断

- 15m は screening cadence と broad history の正本。
- 1m は candidate event の time ordering と entry/exit realism 用。
- 全銘柄 1m 常時収集は mandatory にしない。
- 実測した API 負荷、保存量、欠損率が許容範囲なら後から optional policy で有効化する。
- 5m / 1h / 4h / 1d は 1m または 15m から deterministic に生成し、役割を固定する。

---

## 7. Artifact contracts

Pydantic model を runtime validation の正本、tracked JSON Schema を interoperability guard とする。

### 7.1 `crypto_perp_provider_probe.v1`

必須 field:

```text
probe_id
provider_id
started_at / finished_at
base_url
network_attempted
credentials_used
endpoint_results[]
  endpoint_id
  request_path
  status_code
  latency_ms
  response_shape
  observed_limit
  pagination_behavior
  rate_limit_headers
  clock_offset_ms
  error_code
capabilities
  instruments
  all_tickers
  candle_1m
  candle_15m
  mark_candle
  index_candle
  funding_history
  open_interest
  public_trade_ws
  bbo_ws
  depth_ws
documentation_anomalies[]
boundary flags
```

重要: Bitget candle docs は取得上限表記が一貫しないため、`observed_limit` を probe で確定し、固定値をコードへ埋め込まない。

### 7.2 `crypto_perp_universe_snapshot.v1`

```text
snapshot_id
provider_id
product_type
observed_at
source_path / source_sha256
instruments[]
  native_symbol
  canonical_symbol
  base_asset / quote_asset
  status
  launch_time / off_time / limit_open_time
  tick_size / qty_step / min_order_amount
  max_market_order_qty / max_leverage
  funding_interval_hours
  maker_fee_rate / taker_fee_rate
  metadata_hash
eligibility[]
  eligible
  liquidity_band
  reason_codes[]
diff
  added[]
  removed[]
  status_changed[]
  metadata_changed[]
boundary flags
```

`removed` は API から消えた銘柄も含む。前 snapshot を上書きしない。

### 7.3 `crypto_perp_data_snapshot_manifest.v1`

```text
snapshot_id
provider_id
created_at
cutoff_at
raw_segments[] path/hash/count/min_ts/max_ts
normalized_artifacts[] path/hash/schema_version/row_count/min_ts/max_ts
quality_summary
  duplicate_count
  out_of_order_count
  missing_bar_count
  non_final_bar_count
  invalid_ohlc_count
  stale_snapshot_count
  ws_disconnect_count
  sequence_gap_count
  checksum_failure_count
known_gaps[]
boundary flags
```

### 7.4 `crypto_perp_event.v1`

```text
event_id                     # deterministic hash
event_family                 # slow_pump_74h_v1 / fast_pump_1h_v1 / near_miss_v1
provider_id
native_symbol / canonical_symbol
first_detected_at
information_cutoff_at
universe_snapshot_id
data_snapshot_id
detector_version
features_at_detection
market_context
  btc_return
  eth_return
  cross_section_median_return
  breadth
  market_regime
competing_hypotheses
  REVERSAL_SHORT
  CONTINUATION
  NO_TRADE
capture_request
status
reason_codes[]
boundary flags
```

`event_id = sha256(provider_id | native_symbol | detector_version | first_trigger_bucket)` とし、同一 detector / symbol の短時間重複 alert を防ぐ。

### 7.5 `crypto_perp_capture_manifest.v1`

```text
capture_id / event_id
started_at / ended_at
channels[]
segments[] path/hash/count/min_ts/max_ts
subscription_attempts
reconnect_count
sequence_gap_count
checksum_failure_count
resync_count
coverage_status
known_gaps[]
boundary flags
```

### 7.6 `crypto_perp_human_review.v1`

```text
review_id / event_id
reviewed_at
information_cutoff_at
operator
human_action
  ACCEPT_SHADOW
  WATCH_ONLY
  REJECT
  SIZE_CAP
size_cap_usd
reason_tags[]
  known_catalyst
  catalyst_not_checked
  listing_recent
  thin_book
  spread_bad
  continuation_risk
  data_gap
  funding_risk
  oi_unknown
  manual_other
notes
review_seconds
source_event_path / hash
boundary flags
```

レビュー後に event feature を書き換えない。

### 7.7 `crypto_perp_outcome.v1`

```text
outcome_id / event_id
settled_at
source_snapshot_refs[]
forward_horizons
  5m / 15m / 1h / 4h / 12h / 24h
for each horizon
  raw_return
  reversal_short_return
  max_favorable_excursion
  max_adverse_excursion
  high_first / low_first / ambiguous_order
  market_adjusted_return
matched_control_ids[]
status
known_gaps[]
boundary flags
```

### 7.8 `crypto_perp_execution_replay.v1`

```text
replay_id / event_id
entry_model
  first_valid_bbo_after_latency
exit_model
  bbo_at_horizon / stop / take-profit / time-stop
notional_results[]
  notional_usd
  latency_seconds
  entry_bid_vwap
  exit_ask_vwap
  entry_slippage_bps
  exit_slippage_bps
  fee_usd
  funding_usd
  gross_pnl_usd
  net_pnl_usd
  fill_status
    FILLED
    PARTIAL
    UNFILLABLE
    UNKNOWN_DEPTH
    DATA_GAP
stress_results[]
assumption_codes[]
boundary flags
```

Short entry は bid、short exit は ask を消費する。観測 depth より先を外挿しない。

### 7.9 `crypto_perp_discovery_report.v1`

```text
report_id
window_start / window_end
config_hash
trial_ids[]
event_counts_by_family
symbol_count
liquidity_band_counts
hypothesis_results
notional_results
operator_metrics
veto_metrics
loss_concentration
matched_control_comparison
near_miss_comparison
data_quality_summary
recommendation
  CONTINUE_DISCOVERY
  FREEZE_CONFIRMATORY_TRIAL
  REVISE_DETECTOR
  REJECT_EVENT_FAMILY
  INCONCLUSIVE_DATA
required_actions[]
boundary flags
```

---

## 8. Normalized table contracts

### 8.1 `instrument_snapshot.parquet`

Key:

```text
(provider_id, native_symbol, observed_at)
```

### 8.2 `ticker_snapshot.parquet`

Key:

```text
(provider_id, native_symbol, ts_event, ts_received)
```

必須列:

```text
last_price
bid1 / ask1
bid1_size / ask1_size
spread_bps
turnover_24h_quote
base_volume_24h
mark_price / index_price
funding_rate
open_interest_raw
open_interest_unit
source_payload_hash
```

### 8.3 `candle_15m.parquet` と `candle_1m.parquet`

Key:

```text
(provider_id, native_symbol, interval, ts_open)
```

必須列:

```text
open / high / low / close
base_volume
quote_volume
usdt_volume
is_final
ts_available
ts_ingested
source_payload_hash
```

### 8.4 `public_trades.parquet`

```text
trade_id
ts_event / ts_received
price
base_size
quote_size
aggressor_side
batch_id
source_payload_hash
```

### 8.5 `book_snapshots.parquet`

```text
ts_event / ts_received
sequence / previous_sequence
checksum
bid_levels / ask_levels
spread_bps
depth_5bps_quote
depth_10bps_quote
depth_25bps_quote
```

---

## 9. Storage layout

```text
data/crypto_perp/
  raw/
    provider=bitget/
      date=YYYY-MM-DD/
        channel=instruments/
        channel=tickers/
        channel=candle15m/
        channel=candle1m/
        channel=trade/
        channel=books1/
        channel=books15/
  normalized/
    provider=bitget/
      instruments/
      tickers/
      candles/interval=15m/symbol=<symbol>/
      candles/interval=1m/symbol=<symbol>/
      trades/symbol=<symbol>/
      books/symbol=<symbol>/
  checkpoints/
    bitget_refresh.json
    bitget_ws.json
  snapshots/
    universe/<snapshot_id>.json
    data/<snapshot_id>/manifest.json
  events/
    date=YYYY-MM-DD/events.jsonl
  captures/
    <event_id>/capture_manifest.json
  reviews/
    <event_id>/human_review.json
  outcomes/
    <event_id>/outcome.json
  replays/
    <event_id>/execution_replay.json
  reports/
    <report_id>/
      discovery_report.json
      discovery_report.md
      watchdeck.html
```

### 9.1 Writer rules

- raw segment は `part-*.jsonl.gz`。
- temporary file に書き、flush / fsync / close 後に `os.replace`。
- segment close 後に sha256 と row count を manifest へ書く。
- 同一 channel writer は `filelock` で排他する。
- crash 後の `.tmp` は quarantine し、成功 artifact として読まない。
- checkpoint と artifact を同じ transaction とみなさない。artifact commit 後に checkpoint を進める。
- raw を上書きしない。
- normalized は partition 単位で deterministic rebuild 可能にする。

---

## 10. Configuration contract

新規:

```text
configs/crypto_perp/bitget_personal_edge_lab.yaml
schemas/crypto_perp_lab_config.v1.schema.json
```

初期 config:

```yaml
schema_version: crypto_perp_lab_config.v1
provider:
  id: bitget
  base_url: https://api.bitget.com
  product_type: USDT-FUTURES
  timeout_seconds: 10
  max_rest_requests_per_second: 5

heartbeat:
  instrument_interval_seconds: 300
  ticker_interval_seconds: 30
  candle_interval: 15m
  candle_backfill_hours: 336
  finalized_lag_seconds: 5

universe:
  allowed_statuses: [online]
  min_listing_age_days_for_actionable: 7
  max_spread_bps_for_actionable: 35
  classify_liquidity_bands: true
  hard_exclude_by_market_cap: false

screening:
  cadence_seconds: 60
  dedupe_minutes: 360
  max_alerts_per_hour: 5
  detectors:
    slow_pump_74h_v1:
      enabled: true
      return_74h_min: 0.04
      quote_turnover_impulse_74h_min: 0.15
    fast_pump_1h_v1:
      enabled: true
      return_60m_abs_min: 0.05
      robust_return_z_min: 4.0
      turnover_percentile_min: 0.99
    near_miss_v1:
      enabled: true
      lower_bound_fraction: 0.80

candidate_capture:
  max_concurrent: 5
  duration_minutes: 360
  one_minute_backfill_hours: 48
  channels: [trade, books1, books15]
  reconnect_max_delay_seconds: 30

human_review:
  required_for_shadow_accept: true
  default_action_on_timeout: WATCH_ONLY

outcomes:
  horizons_minutes: [5, 15, 60, 240, 720, 1440]
  matched_controls_per_event: 3
  deterministic_seed: 20260620

execution_replay:
  notionals_usd: [25, 50, 100, 250]
  latency_seconds: [5, 15, 30, 60]
  primary_fee_mode: observed_instrument_then_fallback
  fallback_maker_rate: 0.0002
  fallback_taker_rate: 0.0006
  primary_order_style: taker_taker
  do_not_extrapolate_book_depth: true

boundary:
  permits_live_order: false
  live_conversion_allowed: false
  wallet_used: false
  signing_used: false
  exchange_write_used: false
```

数値は discovery seed であり、利益の事前保証ではない。変更時は config hash と trial id を更新する。

---

## 11. CLI contract

CLI は `src/sis/commands/crypto_perp.py` に集約し、domain logic を command 内へ書かない。

### 11.1 Probe

```bash
uv run sis crypto-perp-probe \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --out data/crypto_perp/probes \
  --network
```

Exit:

```text
0: required public capabilities pass
2: config / response / capability failure
3: network disabled or not explicitly opted in
```

### 11.2 One-shot refresh

```bash
uv run sis crypto-perp-refresh \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --through watchdeck
```

`--through`:

```text
universe
tickers
candles
events
watchdeck
```

### 11.3 Long-running recorder

```bash
uv run sis crypto-perp-record \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --duration-minutes 1440
```

- public-only。
- SIGTERM で segment を atomic close。
- restart checkpoint を使用。
- stale / disconnected を成功扱いしない。

### 11.4 Human review

```bash
uv run sis crypto-perp-review \
  --event data/crypto_perp/events/.../event.json \
  --action ACCEPT_SHADOW \
  --size-cap-usd 50 \
  --reason continuation_risk \
  --reviewer operator
```

### 11.5 Outcome / replay settlement

```bash
uv run sis crypto-perp-settle \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --event-id <event-id> \
  --through replay
```

### 11.6 Discovery report

```bash
uv run sis crypto-perp-report \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --start 2026-06-20T00:00:00Z \
  --end 2026-07-20T00:00:00Z
```

### 11.7 Watchdeck

```bash
uv run sis crypto-perp-watchdeck \
  --config configs/crypto_perp/bitget_personal_edge_lab.yaml \
  --top 20 \
  --html data/crypto_perp/reports/latest/watchdeck.html
```

表示列:

```text
symbol
event_family
return_15m / return_60m / return_74h
quote_turnover_anomaly
market_adjusted_return
spread_bps
OI / funding
listing_age
capture_status
human_action
25/50/100/250 fillability
reason_codes
```

---

## 12. Reason code taxonomy

新規:

```text
src/sis/crypto_perp/reason_codes.py
```

最低限:

```text
DATA_MISSING
DATA_STALE
NON_FINAL_CANDLE
DUPLICATE_EVENT
WS_DISCONNECTED
WS_SEQUENCE_GAP
WS_CHECKSUM_FAILED
BOOK_DEPTH_UNKNOWN
BOOK_TOO_THIN
SPREAD_TOO_WIDE
UNIVERSE_STATUS_NOT_ONLINE
LISTING_TOO_RECENT
SYMBOL_REMOVED
SYMBOL_METADATA_CHANGED
FEE_SOURCE_FALLBACK
FUNDING_UNKNOWN
OI_UNIT_UNKNOWN
MARKET_WIDE_MOVE
IDIOSYNCRATIC_MOVE
PUMP_TRIGGERED
NEAR_MISS_CAPTURED
CONTINUATION_EVIDENCE
REVERSAL_EVIDENCE
NO_TRADE_EVIDENCE
HUMAN_VETO
HUMAN_ACCEPT_SHADOW
UNFILLABLE_AT_NOTIONAL
OUTCOME_NOT_MATURED
MATCHED_CONTROL_MISSING
```

同じ意味の自由文を増やさない。

---

## 13. Detailed implementation sequence

### CP-00: Plan, package skeleton, config and schema base

目的:

- 新 domain と境界を作る。
- 既存 Strategy Lab / venue permission を壊さず、public data lab を独立起動できるようにする。

新規対象:

```text
src/sis/crypto_perp/__init__.py
src/sis/crypto_perp/models.py
src/sis/crypto_perp/io.py
src/sis/crypto_perp/reason_codes.py
src/sis/commands/crypto_perp.py
configs/crypto_perp/bitget_personal_edge_lab.yaml
schemas/crypto_perp_lab_config.v1.schema.json
tests/crypto_perp/__init__.py
tests/crypto_perp/test_config.py
docs/strategy_research_lab/15_CRYPTO_PERP_PERSONAL_EDGE_LAB_IMPLEMENTATION_PLAN_2026-06-20.md
```

変更対象:

```text
src/sis/cli.py
docs/strategy_research_lab/README.md
```

実装:

- config Pydantic model は `extra="forbid"`。
- boundary true を拒否。
- all public functions に type hints。
- CLI 登録だけ行い、未実装 subcommand は expose しない。

テスト:

```bash
uv run pytest tests/crypto_perp/test_config.py -q
uv run sis --help
uv run sis crypto-perp-probe --help
```

完了条件:

- valid config が Pydantic と JSON Schema を通る。
- unknown field、負 interval、空 provider、boundary true を拒否。
- existing CLI help contract が壊れない。

停止条件:

- 既存 `VenueId` widening を要求し始めたら設計を戻す。CP-00 では不要。

### CP-01: Bitget public capability probe

目的:

- API key なしで取得可能な機能と実際の response / pagination / limit を記録する。

新規対象:

```text
src/sis/crypto_perp/bitget/__init__.py
src/sis/crypto_perp/bitget/client.py
src/sis/crypto_perp/bitget/probe.py
src/sis/crypto_perp/bitget/normalizers.py
schemas/crypto_perp_provider_probe.v1.schema.json
tests/crypto_perp/test_bitget_client.py
tests/crypto_perp/test_bitget_probe.py
tests/fixtures/crypto_perp/bitget/*.json
```

実装:

- `httpx.AsyncClient`。
- transport injection。
- timeout、429 / 5xx の bounded exponential retry。
- retry 回数、wait、status code を artifact に残す。
- server time と local receive time の差を保存。
- instruments / tickers / candle / OI / funding を probe。
- REST response body は error 時も最大長を制限して raw artifact へ保存。
- candle limit の docs 矛盾を `documentation_anomalies` に保存し、observed behavior を採用。

テスト:

- `pytest-httpx` で 200 / 429 / 500 / timeout / malformed JSON / wrong shape。
- pagination boundary と duplicate cursor。
- network test は通常 CI で実行しない。

Network smoke:

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe --network ...
```

完了条件:

- credentials 無しで required endpoints を probe。
- network opt-in 無しでは外部接続しない。
- response shape drift は PASS にしない。

### CP-02: Universe heartbeat, diff and ticker snapshots

目的:

- Perp の追加、削除、status、fee、tick、minimum order、funding interval の変化を point-in-time で残す。

新規対象:

```text
src/sis/crypto_perp/universe.py
src/sis/crypto_perp/heartbeat.py
src/sis/crypto_perp/storage.py
schemas/crypto_perp_universe_snapshot.v1.schema.json
schemas/crypto_perp_data_snapshot_manifest.v1.schema.json
tests/crypto_perp/test_universe.py
tests/crypto_perp/test_storage.py
tests/crypto_perp/test_heartbeat.py
```

実装:

- instruments snapshot は immutable。
- previous snapshot と field-level diff。
- absent symbol は removed。
- `online` 以外は actionable false。
- liquidity band は hard exclusion ではなく label。
- ticker all-symbol response を one request で保存。
- OI unit が確定できない場合は `unknown` のまま raw value を保持。
- local alert outbox は `sis.ops.alerts.queue_notification` を再利用。

テスト:

- add / remove / status change / tick change / fee change / launch time change。
- same payload は empty diff。
- partial write / stale temp / lock contention / restart。

完了条件:

- 新規上場・削除・状態変化を次回 snapshot で検出。
- history を上書きしない。
- unknown を zero に置換しない。

### CP-03: 15m candle backfill, finalization and quality

目的:

- 全 eligible symbol の screening history を安価に揃える。

新規対象:

```text
src/sis/crypto_perp/bars.py
src/sis/crypto_perp/quality.py
src/sis/crypto_perp/bitget/candles.py
tests/crypto_perp/test_bars.py
tests/crypto_perp/test_quality.py
tests/crypto_perp/test_candle_backfill.py
```

実装:

- default 336h backfill。74h recent + 74h previous + warm-up を満たす。
- market / mark / index candle を source type 別保存。
- unfinished current bar を canonical result に入れない。
- latest two bars を再取得し、revision を検出。
- duplicate key、missing interval、OHLC invariant、negative volume を検査。
- official timeframe を盲信せず `ts_open` alignment を検査。
- gap は forward-fill しない。

テスト:

- pagination overlap / gap / reverse order。
- non-final exclusion。
- revised latest candle。
- zero-trade bar と missing bar の区別。

完了条件:

- detector に必要な history が揃わない symbol は `INCONCLUSIVE_DATA`。
- gap を補間して event を生成しない。

### CP-04: Event engine, matched controls and watchdeck

目的:

- 反落を決めつけず event、near miss、control を記録する。

新規対象:

```text
src/sis/crypto_perp/features.py
src/sis/crypto_perp/events.py
src/sis/crypto_perp/controls.py
src/sis/crypto_perp/watchdeck.py
src/sis/crypto_perp/rendering.py
schemas/crypto_perp_event.v1.schema.json
tests/crypto_perp/test_features.py
tests/crypto_perp/test_events.py
tests/crypto_perp/test_controls.py
tests/crypto_perp/test_watchdeck.py
```

実装:

- `slow_pump_74h_v1` をユーザー定義 seed として実装。
- `fast_pump_1h_v1` は robust median / MAD と turnover percentile を使う。
- market context は BTC、ETH、cross-sectional median、breadth を保存。
- event feature は `information_cutoff_at` より後の行を読まない。
- deterministic event id と dedupe。
- top-N alert cap。
- matched control は liquidity band、hour-of-week、market regime を合わせ、固定 seed で選ぶ。
- near miss を保存。
- event artifact 生成時に local outbox へ alert。
- Rich table と static HTML を生成。

テスト:

- future mutation differential。
- threshold boundary。
- duplicate alert suppression。
- control deterministic selection。
- same symbol / different detector の区別。
- HTML escape。

完了条件:

- price / volume の二変数だけで actionable short を出さない。
- Event は `CAPTURE_REQUESTED` まで。paper/live permission を出さない。

### CP-05: Candidate high-resolution recorder

目的:

- event 発生後だけ 1m、trade、BBO、depth を集める。

新規対象:

```text
src/sis/crypto_perp/capture.py
src/sis/crypto_perp/ws.py
src/sis/crypto_perp/bitget/ws_protocol.py
src/sis/crypto_perp/bitget/ws_recorder.py
src/sis/crypto_perp/bitget/book.py
schemas/crypto_perp_capture_manifest.v1.schema.json
tests/crypto_perp/test_capture_scheduler.py
tests/crypto_perp/test_ws_protocol.py
tests/crypto_perp/test_book.py
tests/crypto_perp/test_ws_restart.py
```

実装:

- max concurrent captures と priority queue。
- `trade`, `books1`, `books15`。
- ping 30s、pong timeout、bounded reconnect。
- subscription request rate / channel count を config で制限。
- snapshot/update、sequence、checksum を検証。
- sequence gap / checksum failure では book を無効化し resync。
- raw message を normalize 前に保存。
- SIGTERM graceful close。
- candidate 1m candle REST backfill を併用。

テスト:

- fixture WS stream replay。
- reconnect、duplicate、out-of-order、gap、checksum fail、resync。
- interrupted gzip segment recovery。
- max concurrent capture。

完了条件:

- gap のある book を fillable と判定しない。
- 24h continuous local smoke で data loss / restart behavior を報告できる。

停止条件:

- 自前 WS の複雑性がテスト可能範囲を超えた場合だけ `pybotters<2.0` spike を別 commit で行う。

### CP-06: Human review and forward outcome ledger

目的:

- 人間判断を結果より前に固定し、判断力も検証する。

新規対象:

```text
src/sis/crypto_perp/review.py
src/sis/crypto_perp/outcomes.py
schemas/crypto_perp_human_review.v1.schema.json
schemas/crypto_perp_outcome.v1.schema.json
tests/crypto_perp/test_review.py
tests/crypto_perp/test_outcomes.py
```

実装:

- review source hash を固定。
- review 後の overwrite は `--replace-existing` と replacement lineage 必須。
- outcome maturity を horizon ごとに判定。
- MFE / MAE、high/low order ambiguity を記録。
- 1m が無い場合、同一 bar で stop / take-profit 両方 hit は optimistic に解決せず `ambiguous_order`。
- matched controls の outcome も settle。

テスト:

- review before / after cutoff。
- stale source hash。
- incomplete horizon。
- ambiguous OHLC ordering。
- replacement lineage。

完了条件:

- hindsight で human action を書き換えた記録が残らない状態を禁止。
- 未成熟 outcome を loss / win として集計しない。

### CP-07: Execution replay, fee, funding and capacity grid

目的:

- 小口で本当に通ったかと net USD を計算する。

新規対象:

```text
src/sis/crypto_perp/fees.py
src/sis/crypto_perp/funding.py
src/sis/crypto_perp/replay.py
src/sis/crypto_perp/capacity.py
schemas/crypto_perp_execution_replay.v1.schema.json
tests/crypto_perp/test_fees.py
tests/crypto_perp/test_funding.py
tests/crypto_perp/test_replay.py
tests/crypto_perp/test_capacity.py
```

実装:

- 25 / 50 / 100 / 250 USD。
- 5 / 15 / 30 / 60 sec latency。
- short entry は bid levels、exit は ask levels。
- minimum order / qty step / tick size を適用。
- observed fee > public instrument fee > fallback。
- funding event を保有区間に厳密適用。
- depth不足は `UNFILLABLE`。残量を mid で埋めない。
- primary taker/taker、stress は spread x2、slippage x2、delay x2、gap exit。
- maker scenario は diagnostic のみ。primary recommendation に使わない。

テスト:

- golden hand calculation。
- partial / unfillable / unknown depth。
- negative maker fee。
- multiple funding events。
- short PnL sign。
- rounding / minimum notional。

完了条件:

- gross return ではなく net USD を notional ごとに出す。
- observed book なしの result は `EXECUTION_REALISM_CHECKED` と呼ばない。

### CP-08: Discovery analysis, competing hypotheses and freeze gate

目的:

- 好きな event だけ選ばず、反落、継続、見送り、control を比較する。

新規対象:

```text
src/sis/crypto_perp/analysis.py
src/sis/crypto_perp/report.py
src/sis/crypto_perp/trials.py
schemas/crypto_perp_discovery_report.v1.schema.json
tests/crypto_perp/test_analysis.py
tests/crypto_perp/test_report.py
tests/crypto_perp/test_trials.py
```

実装:

- event family / symbol / liquidity band / hour / regime breakdown。
- win rate より expected net USD、tail loss、loss concentration を優先。
- matched control / near miss 比較。
- human veto save / missed winner。
- operator time cost。
- detector / universe / fee / provider / threshold の変更を trial として記録。
- PBO / DSR は sample が足りない場合 `not_estimable`。ゼロと表示しない。
- discovery freeze 条件:
  - 30 calendar days かつ 50 matured eligible events を目安にする。
  - 未達なら `INCONCLUSIVE_DATA`。
  - freeze 後は detector config hash を固定し、新しい future window で confirmatory trial。

テスト:

- one huge winner / one huge loser concentration。
- empty / insufficient sample。
- controls missing。
- trial mutation。
- deterministic report。

完了条件:

- 結果は次のいずれか。

```text
CONTINUE_DISCOVERY
FREEZE_CONFIRMATORY_TRIAL
REVISE_DETECTOR
REJECT_EVENT_FAMILY
INCONCLUSIVE_DATA
```

- `FREEZE_CONFIRMATORY_TRIAL` は paper/live permission ではない。

### CP-09: Existing Workbench bridge and limited v2 venue separation

目的:

- 成熟した event family だけ既存 evidence chain へ渡す。

新規対象:

```text
src/sis/crypto_perp/workbench_bridge.py
schemas/market_data_venue_ref.v1.schema.json
schemas/strategy_signal.v2.schema.json
schemas/evaluation_plan.mls.v2.schema.json
tests/crypto_perp/test_workbench_bridge.py
tests/strategy_authoring/test_v2_venue_separation.py
```

変更対象:

```text
src/sis/venues/ids.py
src/sis/venues/capabilities.py
src/sis/venues/suitability.py
src/sis/research/strategy_lab/signal_artifact.py
src/sis/research/strategy_lab/evaluation_plan.py
src/sis/research/strategy_lab/specs.py
src/sis/research/strategy_lab/authoring/contracts/core.py
src/sis/research/strategy_lab/authoring/contracts/spec.py
src/sis/strategy_case_lite/
src/sis/strategy_workbench_viewer/
schemas/strategy_authoring_spec.v2.schema.json
tests/test_venue_capabilities.py
tests/test_venue_suitability.py
tests/strategy_authoring/
tests/strategy_case_lite/
tests/strategy_workbench_viewer/
```

設計:

```text
MarketDataVenueId:
  bitget_public
  hyperliquid_public
  grvt_public
  mexc_public

ExecutionVenueId:
  trade_xyz
  bitget_demo
  bitget_futures
  hyperliquid_perp
  grvt_perp
  mexc_futures
```

- market data known と execution enabled を分ける。
- `bitget_public` は research data source として有効でも paper / live execution は false。
- `bitget_futures` は credentialed read-only / paper / live gate を別々に持つ。
- signal v2 は `source_venue_id` と nullable `intended_execution_venue_id`。
- evaluation plan v2 は `data_snapshot_id`, `universe_snapshot_id`, `execution_model_id`, `fee_snapshot_id`。
- v1 reader を残す。
- new write は v2。
- paper intent へ進む時だけ execution venue 必須。

テスト:

- v1 golden unchanged。
- v2 roundtrip。
- public source cannot imply execution permission。
- bitget_futures remains paper/live disabled until separate evidence。
- NDX / Trade[XYZ] existing paths unchanged。

完了条件:

- event lab result を Strategy Input Contract、Strategy Review、Strategy Case Lite、Workbench Viewer で読める。
- schema widening が live permission を暗黙付与しない。

### CP-10: Reference venue adapters and optional OSS decision

前提:

- CP-01〜CP-08 が完成。
- Bitget event が十分発生し、cross-venue context が判断を変える可能性がある。

候補対象:

```text
src/sis/crypto_perp/reference/hyperliquid.py
src/sis/crypto_perp/reference/grvt.py
src/sis/crypto_perp/reference/mexc.py
tests/crypto_perp/test_reference_venues.py
```

採用順:

1. Hyperliquid public info / WS。
2. GRVT market data / sequence-rich WS。
3. MEXC public price reference。

OSS decision:

| OSS | 判断 |
|---|---|
| `pybotters<2.0` | 24h spike で reconnect / raw preservation / gap handling のコード削減が明確な場合だけ optional extra |
| `ccxt` | symbol / metadata differential check だけ。raw canonical source にしない |
| `cryptofeed` | Bitget + Hyperliquid + GRVT の中心構成を一括で満たさず責務重複するため保留 |
| `freqtrade` | 外部 implementation differential。独立した data truth とは呼ばない |
| `hftbacktest` | queue / latency が利益の本体と判明した場合だけ再評価。戦略を HFT/MM に変えない |

完了条件:

- reference venue 欠損で Bitget primary flow が停止しない。
- reference 不一致を arbitrage order に変換しない。

---

## 14. Test policy

### 14.1 通常 CI

外部 network を使わない。

```bash
uv sync --dev --locked
uv run pytest tests/crypto_perp -q
uv run pytest tests/strategy_authoring -q
uv run pytest tests/strategy_inputs -q
uv run pytest tests/strategy_case_lite -q
uv run pytest tests/strategy_workbench_viewer -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

### 14.2 Test layers

| Layer | 必須内容 |
|---|---|
| model/schema | Pydantic / tracked JSON Schema parity、extra forbid、boundary false |
| REST | success、429、5xx、timeout、malformed、shape drift、pagination |
| WS | snapshot/update、sequence、checksum、gap、reconnect、duplicate、shutdown |
| storage | atomic write、hash、rotation、partial file quarantine、lock、restart |
| time | UTC、event/receive/available、finalized candle、future mutation |
| universe | add/remove/status/metadata/fee/funding interval diff |
| detector | threshold、near miss、dedupe、market context、no lookahead |
| controls | deterministic matched controls、missing control |
| review | source hash、pre-outcome timestamp、replacement lineage |
| outcome | maturity、MFE/MAE、ambiguous OHLC order |
| replay | bid/ask direction、fee/funding、rounding、unfillable、stress |
| analysis | sample insufficiency、tail loss、loss concentration、veto metrics |
| regression | Trade[XYZ]、NDX、Strategy Authoring v1、existing CLI golden |

### 14.3 Network smoke

手動 opt-in のみ。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-probe --network ...
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis crypto-perp-record --duration-minutes 10 ...
```

Network smoke artifact に endpoint、status、latency、clock offset、response shape hash を残す。成功値を tracked docs に固定しない。

### 14.4 Long-running soak

CP-05 完了前に最低一回実行する。

```text
24時間
candidate capture max 5
人工的な disconnect / SIGTERM を含む
restart 後に manifest continuity を確認
```

---

## 15. Acceptance matrix

| ID | Requirement | Verification |
|---|---|---|
| A1 | public network opt-in 無しでは外部接続しない | probe CLI test |
| A2 | Bitget instruments / tickers / candle / OI / funding response を fixture で normalize | REST tests |
| A3 | API docs の limit と observed behavior の差を artifact 化 | probe test |
| A4 | universe add/remove/status/fee/tick/funding interval diff を検出 | universe tests |
| A5 | 15m history に欠損があれば event を成功生成しない | quality tests |
| A6 | slow 74h、fast 1h、near miss、matched controls を同時生成 | event/control tests |
| A7 | event feature は information cutoff 後の行に不変 | no-lookahead differential |
| A8 | candidate-only WS が reconnect/gap/checksum/resync を処理 | WS replay tests |
| A9 | human review は outcome より前の source hash を固定 | review tests |
| A10 | 25/50/100/250 USD と 5/15/30/60s を replay | capacity tests |
| A11 | depth 外挿をせず unfillable/unknown を返す | replay tests |
| A12 | fee/funding/spread/slippage 後の net USD を出す | golden hand calc |
| A13 | reversal/continuation/no-trade/control/near-miss を比較 | analysis tests |
| A14 | operator time、veto save、missed winner、loss concentration を出す | report tests |
| A15 | v1 Strategy Lab / NDX / Trade[XYZ] regression を壊さない | existing tests |
| A16 | public source venue から execution permission が生えない | v2 venue tests |
| A17 | docs metadata / links / CLI catalog が通る | docs / CLI scripts |
| A18 | full gate が通る | `./scripts/check` |

---

## 16. Operational protocol after implementation

### 16.1 毎日

```text
1. instruments / ticker heartbeat
2. universe diff確認
3. event / near miss / control生成
4. top alertだけ人間review
5. candidate high-res capture確認
6. matured outcome / replay settle
7. local watchdeck / brief確認
```

### 16.2 毎週

```text
- alert件数とoperator時間
- data gap / reconnect / checksum failure
- 25/50/100/250 fillability
- biggest loss / missed winner
- human vetoの実績
- config変更のtrial化
```

### 16.3 Discovery から confirmatory への移行

次をすべて満たすまで detector を confirmatory strategy と呼ばない。

```text
minimum 30 calendar days
minimum 50 matured eligible events
minimum 20 symbols, or explicit reason why impossible
matched controls present
primary taker/taker net USD available
loss concentration reported
human decision timestamps valid
config hash frozen
```

未達なら `INCONCLUSIVE_DATA`。

Freeze 後は、同じ未来 window を見て detector threshold を変えない。変更する場合は新 trial / 新 confirmatory window。

---

## 17. Software completion criteria

この計画のソフトウェア実装完了条件:

- CP-00〜CP-09 が実装済み。
- CP-10 は採用条件を満たす reference venue だけ実装し、不要なら deferred decision artifact を残す。
- public Bitget heartbeat を one-shot と long-running の両方で実行できる。
- universe history、event、capture、review、outcome、replay、report が source hash でつながる。
- 事故復旧後に raw segment / checkpoint / manifest が矛盾しない。
- event alert が paper/live order を作らない。
- existing Strategy Operations Workbench で JSON/Markdown evidence を読める。
- existing v1 artifacts を読める。
- normal CI は network / credentials を要求しない。
- `./scripts/check` が通る。

ソフトウェア完了と戦略採用を分ける。収益が出なくても、`REJECT_EVENT_FAMILY` を再現可能に出せればソフトウェアは正しく完成している。

---

## 18. 研究判断の利益基準

単純な win rate で進めない。最低限次を読む。

```text
expected_net_usd_by_notional
median_net_usd_by_notional
p05 / p95 net_usd
max_loss_usd
expected_shortfall_usd
top_1_loss_share_of_total_profit
median_winner_to_max_loser_ratio
tradeable_rate
alert_frequency
operator_minutes
net_usd_per_operator_hour
```

強制的な棄却候補:

```text
maker scenarioでしか利益が出ない
1件の損失がmedian winner 5件以上を消す
primary taker/takerで全notionalが負
25 USDでもdepth不足が頻発
human reviewを毎日長時間要求する
reference venue追加でしか説明できない
特定symbol一つで利益の大半を占める
threshold近傍で符号が反転する
matched controlとの差がない
```

---

## 19. 残る不確実性と停止条件

### 19.1 API仕様

- Bitget v2 / v3 / UTA docs は field / limit / naming が変わり得る。
- docs と runtime response が矛盾した場合は runtime probe を優先し、anomaly を保存する。
- schema drift は silent fallback せず collector を degraded / blocked にする。

### 19.2 出来高

- reported volume は関心、実需、清算、bot、wash を分離しない。
- quote volume 単独で reversal を出さない。
- trade count、aggressor side、spread、depth、OI、funding と分ける。

### 19.3 OI / funding

- OI unit が venue / endpoint ごとに異なる可能性がある。
- unit unknown は raw only。
- funding は高いほど安全な short ではない。

### 19.4 小口 capacity

- 25 USD が通ることは edge の証明ではない。
- 一瞬の book snapshot は実 fill を保証しない。
- latency grid と stress を必須にする。

### 19.5 人間判断

- human veto は hindsight で美化されやすい。
- decision timestamp、source hash、review seconds を必須にする。

### 19.6 Alert fatigue

- max alerts per hour と dedupe を必須にする。
- operator time が利益を上回る event family は reject 対象。

### 19.7 Scope creep

次が起きたら新機能追加を止める。

```text
Bitget vertical slice未完のままreference venueを増やす
Eventが無いのにML/AI optimizerを入れる
BBOで足りるのにfull L2を全銘柄保存する
public-only未安定のままlive adapterを作る
viewerを先に豪華にする
```

---

## 20. Dependencies

### 20.1 Main dependencies

追加不要。現行で足りる。

```text
httpx
tenacity
websockets
pydantic / pydantic-settings
polars
pyarrow
duckdb
filelock
rich
```

### 20.2 Conditional optional dependencies

```toml
[project.optional-dependencies]
crypto-ws = [
  "pybotters<2.0",
]
crypto-interop = [
  "ccxt",
]
```

採用条件:

- `pybotters`: 24h spike で自前実装よりコード量と障害率を下げ、raw preservation と gap detection を壊さない。
- `ccxt`: native API との differential metadata test に限定する。

採用しない:

```text
cryptofeed
OpenBB
MLflow
Great Expectations
full HFT backtester
```

理由は、現時点で operator value より依存・運用・抽象化コストが大きいからである。

---

## 21. External primary references

- Bitget Instruments: https://www.bitget.com/api-doc/uta/public/Instruments
- Bitget Tickers: https://www.bitget.com/api-doc/uta/public/Tickers
- Bitget Candles: https://www.bitget.com/api-doc/uta/public/Get-Candle-Data
- Bitget Open Interest: https://www.bitget.com/api-doc/uta/public/Get-Open-Interest
- Bitget Funding History: https://www.bitget.com/api-doc/uta/public/Get-History-Funding-Rate
- Bitget Public Trades WS: https://www.bitget.com/api-doc/contract/websocket/public/New-Trades-Channel
- Bitget Depth WS: https://www.bitget.com/api-doc/contract/websocket/public/Order-Book-Channel
- Bitget WebSocket limits: https://www.bitget.com/api-doc/common/websocket-intro
- Hyperliquid API: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api
- GRVT Market Data: https://api-docs.grvt.io/market_data_api/
- GRVT Market Data WS: https://api-docs.grvt.io/market_data_streams/
- GRVT Fee Model: https://help.grvt.io/en/articles/9614699-how-does-grvt-s-fee-model-work
- MEXC Futures Market API: https://www.mexc.com/api-docs/futures/market-endpoints/

Research context:

- Risks and Returns of Cryptocurrency: https://www.nber.org/papers/w24877
- Common Risk Factors in Cryptocurrency: https://www.nber.org/papers/w25882
- Trading and Arbitrage in Cryptocurrency Markets: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3171204
- Crypto Wash Trading: https://arxiv.org/abs/2108.10984
- The Probability of Backtest Overfitting: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- The Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

これらの研究は `pump exhaustion short` の収益性を証明しない。観測変数、反証、trial管理の設計参考としてだけ使う。
