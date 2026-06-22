<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Artifact / Data Contract

## 1. 共通規則

### 1.1 Pydantic / JSON Schema

- Pydantic modelがruntime validationの正本。
- tracked JSON Schemaは外部互換・artifact検査用。
- すべて `extra="forbid"`。
- floatで金額・価格・数量を保持しない。raw stringまたは`Decimal`でparseし、Parquetではdecimal型または明示scale整数を使う。

### 1.2 Common envelope

全JSON artifactに必須:

```text
schema_version
artifact_id
created_at
producer
  tool: sis
  command
source_refs[]
  path
  sha256
  schema_version
boundary
  permits_live_order
  live_conversion_allowed
  wallet_used
  signing_used
  exchange_write_used
  live_order_submitted
```

通常artifactのboundaryはすべてfalse。live measurement artifactだけ`exchange_write_used=true`と`live_order_submitted=true`を事実として記録できるが、`permits_live_order`や`live_conversion_allowed`をpermissionとしてtrueにしない。

### 1.3 Time

必須時刻:

```text
ts_event       取引所が付けた市場event時刻
ts_received    local processが受信した時刻
ts_ingested    durable storageへcommitした時刻
ts_available   strategy/operatorが利用可能になった時刻
information_cutoff_at  decisionが参照できる最大時刻
decision_at    判断を確定した時刻
settled_at     outcomeを確定した時刻
```

- UTC awareのみ。
- serializationはISO 8601 `Z`。
- `ts_event <= ts_received <= ts_ingested`を原則とする。clock skewがある場合はviolationではなく`clock_offset_ms`を記録し、順序判定を補正する。
- `decision`は`information_cutoff_at`より後に作成できるが、参照sourceのmax timestampはcutoff以下でなければならない。

### 1.4 ID

```text
provider_snapshot_id = sha256(provider | endpoint | request | received_bucket | raw_sha)
universe_snapshot_id = sha256(provider | product_type | observed_at | instruments_sha)
event_id = sha256(provider | symbol | detector_version | first_trigger_bucket)
decision_id = sha256(event_id | decision_version | decision_at | actor)
measurement_id = sha256(event_id | client_oid | order_attempt)
```

ID生成関数を一箇所へ集約する。

## 2. Config `crypto_perp_lab_config.v1`

必須群:

```text
provider
network_policy
heartbeat
universe
screening
candidate_capture
outcomes
execution_replay
capital
boundary
```

重要validation:

- `capital_ceiling_usd <= 3000`。
- `measurement_notional_max_usd <= 25` for MVP-C。
- `allow_top_up=false`。
- `max_open_positions=1` for tiny live。
- network default deny。
- boundary false。
- detector windowがhistory backfill以内。

## 3. `crypto_perp_provider_probe.v1`

```text
probe_id
provider_id
base_url
started_at / finished_at
network_attempted
credentials_used
clock_offset_ms
endpoint_results[]
  endpoint_id
  method
  path
  params_redacted
  status_code
  latency_ms
  response_shape_hash
  row_count
  observed_page_limit
  pagination_behavior
  rate_limit_headers
  error_class
  error_excerpt
capabilities
  instruments
  tickers
  candle_1m
  candle_15m
  mark_candle
  index_candle
  funding_history
  open_interest
  public_trade_ws
  books1_ws
  books15_ws
documentation_anomalies[]
```

## 4. `crypto_perp_universe_snapshot.v1`

```text
snapshot_id
provider_id
product_type
observed_at
instruments[]
  native_symbol
  canonical_symbol
  base_asset
  quote_asset
  type
  status
  launch_time
  off_time
  limit_open_time
  maker_fee_rate
  taker_fee_rate
  price_precision
  quantity_precision
  price_multiplier
  quantity_multiplier
  min_order_qty
  min_order_amount
  max_market_order_qty
  min_leverage
  max_leverage
  funding_interval_hours
  metadata_hash
eligibility[]
  native_symbol
  eligible_for_screening
  eligible_for_measurement
  liquidity_band
  reason_codes[]
diff
  added[]
  removed[]
  status_changed[]
  metadata_changed[]
```

