# Trade[XYZ] Backtest 実データ定義 2026-05-31

## 結論

Trade[XYZ]バックテストを円滑に行うために集めるべき実データは、理想的な「全部入り市場データ」ではなく、現コードの `run_backtest()` が誤読せず処理できる実務データである。

まず集めるべき market / execution 側の正本は次の5種類に絞る。

```text
1. quote snapshots
2. instrument registry snapshots
3. funding events
4. fee snapshots
5. data quality manifests
```

ただし、これは「バックテストに必要な全データ」ではない。

```text
BT engineを動かすだけ:
  quote snapshots中心で足りる。

Trade[XYZ]実データを誤読せず約定・コストを再現する:
  quote snapshots
  instrument registry snapshots
  funding events
  fee snapshots
  data quality manifests
  が必要。

Repoで戦略を評価する:
  上記に加えて、
  feature panel
  strategy signal artifact
  evaluation plan
  leakage check report
  baseline / benchmark data
  が必要。
```

現時点では、`data/normalized/quotes.parquet` が中心でよい。ただし、戦略評価に進むには、現在不足している `exec_buy_price` / `exec_sell_price` / `funding_interval_minutes` / `oracle_ts_ms` / `raw_payload_ref` / `oi_cap_usage` / `discovery_bound_pct` / `bound_distance` を埋める必要がある。

この文書は、夢想的なデータカタログではなく、現在のコードとTrade[XYZ]仕様から逆算した実務定義である。

## この文書の前提

対象はTrade[XYZ]専用の純粋バックテストである。

本当に必要なのはこれらだけか、という問いへの答えは次である。

```text
v0.1.2 engine smoke:
  ほぼこれだけでよい。

実データの約定・コスト再現:
  market / execution 5種類が必要。

Repoで戦略評価:
  これだけではない。
  feature / signal / evaluation / leakage / baseline 系の正本が追加で必要。
```

対象外:

```text
live order
paper order
wallet
signing
exchange write
short
multi-symbol portfolio
leverage simulation
L2 replay
strategy optimization
```

この「対象外」はv0.1.2の実装対象外という意味である。Repo全体の研究バックテストでは、別途 `feature_panel`、`strategy_signals`、`evaluation_plan`、`leakage_check` が必要になる。

現在のBT投入経路:

```text
data/normalized/quotes.parquet
  -> prepare_quote_rows_for_backtest()
  -> optional build_quote_bars()
  -> run_backtest()
```

重要な制約:

```text
signal fields:
  戦略が見る値

fill snapshot fields:
  仮想約定が見る値

この2つをbar集約時に混ぜない。
```

## 現コードが実際に使う列

この章は、現在のpure backtest engineが直接読むmarket/execution列の定義である。Strategy Lab側の特徴量・signal・評価splitは別章で定義する。

### 1. quote rows からBT入力へ変換する列

実装:

```text
src/sis/backtest/trade_xyz/market_data.py
```

必須:

```text
canonical_symbol or symbol
ts_client or source_ts_ms or recv_ts_ms
mid_price or mark_price or oracle_price or index_price
```

変換後に作る列:

```text
event_ts
symbol
close
event_time_source
close_source
external_price
min_side_depth_10bps_usd
```

実務判断:

```text
close_source default:
  mid_price

event_time_source default:
  ts_client
```

`SPY -> SP500` のような暗黙aliasはしない。symbolが違えば別物として落とす。

### 2. bar集約で分ける列

実装:

```text
src/sis/backtest/trade_xyz/bar_builder.py
```

signal fields:

```text
open
high
low
close
signal_is_tradable
signal_market_status
signal_block_reasons
session_type
```

fill snapshot fields:

```text
fill_is_tradable
fill_market_status
fill_block_reasons
fill_best_bid
fill_best_ask
fill_mid_price
fill_spread_bps
fill_min_side_depth_10bps_usd
fill_bound_distance
fill_oi_cap_usage
fill_taker_fee_bps
fill_maker_fee_bps
fill_fee_mode
```

bar補助列:

```text
bar_max_spread_bps
bar_min_side_depth_10bps_usd
bar_block_reason_union
bar_builder
timeframe
close_source
event_time_source
```

実務判断:

```text
signal row:
  bar内の最後のquote

fill snapshot:
  bar内の最初の約定価格候補を持つquote

約定価格候補:
  exec_buy_price
  exec_sell_price
  best_ask
  best_bid
  ask_price
  bid_price
  mid_price + spread_bps
```

### 3. fill gateが使う列

実装:

```text
src/sis/backtest/trade_xyz/gates.py
src/sis/backtest/engine/fill.py
```

open fillで見る列:

```text
fill price resolved
fee resolved
fill_is_tradable
fill_block_reasons
fill_market_status
fill_spread_bps
fill_min_side_depth_10bps_usd
fill_bound_distance
fill_oi_cap_usage
```

`fill_*` が存在する場合は、通常列より優先する。

open fill禁止理由:

```text
fill_price_unresolved
fill_fee_unresolved
fill_row_is_tradable_false
fill_row_block_reasons_non_empty
fill_row_market_status_not_open
fill_row_spread_bps_above_max
fill_row_min_depth_10bps_usd_below_min
fill_row_bound_distance_above_max
fill_row_oi_cap_usage_above_max
```

close fillは `open` / `close_only` / `unknown_if_fixture` を許す。これはOI cap等で新規建ては禁止だが決済は可能なケースを想定するためである。

### 4. fee modelが使う列

実装:

```text
src/sis/backtest/trade_xyz/cost_model.py
configs/fee_model.trade_xyz.yaml
```

優先順:

```text
fill_taker_fee_bps / fill_maker_fee_bps
  -> taker_fee_bps / maker_fee_bps
  -> fill_fee_mode / fee_mode
  -> configs/fee_model.trade_xyz.yaml fallback
```

実務判断:

```text
fee_mode=unknown かつ fee bps未解決:
  open fillしない

taker_fee_bps / maker_fee_bps がnull:
  fallbackできる場合だけBT可能
  fallbackした事実をmanifest/reportへ残す
```

## 集めるべき正本データ

## 1. Quote Snapshots

保存先:

```text
data/raw/quotes/trade_xyz/YYYY-MM-DD/*.jsonl
data/normalized/quotes.parquet
```

目的:

```text
signal生成
market-like fill
spread/slippage近似
entry/exit gate
data quality監査
```

必須列:

```text
ts_client
source_ts_ms
recv_ts_ms
venue
canonical_symbol
venue_symbol
dex
coin
asset_id
source
raw_payload_sha256
raw_payload_ref
```

価格列:

```text
mid_price
mark_price
oracle_price
index_price
external_price
best_bid
best_ask
bid_price
ask_price
last_trade_price
```

約定近似列:

```text
exec_buy_price
exec_sell_price
spread_bps
bid_depth_10bps_usd
ask_depth_10bps_usd
min_side_depth_10bps_usd
bid_depth_25bps_usd
ask_depth_25bps_usd
depth_10bps_usd
depth_25bps_usd
```

Trade[XYZ]固有列:

```text
oracle_ts_ms
funding_rate
open_interest_usd
oi_cap_usd
oi_cap_usage
discovery_bound_pct
bound_distance
market_status
session_type
is_tradable
block_reasons
source_confidence
venue_quality_score
```

実務上の注意:

```text
mid_price:
  signal用の基本close_source。

mark_price:
  margin / liquidation / unrealized PnL 系の参照価格。
  signal closeとして使う場合は明示する。

oracle_price:
  funding notional計算とmark price構成要素。

external_price:
  外部市場が閉まった後のdiscovery bound基準。

index_price:
  現コードではexternal_price代替として扱える。
  ただし意味はデータ取得元で固定する。

best_bid / best_ask:
  market-like fillの基本価格。

last_trade_price:
  現コードでは未使用だが、mark price検証に必要。
```

欠損許容:

```text
許容しにくい:
  ts_client
  canonical_symbol
  mid_price
  best_bid
  best_ask
  spread_bps
  is_tradable
  market_status
  block_reasons
  fee_mode

短期smokeでは許容:
  exec_buy_price
  exec_sell_price
  oracle_ts_ms
  raw_payload_ref
  oi_cap_usage
  discovery_bound_pct
  bound_distance

戦略評価では許容しない:
  fee bps未解決
  raw payload追跡不能
  coverage不足
```