`removed`は前snapshotに存在し現在消えたsymbolを含む。

## 5. Market tables

### `instrument_snapshots.parquet`

Key:

```text
(provider_id, native_symbol, observed_at)
```

### `ticker_snapshots.parquet`

Key:

```text
(provider_id, native_symbol, ts_event, ts_received)
```

Columns:

```text
last_price
bid1_price
ask1_price
bid1_size
ask1_size
spread_bps
price_change_24h
volume_24h_base
turnover_24h_quote
index_price
mark_price
funding_rate
open_interest_raw
open_interest_unit
source_payload_sha256
```

### `candles.parquet`

Key:

```text
(provider_id, native_symbol, candle_type, interval, ts_open)
```

Columns:

```text
open high low close
base_volume
quote_turnover
is_final
ts_available
ts_ingested
source_payload_sha256
revision_number
```

### `public_trades.parquet`

```text
provider_id
native_symbol
trade_id
ts_event
ts_received
price
base_size
quote_size
aggressor_side
source_payload_sha256
```

### `book_snapshots.parquet`

```text
provider_id
native_symbol
channel
ts_event
ts_received
action
seq
checksum
checksum_valid
bids: list<struct<price,qty>>
asks: list<struct<price,qty>>
spread_bps
depth_5bps_quote
depth_10bps_quote
depth_25bps_quote
```

## 6. `crypto_perp_event.v1`

```text
event_id
event_family
provider_id
native_symbol
canonical_symbol
first_detected_at
information_cutoff_at
universe_snapshot_id
market_snapshot_id
detector_version
detector_config_hash
features_at_detection
  return_15m
  return_60m
  return_74h
  recent_turnover
  previous_turnover
  turnover_impulse
  robust_return_z
  turnover_percentile
  spread_bps
  mark_index_basis_bps
  funding_rate
  open_interest_raw
market_context
  btc_return
  eth_return
  cross_section_median_return
  breadth
  market_adjusted_return
data_quality
  status
  reason_codes[]
capture_request
  requested
  channels[]
  duration_minutes
status
```

Eventには売買方向を入れない。

## 7. `crypto_perp_capture_manifest.v1`

```text
capture_id
event_id
backend: native | pybotters
started_at / ended_at
channels[]
segments[]
  path
  sha256
  row_count
  min_ts
  max_ts
subscription_attempts
reconnect_count
sequence_gap_count
checksum_failure_count
resync_count
coverage_status
known_gaps[]
```

## 8. `crypto_perp_decision.v1`

```text
decision_id
event_id
decision_version
actor_type: system | human
actor_id
decision_at
information_cutoff_at
action
  REVERSAL_SHORT
  CONTINUATION_LONG
  NO_TRADE
  UNKNOWN
  CAPTURE_ONLY
size_cap_usd
reason_codes[]
notes
review_seconds
source_event_path
source_event_sha256
replacement_of
```

Outcome情報をfieldへ入れない。

## 9. `crypto_perp_outcome.v1`

```text
outcome_id
event_id
settled_at
horizons[]
  horizon_minutes
  matured
  reference_price
  close_price
  raw_return
  short_return_before_cost
  long_return_before_cost
  mfe_long
  mae_long
  mfe_short
  mae_short
  high_first_low_first
  market_adjusted_return
near_miss_refs[]
known_gaps[]
```

## 10. `crypto_perp_account_snapshot.v1`

```text
account_snapshot_id
observed_at
account_equity_usd
available_usd
unrealized_pnl_usd
margin_mode
position_mode
positions[]
open_orders[]
fee_snapshot
credential_scope_attestation
  read_enabled
  trade_enabled
  withdrawal_disabled_confirmed
  ip_restriction_confirmed
  attested_by
  attested_at
```

secret自体は保存しない。