推奨取得間隔:

```text
最低:
  1分

推奨:
  3秒〜15秒

理由:
  Trade[XYZ] relayer updatesは短周期であり、1分足だけではspread/gate/fill snapshotを取り逃がす。
```

## 2. Instrument Registry Snapshots

保存先:

```text
data/raw/instruments/trade_xyz/YYYY-MM-DD.json
data/normalized/instrument_registry.parquet
```

目的:

```text
symbol仕様の時点管理
session判定
discovery bound判定
OI cap判定
fee mode判定
将来のデータ再現性
```

必須列:

```text
snapshot_ts
canonical_symbol
venue_symbol
dex
coin
asset_id
underlying
asset_class
max_leverage
margin_mode
discovery_bound_pct
open_interest_cap_usd
external_session_hours
internal_session_hours
holiday_calendar_ref
fee_mode
tick_size
lot_size
min_order_size
min_notional_usd
source_url
source_hash
```

重要:

```text
registryは上書きしない。
仕様変更があり得るため、日次または取得runごとにsnapshotとして残す。
```

`configs/instrument_registry.seed.json` はseedであり、実データ正本ではない。BTで使う実データは時点付きregistry snapshotに寄せる。

## 3. Funding Events

保存先:

```text
data/raw/funding/trade_xyz/YYYY-MM-DD.jsonl
data/normalized/funding_events.parquet
```

目的:

```text
funding costをquote row単位ではなく、hourly eventとして再現する。
```

必須列:

```text
funding_event_ts
canonical_symbol
funding_rate
funding_interval_minutes
oracle_price_at_funding
source_ts_ms
recv_ts_ms
raw_payload_sha256
raw_payload_ref
```

補助列:

```text
premium
impact_bid_px
impact_ask_px
impact_notional_usd
interest_rate
funding_cap_rate
```

実務判断:

```text
funding_interval_minutes:
  Trade[XYZ]仕様上はhourlyなので通常60。
  ただしコードには固定値として埋め込まず、データ列に残す。

funding_rate:
  quote snapshotに見える値は可視化用。
  課金はfunding_eventsでのみ行う。

oracle_price_at_funding:
  funding paymentのnotional計算に使う。
```

現在のv0.1.2では、quote rowに `funding_rate` があっても `nullable_zero_v0` では課金しない。これは過大計上を避けるための安全側実装である。

## 4. Fee Snapshots

保存先:

```text
data/raw/fees/trade_xyz/YYYY-MM-DD.json
data/normalized/fee_snapshots.parquet
```

目的:

```text
fee nullをなくす
growth/standard/tier差を再現する
fallback利用を明示する
```

必須列:

```text
snapshot_ts
canonical_symbol
fee_mode
fee_tier
taker_fee_bps
maker_fee_bps
builder_fee_bps
staking_discount_bps
source
source_hash
```

実務判断:

```text
row_resolved:
  quote rowまたはfill snapshotにfee bpsがある状態。
  最も望ましい。

fallback:
  configs/fee_model.trade_xyz.yaml から補完。
  smokeや暫定評価では可。
  戦略評価ではfallback率をreportに出す。

unknown:
  open fill禁止。
```

## 5. Data Quality Manifests

保存先:

```text
data/manifests/quote_snapshot_manifest.json
data/manifests/instrument_registry_manifest.json
data/manifests/funding_manifest.json
```

目的:

```text
どのrawからどのnormalizedを作ったかを追跡する。
後から同じBT結果を再現できるようにする。
```

必須項目:

```text
created_at
collector_version
normalization_version
input_paths
input_file_sha256
output_path
output_file_sha256
row_count
symbol_count
symbols
first_ts
last_ts
null_counts
duplicate_ts_count
out_of_order_count
cadence_gap_count
fee_unresolved_rate
funding_interval_missing_rate
oracle_ts_missing_rate
raw_payload_ref_missing_rate
coverage_by_symbol
```

合格条件:

```text
smoke:
  run_backtest()が落ちない
  data_quality.statusがfailでない
  candidate_result.usable_for_strategy_selection=false

research:
  1銘柄30日以上
  fee unresolved rate = 0
  raw_payload_ref missing rate = 0
  oracle_ts missing rateが説明可能
  coverage gapがreportに出る

strategy evaluation:
  対象timeframeに対して十分なbar数
  funding eventsが別系列で存在
  instrument registry snapshotがperiod全体を覆う
  fee fallback率が明示されている
```

## 6. Feature Panel

保存先:

```text
data/research/feature_panel.parquet
data/manifests/feature_snapshot_manifest.json
```

目的:

```text
戦略が見る特徴量を固定する。
quote / external market / macro / regime 由来の値を、signal生成時点で利用可能だった形にそろえる。
```

Repo内の関連schema:

```text
schemas/feature_snapshot_manifest.v1.schema.json
schemas/data_snapshot_manifest.v1.schema.json
plan/marketlens_strategy_research_lab_migration_pack/06_SCHEMA_CONTRACTS.md
```

必須列:

```text
feature_ts
canonical_symbol
real_market_symbol
timeframe
source_ts_max
feature_version
```

価格・リターン特徴量:

```text
close
return_5m
return_15m
return_30m
return_1h
return_4h
return_1d
realized_vol_15m
realized_vol_1h
realized_vol_1d
atr_like_range
```

流動性・venue quality特徴量:

```text
spread_bps
min_side_depth_10bps_usd
venue_quality_score
source_confidence
quote_age_ms
oracle_age_ms
tracking_diff_bps
mark_oracle_diff_bps
mark_external_diff_bps
```

regime特徴量:

```text
vix_level
vix_change
rates_2y
rates_10y
rates_10y_2y_spread
dxy
qqq_return
spy_return
sector_or_theme_return
macro_event_blackout
earnings_blackout
session_bucket
```

戦略候補との対応:

```text
qqq_trend_rates_vix:
  qqq_return
  vix_level
  vix_change
  rates_10y
  rates_10y_2y_spread
  macro_event_blackout

trend_orderbook_confirmation:
  close / returns
  spread_bps
  min_side_depth_10bps_usd
  mark_oracle_diff_bps
  venue_quality_score

regime_riskguard_trend:
  trend returns
  realized_vol
  vix_level
  macro_event_blackout
  source_confidence
  venue_quality_score
```

実務判断:

```text
feature_ts:
  signal生成時刻。

source_ts_max:
  そのrowの特徴量を作るために使った最大source timestamp。
  source_ts_max > feature_ts ならリーク。

feature_version:
  計算式を変えたら必ず変える。

feature_build_config_hash:
  rolling window, timezone, session filter, fill policyを固定する。
```

これがないと、quote execution dataだけで「戦略を評価した」と錯覚する。実際にはbreakout smokeしか評価できない。

## 7. Strategy Signal Artifact

保存先:

```text
data/research/strategy_signals.parquet
data/research/strategy_signals.jsonl
data/manifests/strategy_signal_manifest.json
```

目的:

```text
戦略がいつ、何を、なぜ、どの特徴量snapshotから出したかを固定する。
```

Repo内の関連schema:

```text
schemas/strategy_signal.v1.schema.json
schemas/strategy_signal_manifest.v1.schema.json
```

必須列:

```text
signal_id
generated_at
strategy_id
strategy_family
strategy_version
trial_id
parameter_hash
ts_signal
timeframe
execution_venue
execution_symbol
real_market_symbol
side
confidence
feature_snapshot_ref
quote_ref
reason_codes
block_reasons
```

実務判断:

```text
signals.csv:
  legacy export扱い。
  正本にしない。

strategy_signals.parquet/jsonl:
  正本。

execution_symbol:
  Trade[XYZ]で約定させるsymbol。

real_market_symbol:
  QQQ / SPY / VIX等、特徴量側のsymbol。
```

`QQQ signal` を `XYZ100` に流すようなsymbol bindingは、必ずmanifestに残す。暗黙変換は禁止。

## 8. Evaluation Plan / Leakage Check

保存先:

```text
data/research/evaluation_plan.json
data/research/leakage_check_report.json
data/research/trial_registry.jsonl
```

目的:

```text
どのsplit、purge、embargo、label horizon、cost stressで評価したかを固定する。
```

Repo内の関連schema:

```text
schemas/evaluation_plan.mls.v1.schema.json
plan/marketlens_strategy_research_lab_migration_pack/contracts/LEAKAGE_CHECK_REPORT.md
```

必須項目:

```text
evaluation_plan_id
target_venue
split_method
label_horizon_minutes
purge_minutes
embargo_minutes
era_unit
quote_data_path
feature_panel_path
cost_model_path
min_trade_count
primary_metric
secondary_metrics
forbidden_claims
```

leakage check項目:

```text
feature_ts <= ts_signal
source_ts_max <= ts_signal
quote_ts <= ts_signal
label horizon overlapなし
purge適用
embargo適用
train / validation / test のera重複なし
```

実務判断:

```text
これがないrun:
  smoke / plumbing確認。

これがあるrun:
  research評価候補。

これがあり、十分なcoverageとtrade countがあるrun:
  戦略比較候補。
```

## 9. Baseline / Benchmark Data

保存先:

```text
data/research/benchmarks.parquet
data/research/baseline_results.json
```

目的:

```text
戦略PnLが単なる市場上昇、低頻度偶然、cost未反映、session偏りでないかを確認する。
```

最低限必要:

```text
buy_and_hold
flat_no_trade
random_entry_same_trade_count
breakout_default
cost_stressed
slippage_stressed
```

参照データ:

```text
SP500 / XYZ100 / NVDA / TSLA のTrade[XYZ] quote bars
対応するreal market reference bars
VIX / rates / macro blackout calendar
session calendar
```

実務判断:

```text
baselineに勝っていない:
  戦略として採用しない。

cost_stressedで消える:
  executionに弱い戦略として扱う。

random_entryと同程度:
  edge未確認。
```

## 現在データの評価

対象:

```text
data/normalized/quotes.parquet
```

確認結果:

```text
rows:
  970

period:
  2026-05-27T02:23:16.768478Z
  から
  2026-05-28T14:45:01.519891Z

symbols:
  SP500 122
  XYZ100 122
  NVDA 122
  AAPL 122
  MSFT 122
  AMD 60
  META 60
  AMZN 60
  EWJ 60
  GOOGL 60
  TSLA 60
```

そろっている:

```text
canonical_symbol
ts_client
source_ts_ms
recv_ts_ms
mid_price
mark_price
oracle_price
index_price
best_bid
best_ask
spread_bps
min_side_depth_10bps_usd
funding_rate
open_interest_usd
fee_mode
market_status
session_type
is_tradable
block_reasons
source_confidence
venue_quality_score
raw_payload_sha256
```

不足:

```text
exec_buy_price:
  全null

exec_sell_price:
  全null

funding_interval_minutes:
  全null

oracle_ts_ms:
  全null

raw_payload_ref:
  全null

oi_cap_usage:
  missing

discovery_bound_pct:
  missing

bound_distance:
  missing

taker_fee_bps / maker_fee_bps:
  310 rows null
```

判断:

```text
smoke:
  可

plumbing / artifact検証:
  可

戦略評価:
  不足

funding込み評価:
  不可

discovery bound / OI cap gate込み評価:
  不足
```

## 推奨する収集順

### Phase 1: SP500だけを厚くする

目的:

```text
システム全体の誤読を潰す。
```

対象:

```text
SP500
```

期間:

```text
最低30日
推奨90日
```

間隔:

```text
3秒〜15秒 quote snapshots
```

完了条件:

```text
raw_payload_ref missing rate = 0
fee unresolved rate = 0
funding_interval_minutes populated
oracle_ts_ms populated or reason documented
```

### Phase 2: registry snapshotを導入する

目的:

```text
仕様変更とsession差をBTへ反映する。
```

対象:

```text
SP500
XYZ100
NVDA
TSLA
```

完了条件:

```text
discovery_bound_pctが入る
oi_cap_usdが入る
oi_cap_usageを計算できる
external/internal sessionを区別できる
holiday closureを判定できる
```

### Phase 3: funding eventsを別系列化する

目的:

```text
fundingの過大/過小計上を避ける。
```

完了条件:

```text
funding_events.parquetが作れる
funding_event_tsがhourly cadence
oracle_price_at_fundingが入る
quote rowからのfunding課金をしない
```

### Phase 4: 銘柄を増やす

優先順:

```text
1. SP500
2. XYZ100
3. NVDA
4. TSLA
5. AAPL / MSFT / AMZN / GOOGL / META
6. GOLD / OIL
```

理由:

```text
SP500:
  index系の基準。

XYZ100:
  Trade[XYZ]固有性が高い。

NVDA / TSLA:
  単名株でspread/session/gateの弱点が出やすい。

GOLD / OIL:
  商品sessionとdiscovery bound検証に使える。
```

### Phase 5: feature panelを作る

目的:

```text
Repoで実際に比較したい戦略を評価できる状態にする。
```

最初に作る特徴量:

```text
SP500 / XYZ100:
  return_30m
  return_1h
  return_4h
  realized_vol_1h
  spread_bps
  venue_quality_score

qqq_trend_rates_vix用:
  qqq_return_1h
  qqq_return_4h
  vix_level
  vix_change
  rates_10y
  rates_10y_2y_spread

riskguard用:
  macro_event_blackout
  earnings_blackout
  source_confidence
  tracking_diff_bps
```

完了条件:

```text
feature_panel.parquetが作れる
feature_snapshot_manifest.jsonが作れる
source_ts_max <= feature_ts を検査できる
missing_rate_by_featureが出る
```

### Phase 6: signalと評価計画を固定する

目的:

```text
結果の良し悪し以前に、何を評価したかを再現できるようにする。
```

完了条件:

```text
strategy_signals.parquet/jsonlが作れる
strategy_signal_manifest.jsonが作れる
evaluation_plan.jsonが作れる
leakage_check_report.jsonが作れる
trial_registry.jsonlにrunを残せる
```

このPhaseなしで出た成績は、戦略評価ではなくsmokeまたは手元実験として扱う。

## 受け入れ基準

### Smoke用

```text
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --event-time-source ts_client \
  --auto-small-lookback
```

合格:

```text
backtest_report.html が出る
data_quality.status != fail
candidate_result.smoke_only = true
candidate_result.usable_for_strategy_selection = false
```

### Research用

合格:

```text
対象symbolごとに30日以上
1h barで最低500本以上
fee unresolved rate = 0
raw_payload_ref missing rate = 0
duplicate event_ts per symbol = 0
funding_eventsあり
instrument registry snapshotあり
feature_panelあり
feature_snapshot_manifestあり
```

### Strategy Evaluation用

合格:

```text
対象symbolごとに90日以上
30m/1h/4h/1dでcoverageを確認
funding costをeventとして計上可能
session/holiday/maintenanceを区別可能
discovery bound / OI cap gateが有効
fallback fee率がreportに出る
strategy_signal_manifestがある
evaluation_planがある
leakage_check_reportがpassしている
baseline / benchmark と比較されている
```

## 外部仕様からの根拠

Trade[XYZ] docsで確認した実務上重要な仕様:

```text
XYZ perps:
  HyperCore上でmatching, order types, funding, liquidation, ADLが管理される。
  独自要素はoracle price, mark price, external price。

mark price:
  oracle price
  oracle + 150秒EWMA(mid-oracle差)
  median(best bid, best ask, last trade)
  のmedian。

funding:
  hourly。
  payment = position_size * oracle_price * funding_rate。
  oracle priceをnotional計算に使う。

external price:
  external market open時はoracle priceと同じ。
  external market closed時はexternal close priceに固定される。

discovery bounds:
  internal pricing session中の価格発見範囲を制限する。
  v2ではre-anchorがあり得る。

specification index:
  symbolごとにmax leverage, discovery bound, margin mode,
  external/internal session hours, OI capが定義される。

Hyperliquid info endpoint:
  HIP-3 candleSnapshotでは coin に dex prefix が必要な場合がある。
  例: xyz:XYZ100
  candleSnapshotは最近5000本制限がある。
```

参照:

```text
https://docs.trade.xyz/perp-mechanics/overview
https://docs.trade.xyz/perp-mechanics/mark-price
https://docs.trade.xyz/perp-mechanics/funding
https://docs.trade.xyz/perp-mechanics/fees
https://docs.trade.xyz/perp-mechanics/external-price
https://docs.trade.xyz/perp-mechanics/discovery-bounds
https://docs.trade.xyz/consolidated-resources/specification-index
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
```