## 11. `crypto_perp_order_preview.v1`

```text
preview_id
event_id
created_at
symbol
side
position_side
order_type
requested_notional_usd
normalized_qty
reference_price
limit_price
margin_mode
leverage
estimated_margin_usd
estimated_fee_usd
min_order_checks
precision_checks
account_checks
client_oid
expires_at
blocked
block_reasons[]
```

## 12. `crypto_perp_live_measurement.v1`

```text
measurement_id
event_id
preview_id
client_oid
armed_at
submitted_at
acknowledged_at
first_fill_at
closed_at
entry
  side
  requested_qty
  filled_qty
  average_fill_price
  fee_usd
exit
  reduce_only
  requested_qty
  filled_qty
  average_fill_price
  fee_usd
funding_usd
realized_pnl_usd
net_pnl_usd
latency_metrics
order_state_transitions[]
rejections[]
position_reconciled
flat_confirmed
emergency_actions[]
```

## 13. `crypto_perp_cash_ledger.v1`

Append-only records:

```text
record_id
ts
record_type
  DEPOSIT
  WITHDRAWAL
  REALIZED_PNL
  TRADING_FEE
  FUNDING
  INFRA_COST
  ADJUSTMENT
amount_usd
measurement_id
external_reference
notes
```

Summary:

```text
total_deposits_usd
total_withdrawals_usd
realized_pnl_usd
fees_usd
funding_usd
infra_cost_usd
current_liquidatable_equity_usd
net_cash_usd
```

## 14. `crypto_perp_execution_replay.v1`

Direction-neutral:

```text
replay_id
event_id
side
entry_model
exit_model
notional_results[]
  notional_usd
  latency_seconds
  entry_book_side
  exit_book_side
  entry_vwap
  exit_vwap
  entry_slippage_bps
  exit_slippage_bps
  fee_usd
  funding_usd
  gross_pnl_usd
  net_pnl_usd
  fill_status
assumption_codes[]
calibration_version
```

Fill status:

```text
FILLED
PARTIAL
UNFILLABLE
UNKNOWN_DEPTH
DATA_GAP
```

## 15. `crypto_perp_tournament_report.v1`

```text
report_id
window_start / window_end
config_hash
trial_ids[]
event_counts
branch_results
  reversal_short
  continuation_long
  no_trade
notional_results
actual_measurement_results
cash_summary
operator_metrics
loss_concentration
near_miss_comparison
data_quality_summary
recommendation
required_actions[]
```

Recommendation:

```text
KEEP_MEASURING
FREEZE_CONFIRMATORY_RULE
REVISE_EVENT_DETECTOR
REJECT_REVERSAL
REJECT_CONTINUATION
REJECT_EVENT_FAMILY
INCONCLUSIVE_DATA
```

## 16. Storage layout

```text
data/crypto_perp/
  raw/provider=bitget/date=YYYY-MM-DD/channel=<channel>/part-*.jsonl.gz
  normalized/provider=bitget/<table>/date=YYYY-MM-DD/*.parquet
  snapshots/universe/<snapshot_id>.json
  snapshots/market/<snapshot_id>.json
  events/<event_id>/event.json
  events/<event_id>/event.md
  events/<event_id>/capture_manifest.json
  decisions/<event_id>/*.json
  outcomes/<event_id>/outcome.json
  account/<snapshot_id>.json
  previews/<preview_id>.json
  measurements/<measurement_id>.json
  ledgers/cash_ledger.jsonl
  reports/<report_id>/tournament_report.json
  reports/<report_id>/tournament_report.md
  checkpoints/<collector>.json
  quarantine/
```

## 17. Atomicity

- raw segmentはtmpへ書き、flush/fsync/close後`os.replace`。
- segment commit後にmanifest、最後にcheckpoint。
- `.tmp`とchecksum不一致はquarantine。
- checkpointだけ進んだ状態を成功扱いしない。
- append-only artifactのreplaceはreplacement lineage必須。