## 抜け・漏れ・誤謬リスク

### 1. last_trade_price欠損

`mark_price` の検証に必要。現コードは未使用だが、将来のmark監査では必須。

対応:

```text
quote snapshotに last_trade_price を追加する。
```

### 2. fundingをquote rowで課金するリスク

quoteごとに課金すると過大計上になる。

対応:

```text
funding_events.parquet を別に作る。
run_backtest側ではfunding eventだけを課金対象にする。
```

### 3. external sessionとinternal sessionの混同

`market_status=open` だけでは足りない。外部市場が閉まっているが、Trade[XYZ]内部では取引される時間がある。

対応:

```text
external_session_open
internal_session_open
maintenance_window
holiday_closure
```

をregistryまたはsession calendarに持つ。

### 4. OI capの誤読

OI cap到達時は新規建て不可でも決済は可能な場合がある。

対応:

```text
is_tradable:
  全体の簡易判定

market_status:
  open / close_only / closed / paused

block_reasons:
  entry禁止理由
```

を分ける。

### 5. fee fallbackを実feeと誤認するリスク

`configs/fee_model.trade_xyz.yaml` fallbackは便利だが、実feeではない。

対応:

```text
fee_source:
  row
  fee_snapshot
  config_fallback
  unresolved
```

をartifactに残す。

### 6. candleSnapshotを長期データ正本にするリスク

Hyperliquidのcandle snapshotは最近5000本制限がある。長期BTの正本には向かない。

対応:

```text
raw quote snapshotsを自前保存する。
candleSnapshotは検算用に限定する。
```

### 7. dex prefixを落とすリスク

HIP-3では `xyz:XYZ100` のようにdex prefixが必要な場合がある。

対応:

```text
canonical_symbol:
  SP500

venue_symbol:
  xyz:SP500 など取得元の正本表記

dex:
  xyz

coin:
  SP500
```

を分けて保存する。

### 8. market/execution dataだけで戦略評価したと誤認するリスク

quote snapshots、registry、funding、feeがそろっても、それだけでは戦略の優位性は評価できない。現v0.1.2の `run_backtest()` はclose breakoutの最小loopであり、`qqq_trend_rates_vix` や `regime_riskguard_trend` の特徴量は直接読まない。

対応:

```text
feature_panel
strategy_signal_artifact
evaluation_plan
leakage_check_report
baseline / benchmark
```

を別正本として持つ。

### 9. real market reference不足

Trade[XYZ]が参照する株式・指数・商品は、外部市場のsession、休場、出来高、価格更新遅延に影響される。Trade[XYZ] quoteだけでは、参照市場との乖離やtracking qualityを十分に判断できない。

対応:

```text
real_market_bars
real_market_session_calendar
macro_event_calendar
earnings_calendar
rates / VIX / DXY などのregime data
```

をfeature panel側で持つ。

### 10. corporate action / symbol continuity不足

単名株系perpでは、株式分割、ティッカー変更、参照先変更、上場廃止、holidayなどの影響を受ける可能性がある。perp価格だけを見ると連続系列に見えても、外部参照側のイベントで特徴量が壊れることがある。

対応:

```text
corporate_action_calendar
symbol_mapping_history
reference_source_history
```

をregistryまたはfeature manifestに残す。

## 次にやること

実装の次スライス:

```text
1. schemas/instrument_registry_snapshot.v1.schema.json を作る
2. schemas/funding_event.v1.schema.json を作る
3. schemas/fee_snapshot.v1.schema.json を作る
4. schemas/feature_panel_snapshot.v1.schema.json または既存 feature_snapshot_manifest を拡張する
5. schemas/strategy_signal_manifest.v1.schema.json を実運用列まで強化する
6. schemas/evaluation_plan.mls.v1.schema.json を実運用列まで強化する
7. data quality manifestに missing rate を追加する
8. collect-trade-xyz-quotes の raw_payload_ref 保存を必須化する
```

ただし、最初の運用改善はschema追加よりも、SP500の長期quote収集である。まずは30日分のSP500を安定収集する。
