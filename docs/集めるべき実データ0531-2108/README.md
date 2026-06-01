<!--
作成日: 2026-05-31_21:08 JST
更新日: 2026-06-01_17:15 JST
-->

# Trade[XYZ] Backtest 実データ定義 2026-05-31

更新注記: 2026-06-01_17:15 JST

現在のstatus snapshotは次を正とする。

```text
data/ops/trade_xyz_collection_status.json generated_at:
  2026-06-01T06:03:43.402583+00:00

readiness:
  NOT_READY

failing_requirements:
  quote_coverage
  real_market_reference

known_gap_requirements:
  oracle_timestamp_provenance

account_specific_fee:
  pass
```

この文書は必要データの定義書であり、最新statusの詳細は
`docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` と
`docs/TRADE_XYZ_REAL_DATA_COLLECTION_STATUS_APPENDIX_2026-06-01.md` を優先する。

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

現時点では、`data/normalized/quotes.parquet` が中心でよい。ただし、戦略評価に進む前に、quote coverage、fee source、funding event、oracle timestamp、session state、OI cap / discovery bound の欠損率を manifest で確認する必要がある。欠損している列を source / recv / client time などで偽装して埋めてはいけない。

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
oracle_ts_source
oracle_ts_status
oracle_ts_missing_reason
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

oracle_ts_ms:
  oracle payload内の時刻fieldが観測できた場合だけ入れる。
  l2Bookのsource_ts_msやcollector受信時刻をoracle_ts_msとして流用しない。

oracle_ts_missing_reason:
  API payloadにoracle timestamp fieldがない場合、または値が不正な場合の理由。
  戦略評価ではmissing rateと理由をmanifestで確認する。
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

現行Repoでは、既存 registry JSON から以下を生成できる。

```bash
uv run sis build-trade-xyz-reference-data
```

出力:

```text
data/normalized/instrument_registry_snapshots.parquet
data/normalized/session_calendar_snapshots.parquet
data/manifests/instrument_registry_manifest.json
data/manifests/session_calendar_manifest.json
```

注意:

```text
この snapshot は現時点では registry JSON 由来。
外部session/holiday/tick/lot/min notional が未収集なら null として残る。
null を実データとして補完済みと誤読しない。
```

## 3. Session Calendar Snapshots

保存先:

```text
data/raw/sessions/trade_xyz/YYYY-MM-DD.jsonl
data/normalized/session_calendar_snapshots.parquet
data/manifests/session_calendar_manifest.json
data/raw/sessions/trade_xyz_state/YYYY-MM-DD.jsonl
data/normalized/session_state_observations.parquet
data/manifests/session_state_manifest.json
```

目的:

```text
external session / internal session / holiday / maintenance を未確認のまま
backtest内で通常取引時間として誤読しない。
```

必須列:

```text
snapshot_ts
canonical_symbol
venue_symbol
real_market_symbol
asset_class
external_session_ref
internal_session_ref
external_session_open
internal_session_open
maintenance_window
holiday_closure
close_only_allowed
source
source_hash
data_status
missing_fields
notes
```

現行Repoでは、registry JSON の `external_session` / `internal_session` から
session calendar snapshot を生成できる。

```bash
uv run sis build-trade-xyz-reference-data
```

注意:

```text
現時点の session calendar snapshot は registry由来の参照名を保存する段階。
external_session_open / internal_session_open / maintenance_window / holiday_closure は
観測済みの実状態ではないため null のまま残す。

session_calendar_manifest.json の missing_field_counts を見て、
どのsymbolで何が未取得かを確認する。
null を「開いている」「閉じている」と読まない。
```

さらに、raw quoteの `ts_client` を使って、session state observation を生成できる。

```bash
uv run sis build-trade-xyz-session-state
```

出力:

```text
data/raw/sessions/trade_xyz_state/YYYY-MM-DD.jsonl
data/normalized/session_state_observations.parquet
data/manifests/session_state_manifest.json
```

現行実装で扱えるもの:

```text
external_session_open:
  Trade[XYZ] docs の 23/5 または 24/5 session specification 由来。

holiday_closure:
  exchange_calendars の non-session dayをproxyとして使う。

internal_session_open:
  supported symbolsではTrade[XYZ] docsのinternal/closed intervalからspec-derivedで生成。

maintenance_window:
  SP500 / XYZ100ではTrade[XYZ] docsのdaily maintenance windowからspec-derivedで生成。

session_type:
  regular / closed / unknown。
```

注意:

```text
source=docs_trade_xyz_specification_index:
  Trade[XYZ] docs由来の仕様派生値。API観測値ではない。

data_status=spec_derived:
  実時刻に対して仕様から導出した値。

source=exchange_calendars:
  unsupported symbolなど、仕様派生できない場合のfallback。

readiness:
  session_state_manifest.json の row_count だけでは完了扱いしない。
  session_type_counts が空なら session_state は fail。
  internal_session_open / maintenance_window の欠損は known gap として扱い、
  open / closed に読み替えない。
```

## 4. Funding Events

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

readiness:

```text
funding_history_join_manifest.json は row_count だけでは完了扱いしない。
usable_as_backtest_funding_event=true、row_count>0、かつ skipped に非ゼロ項目がない場合だけ pass。
skipped.missing_oracle_quote_within_lag などが残る場合は known gap として扱う。
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

現行Repoでは、raw quote JSONL の `funding_rate` / `funding_interval_minutes` / `oracle_price` から hourly bucket の funding event series を生成できる。

```bash
uv run sis build-trade-xyz-reference-data
```

出力:

```text
data/raw/funding/trade_xyz/YYYY-MM-DD.jsonl
data/normalized/funding_events.parquet
data/raw/funding_history/trade_xyz/YYYY-MM-DD.jsonl
data/normalized/funding_history_events.parquet
data/manifests/funding_manifest.json
data/manifests/funding_history_manifest.json
```

注意:

```text
これは quote snapshot 由来の funding event series。
専用 funding endpoint / settlement feed 由来ではない。
同一symbol・同一hourに複数quoteがある場合、現行実装はそのhourの最後のquoteを採用する。
```

現行Repoでは、Hyperliquid public `/info` の `fundingHistory` から
quote snapshotとは別の funding history を取得できる。

```bash
uv run sis collect-trade-xyz-funding-history \
  --symbols XYZ100 \
  --start-time-ms 1683849600000 \
  --end-time-ms 1683853200000
```

出力:

```text
data/raw/funding_history/trade_xyz/YYYY-MM-DD.jsonl
data/normalized/funding_history_events.parquet
data/manifests/funding_history_manifest.json
```

重要:

```text
fundingHistory は fundingRate / premium / time を返す。
oracle_price_at_funding は返さない。
そのため現行実装では usable_as_backtest_funding_event=false として保存する。
run_backtest() の funding payment に使うには、別途 oracle_price_at_funding を結合する必要がある。
```

現行Repoでは、`funding_history_events.parquet` と raw quote の `oracle_price` を
時刻近傍で結合し、backtest投入用の funding event artifact を作れる。

```bash
uv run sis build-trade-xyz-funding-events-from-history \
  --max-oracle-lag-minutes 90
```

出力:

```text
data/raw/funding/trade_xyz_from_history/YYYY-MM-DD.jsonl
data/normalized/funding_events_from_history.parquet
data/manifests/funding_history_join_manifest.json
```

重要:

```text
これは既存 data/normalized/funding_events.parquet を上書きしない。
oracle_price_at_funding は nearest raw quote oracle_price から結合する。
oracle_join_lag_seconds / oracle_join_ts_source / oracle_raw_payload_ref を必ず確認する。
max_oracle_lag_minutes 内に quote oracle がなければ、その funding event は skipped に入る。
run_backtest() に渡す場合は --funding-events data/normalized/funding_events_from_history.parquet を使う。
```

## 5. Fee Snapshots

保存先:

```text
data/raw/fees/trade_xyz/YYYY-MM-DD.jsonl
data/raw/fees/trade_xyz_account/YYYY-MM-DD_<user_hash>.json
data/normalized/fee_snapshots.parquet
data/manifests/fee_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
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

現行Repoでは、registry/config で解決された fee fields から fee snapshot series を生成できる。

```bash
uv run sis build-trade-xyz-reference-data
```

実アカウントの有効 maker/taker rate は、public user address がある場合だけ
read-only の `userFees` で取得できる。

```bash
uv run sis collect-trade-xyz-account-fee --user-address 0x...
```

これは Hyperliquid `/info` の `userFees` request だけを使う。
wallet、signing、exchange write、live order は使わない。
manifest と raw artifact metadata には user address のsha256だけを保存する。
長時間cycleに組み込む場合は、以下のどちらかを使う。

```bash
uv run sis collect-trade-xyz-data-cycle \
  --account-fee-user-address 0x...

SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x... \
  scripts/collect_trade_xyz_data_cycle.sh
```

出力:

```text
data/raw/fees/trade_xyz/YYYY-MM-DD.jsonl
data/raw/fees/trade_xyz_account/YYYY-MM-DD_<user_hash>.json
data/normalized/fee_snapshots.parquet
data/manifests/fee_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
data/manifests/trade_xyz_reference_datasets_manifest.json
```

注意:

```text
現時点のfee snapshotは registry/config 由来。
実アカウントの有効maker/taker rateは userFees snapshot があれば観測値を使う。
userFees が無い場合は account-specific fee を未収集として扱う。
builder fee approval は builder address が必要なので、builder codeを使う別scopeまで未収集。
growth modeはHIP-3 asset/deployer側の状態であり、userFeesだけでは確定しない。
戦略評価では source と source_hash を確認し、fallback率を別途reportする。
```

`fee_manifest.json` では以下を確認する。

```text
fee_snapshot_count
unresolved_symbols
fee_mode_counts
fee_source_counts
account_specific_fee_status
account_specific_missing_fields
account_specific_missing_field_counts
```

`trade_xyz_account_fee_manifest.json` では以下を確認する。

```text
status
source
user_address_sha256
available_fields
missing_fields
parsed.user_taker_fee_bps
parsed.user_maker_fee_bps
parsed.active_referral_discount
parsed.active_staking_discount
not_collected_fields
```

現行のpure backtest / research経路では、wallet / signing / exchange write を使わない。
public user address が未指定なら、実アカウント固有feeは
`not_collected_no_wallet_or_user_context` としてmanifestに残す。
public user address が指定され、`userFees` から `userCrossRate` / `userAddRate` が取れた場合だけ、
readiness の `account_specific_fee` は pass になる。

ただし、`builder_fee_bps` は builder address が必要で、`account_growth_mode` は
HIP-3 asset/deployer側の状態なので、`userFees` の取得成功と混同しない。
これらを0や標準feeとして扱わない。

現行Repoでは、`run_backtest()` の artifact に fee source が出る。

```text
fills.parquet:
  fee_source

metrics.json / candidate_result.json / backtest_report.md:
  fee_source_counts
  fee_row_resolved_rate
  fee_config_fallback_rate
  fee_unresolved_rate_runtime
```

読み方:

```text
fee_row_resolved_rate = 1.0:
  row上のfee bpsで評価できている。

fee_config_fallback_rate > 0:
  configs/fee_model.trade_xyz.yaml 由来のfallbackを使っている。
  smokeでは許容できるが、戦略評価では比率とsourceを明示して読む。

fee_unresolved_rate_runtime > 0:
  約定できない/評価不能なfeeが混じっている。
```

## 6. Real Market Reference Bars

保存先:

```text
data/raw/real_market/yfinance/trade_xyz_reference_bars.parquet
data/raw/real_market/yfinance,yahooquery,stooq/trade_xyz_reference_bars.parquet
data/normalized/real_market_reference_bars.parquet
data/manifests/trade_xyz_real_market_reference_manifest.json
data/reports/trade_xyz_real_market_reference.md
```

目的:

```text
Trade[XYZ] quoteが参照する外部市場の価格系列を固定する。
Trade[XYZ]板・mark/oracleだけで、参照市場との乖離やregimeを評価したと誤認しない。
```

現行Repoでは、Trade[XYZ] registryの `real_market_symbol` を使って
外部参照価格のreference barsを収集できる。default provider chainは
`yfinance -> yahooquery -> stooq` であり、前段providerで返らなかったsymbolだけを
次providerへ渡す。

```bash
uv run sis collect-trade-xyz-real-market-reference \
  --providers yfinance,yahooquery,stooq \
  --period-days 365 \
  --interval 1d
```

対象symbolを絞る場合:

```bash
uv run sis collect-trade-xyz-real-market-reference \
  --symbols SP500,XYZ100,NVDA \
  --providers yfinance,yahooquery,stooq \
  --period-days 365 \
  --interval 1d
```

必須列:

```text
ts
real_market_symbol
canonical_symbol
data_role
open
high
low
close
volume
provider
provider_symbol
interval
adjustment
```

実務判断:

```text
data_role=underlying_reference:
  Trade[XYZ] registryの real_market_symbol から引いた参照市場価格。

data_role=regime_reference:
  VIX / DXY proxy / FX など、戦略regimeやrisk guardの補助系列。

yfinance / yahooquery / stooq:
  research/backtest参照用。live execution dataではない。
  実発注や直近約定可否の判定に使わない。

stooq:
  no-secret fallback。現行実装では日足(1d)のみを対象にする。
  intradayやTrade[XYZ]の約定/mark/oracle/fundingの正本にはしない。
```

readiness:

```text
trade_xyz_real_market_reference_manifest.json は row_count だけでは完了扱いしない。
missing_mapped_symbols または missing_requested_symbols が残る場合は fail。
```

manifestで確認する項目:

```text
status
provider
provider_chain
provider_attempts
missing_after_each_provider
resolved_by_provider
unresolved_symbols
interval
row_count
requested_symbols
returned_symbols
missing_mapped_symbols
missing_requested_symbols
artifacts.normalized_reference_bars
```

`missing_mapped_symbols` が空でない場合は、Trade[XYZ]銘柄に対応する
外部参照価格が欠けている。quote coverageが通っていても、tracking qualityや
feature panel評価には進めない。

外部providerで取得できる価格は、Trade[XYZ]のfill価格、mark price、oracle price、
funding event、oracle_ts_ms の代替ではない。特に `source_ts_ms`、`recv_ts_ms`、
Yahoo/Stooq/Alpaca等のtimestampを `oracle_ts_ms` として穴埋めしてはいけない。
5月30日以前の実データ禁止も維持する。

## 7. Data Quality Manifests

保存先:

```text
data/manifests/quote_snapshot_manifest.json
data/manifests/instrument_registry_manifest.json
data/manifests/fee_manifest.json
data/manifests/oracle_timestamp_manifest.json
data/manifests/funding_manifest.json
data/manifests/funding_history_manifest.json
data/manifests/funding_history_join_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/session_state_manifest.json
data/manifests/trade_xyz_data_readiness_manifest.json
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

現行Repoでは、`collect-trade-xyz-quotes --write-summary --write-report` と
`build-trade-xyz-reference-data` の両方で oracle timestamp の欠損理由を確認できる。

```text
ops/trade_xyz_quote_collection_summary.json:
  per_symbol.*.oracle_ts_status_counts
  per_symbol.*.oracle_ts_missing_reasons
  oracle_ts_missing_reasons

data/manifests/oracle_timestamp_manifest.json:
  oracle_ts_present_count
  oracle_ts_missing_count
  oracle_ts_missing_rate
  oracle_ts_status_counts
  oracle_ts_source_counts
  oracle_ts_missing_reasons
  searched_payload_fields
```

重要:

```text
oracle_ts_ms はpayload内の oracle timestamp field が観測できた場合だけ入る。
source_ts_ms / recv_ts_ms / ts_client をoracle_ts_msに代入して穴埋めしない。
取得できない場合は欠損理由をmanifestで確認する。
readinessでは、`oracle_timestamp_manifest.json` の行数だけでは完了扱いしない。
`oracle_ts_missing_count > 0` または `oracle_ts_present_count = 0` の場合は
`oracle_timestamp_provenance` を known gap として扱う。
```

現行Repoでは、raw quote collectionが30日評価に足りるかを以下で確認できる。

```bash
uv run sis build-trade-xyz-quote-coverage --symbols SP500 --min-days 30 --max-gap-minutes 10
```

出力:

```text
data/manifests/trade_xyz_quote_coverage_manifest.json
```

確認項目:

```text
coverage_passed
per_symbol.*.coverage_status
per_symbol.*.span_days
per_symbol.*.distinct_utc_date_count
per_symbol.*.max_gap_seconds
per_symbol.*.observed_max_gap_seconds
per_symbol.*.gap_segment_count
per_symbol.*.selected_gap_segment_row_count
per_symbol.*.insufficient_reasons
per_symbol.*.missing_rates
traceable_only
raw_row_count
excluded_missing_raw_payload_ref_count
excluded_missing_raw_payload_ref_by_symbol
raw_payload_ref_missing_rate_all_rows
```

重要:

```text
coverage判定はデフォルトで traceable_only=true。
raw_payload_ref が無い旧raw rowsは改変せず、coverage計算から除外する。
除外した件数は excluded_missing_raw_payload_ref_* と
raw_payload_ref_missing_*_all_rows に残す。
古いraw rowsに後から raw_payload_ref を付け足してREADYに見せない。
旧rawも含めた診断が必要な場合だけ --include-untraceable を使う。
coverageは、`max_gap_minutes` を超えたgapで系列を区切り、
最新の連続segmentを評価対象にする。
短いprobeや再開前の孤立rowで将来の30日収集を永久failにしないため。
ただし、全観測row上の最大gapは `observed_max_gap_seconds` に残す。
評価対象segmentのgapは `max_gap_seconds`、行数は
`selected_gap_segment_row_count` を見る。
```

現行Repoでは、主要manifestをまとめて「純粋BTへ流せるか」を判定できる。

既存の `data/raw/quotes/trade_xyz/*.jsonl` と
`data/registry/trade_xyz_instrument_registry.json` から派生artifactをまとめて作る場合:

```bash
uv run sis build-trade-xyz-data-bundle
```

public `fundingHistory` も同じrunで取得する場合:

```bash
uv run sis build-trade-xyz-data-bundle \
  --funding-start-time-ms 1683849600000 \
  --funding-end-time-ms 1683853200000
```

raw quoteの最初/最後の時刻から funding取得windowを自動推定する場合:

```bash
uv run sis build-trade-xyz-data-bundle --auto-funding-window
```

日次収集では、quote収集とbundle/readiness再生成を別々に実行すると抜けやすい。
現行Repoでは、1 cycleとしてまとめて実行できる。

```bash
uv run sis collect-trade-xyz-data-cycle \
  --duration-minutes 1440 \
  --interval-seconds 60 \
  --symbols AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
```

このcommandは以下を順に行う。

```text
1. Trade[XYZ] registry をread-only refresh
2. collect-trade-xyz-quotes 相当のread-only quote収集
3. normalized quotes更新
4. reference datasets / session state生成
5. raw quote windowから fundingHistory windowを自動推定
6. fundingHistory取得
7. funding history と quote oracle の近傍結合
8. trade_xyz_data_readiness_manifest.json更新
```

事前確認だけなら:

```bash
uv run sis collect-trade-xyz-data-cycle --dry-run
```

cron / systemd / 手動tmuxなどで長時間回す入口:

```bash
SIS_TRADE_XYZ_CYCLE_DRY_RUN=1 scripts/collect_trade_xyz_data_cycle.sh
scripts/collect_trade_xyz_data_cycle.sh
setsid -f scripts/collect_trade_xyz_data_until_ready.sh >/tmp/trade_xyz_until_ready.nohup 2>&1 < /dev/null
```

環境変数:

```text
SIS_TRADE_XYZ_COLLECTION_CONFIG=configs/trade_xyz_data_collection.yaml
SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES=1440
SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS=60
SIS_TRADE_XYZ_CYCLE_SYMBOLS=
SIS_TRADE_XYZ_CYCLE_LOG_DIR=logs/trade_xyz_data_cycle
SIS_TRADE_XYZ_CYCLE_LOCK_DIR=.tmp/trade_xyz_data_cycle.lock
SIS_TRADE_XYZ_CYCLE_DRY_RUN=0
SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS=0
SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=1
SIS_TRADE_XYZ_CYCLE_REGISTRY_SEED_PATH=configs/instrument_registry.seed.json
SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES=1
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_INTERVALS=
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_PERIOD_DAYS=
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS=
SIS_TRADE_XYZ_UNTIL_READY_STALE_AFTER_MINUTES=180
SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_RUNNING_STALE=1
SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_LOCK_STALE=1
SIS_TRADE_XYZ_UNTIL_READY_ALLOW_KNOWN_GAPS=0
```

空の `SIS_TRADE_XYZ_CYCLE_SYMBOLS` / signal candle設定は
`configs/trade_xyz_data_collection.yaml` から読む。対象symbolやintervalを変更する
通常運用ではYAMLを編集し、credentialやaccount fee用public user addressは環境変数で渡す。
2026-05-30以前の実データは使用禁止で、該当artifactは
`data/archive/pre_2026_05_31_unusable_real_data/` に移動済み。

logは `logs/trade_xyz_data_cycle/trade_xyz_data_cycle_YYYYMMDD_HHMMSS.log`
に保存される。
wrapperは `SIS_TRADE_XYZ_CYCLE_LOCK_DIR` で重複起動を止める。pid付きstale lockは
起動時に回復し、pid無しの空lock directoryも回復する。非空lockや実processが
残る場合は、既存processと直近logを確認する。
dry-run以外では終了後に `trade-xyz-collection-status` も更新する。
registry refresh は通常有効にする。固定済みregistryだけで再現したい調査時は
`--use-existing-registry` または `SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=0` を使う。
until-ready supervisor は、collector稼働中に最新raw fileが stale になった場合と、
supervisor lock / 稼働中collectorのcycle lockが stale の場合に異常終了する。
異常終了させずに記録だけしたい場合は
`SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_RUNNING_STALE=0` または
`SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_LOCK_STALE=0` を使う。
wrapper / until-ready はデフォルトで strict readiness を使い、account-specific fee
などの known gap が残る状態を完了扱いしない。研究用途で known gap を許す場合だけ
`SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS=1` /
`SIS_TRADE_XYZ_UNTIL_READY_ALLOW_KNOWN_GAPS=1` を使う。
until-ready supervisor は `SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=1` /
`SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=1` の場合でも、collector稼働中は外部前提の失敗を
理由に organic quote collection を止めない。collectorが止まっていて次cycleを起動する
前だけ `--fail-on-archive-preflight` / `--fail-on-account-fee-missing` 付きstatusを
実行し、AWS資格情報やaccount fee user address未設定を起動前gateとして扱う。

signal用のhistorical OHLCVは `collect-trade-xyz-signal-candles` で収集する。
これは `data/normalized/trade_xyz_signal_candles.parquet` に保存し、fill snapshot用の
`data/normalized/quotes.parquet` とは混ぜない。通常cycleでは `30m,4h,1d,3d` を
365日分確認する。既存artifactが完全で新しければ再取得せず、quote coverage収集を
優先する。
連続 `/info` request で429が出る場合は、欠けたsymbolだけを指定し、
`--request-delay-seconds` を長めにして再実行する。

readinessでは、signal candles も row_count だけでは完了扱いしない。
registryがある場合は active Trade[XYZ] symbols が `symbols` に揃っていること、
`requested_intervals` が `intervals` に揃っていること、かつ `request_error_count=0`
を確認する。

30日coverageまで継続監視する場合は `scripts/collect_trade_xyz_data_until_ready.sh`
を使う。既存collectorが動いている間は重複cycleを始めず、collector停止かつ
`backtest_data_ready=false` の場合だけ次のcycleを始める。terminal/session終了後も
残す場合は、上記の `setsid -f ...` 形式でdetachする。

historical L2を使って不足期間の調査をする場合は、Hyperliquid historical archiveを
別経路として扱う。

```bash
uv run sis collect-trade-xyz-historical-l2-archive \
  --coin xyz:XYZ100 \
  --date 2026-05-01 \
  --hour 9

uv run sis collect-trade-xyz-historical-asset-ctxs-archive \
  --date 2026-05-01

uv run sis plan-trade-xyz-historical-archive-bulk \
  --coins xyz:AAPL,xyz:AMD,xyz:AMZN,xyz:EWJ,xyz:GOOGL,xyz:META,xyz:MSFT,xyz:NVDA,xyz:SP500,xyz:TSLA,xyz:XYZ100 \
  --start-date 2026-05-01 \
  --end-date 2026-05-30

uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10

uv run sis check-trade-xyz-historical-archive-preflight

uv run sis execute-trade-xyz-historical-archive-bulk \
  --execute \
  --acknowledge-requester-pays \
  --max-objects 10

uv run sis normalize-trade-xyz-historical-archive-bulk

uv run sis normalize-trade-xyz-historical-archive-quotes \
  --l2-jsonl-path data/raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl \
  --asset-ctxs-path data/raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv \
  --coin xyz:XYZ100
```

これはデフォルトでdry-runだけを行う。実downloadには次が必要である。

```bash
uv run sis collect-trade-xyz-historical-l2-archive \
  --coin xyz:XYZ100 \
  --date 2026-05-01 \
  --hour 9 \
  --execute \
  --acknowledge-requester-pays

uv run sis collect-trade-xyz-historical-asset-ctxs-archive \
  --date 2026-05-01 \
  --execute \
  --acknowledge-requester-pays
```

注意:

```text
Hyperliquid historical archive は requester-pays S3 なので転送費が発生し得る。
aws download command と lz4 が必要。system `aws` が無い場合、現行Repoは
`uv run --with awscli aws` fallbackをdownload commandに使える。
固定profileを使う運用では `SIS_AWS_COMMAND="aws --profile <profile>"` を設定する。
archiveは概ね月次更新で、欠損や遅延があり得る。
`trade-xyz-collection-status` の `preflight_command` で `sts get-caller-identity`
を通してから、requester-pays downloadへ進む。
`check-trade-xyz-historical-archive-preflight` はその確認結果を
`data/manifests/trade_xyz_historical_archive_preflight_manifest.json` に保存する。
`trade-xyz-collection-status` はbulk planの推定object数、bulk executionのdry-run/download/error数、
bulk normalizationの処理済みfile数も出すため、直近のarchive作業が
plan止まりなのか、dry-run済みなのか、download/normalize済みなのかをstatusだけで確認する。
`execute-trade-xyz-historical-archive-bulk --max-objects 10` はdry-runであり、
実downloadではない。対象と費用を確認した後、実download時だけ
`--execute --acknowledge-requester-pays` を付ける。
実downloadは `check-trade-xyz-historical-archive-preflight` が `pass` の場合だけ進める。
preflight未実行またはfail済みなら、単体download / bulk downloadとも
`blocked_preflight_failed` で停止する。
download commandは raw l2Book / asset_ctxs archive を保存するだけで、quotes.parquetへ自動混入しない。
30日live quote coverage の代替として使うには、別途 archive l2Book + asset_ctxs
-> quote snapshot 正規化と provenance 検証が必要。
L2だけでは mark / oracle / funding / fee context を満たしたとは扱わない。
`normalize-trade-xyz-historical-archive-bulk` はbulk planに載っているdecompressed
l2Bookと同日asset_ctxsをまとめて `data/raw/quotes/trade_xyz/*.jsonl` に変換する。
coverage判定はこのflat raw quote JSONLを読む。
`normalize-trade-xyz-historical-archive-quotes` は decompressed L2 JSONL と
asset_ctxs CSV/JSON から raw quote JSONL を作るが、`--normalize` を付けない限り
`data/normalized/quotes.parquet` は更新しない。
asset_ctxsが無いrowは `BLOCK_HISTORICAL_ASSET_CTX_MISSING` 付きで
`is_tradable=false` として残す。
30日・11銘柄・24時間をbulk planすると、L2 objectは7920、asset_ctxs objectは30、
合計7950 objectになる。requester-paysなので、実download前に費用・欠損・coin名を
必ず確認する。
```

長期収集中の現在地だけ確認する場合:

```bash
uv run sis trade-xyz-collection-status
uv run sis trade-xyz-collection-status --fail-on-archive-preflight
uv run sis trade-xyz-collection-status --fail-on-account-fee-missing
uv run sis trade-xyz-collection-status --stale-after-minutes 180 --fail-on-stale
uv run sis trade-xyz-collection-status --fail-on-lock-stale
uv run sis trade-xyz-collection-status --fail-on-progress-warning
scripts/check_trade_xyz_data_prereqs.sh
```

`trade-xyz-collection-status` は、デフォルトで現在の raw quote JSONL から
quote coverage manifest を再計算してから status を出す。収集中の進捗確認では、
古い `trade_xyz_quote_coverage_manifest.json` の行数ではなく、直近rawを反映した
`coverage.row_count` / `raw_quote_inventory.traceable_row_count` を見る。
過去manifestをそのまま読みたい調査時だけ `--no-refresh-coverage` を使う。
また、デフォルトで data readiness manifest も再評価する。bundle全体を再生成する
わけではないため funding / reference / session artifact の更新は
`build-trade-xyz-data-bundle --auto-funding-window` または
`collect-trade-xyz-data-cycle` に任せる。

出力:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
```

確認項目:

```text
decision
backtest_data_ready
readiness_decision
fail_count
known_gap_count
failing_requirements
known_gap_requirements
raw_quote_inventory.traceable_row_count
raw_quote_inventory.untraceable_row_count
raw_quote_inventory.latest_file_age_seconds
latest_file_stale
locks.cycle.stale
locks.supervisor.stale
locks.cycle.pid_running
locks.supervisor.pid_running
coverage.estimated_max_collection_days_required
coverage.min_span_days
coverage.max_remaining_days_exact
coverage.completion_ratio_by_span
coverage.slowest_symbols
coverage.symbols.*.estimated_collection_days_required
coverage_refresh.status
readiness_refresh.status
progress_since_previous_status.status
progress_since_previous_status.traceable_row_count_delta
readiness_requirement_details.funding_events.status
readiness_requirement_details.funding_events.skipped
readiness_requirement_details.oracle_timestamp_provenance.status
readiness_requirement_details.oracle_timestamp_provenance.oracle_ts_missing_rate
readiness_requirement_details.signal_candles.status
readiness_requirement_details.signal_candles.request_error_count
historical_archive_artifacts.bulk_plan.estimated_total_object_count
historical_archive_artifacts.bulk_execution.status
historical_archive_artifacts.bulk_execution.dry_run
historical_archive_artifacts.bulk_execution.selected_object_count
historical_archive_artifacts.bulk_execution.downloaded_object_count
historical_archive_artifacts.bulk_execution.command_error_count
historical_archive_artifacts.bulk_normalization.status
historical_archive_artifacts.bulk_normalization.normalized_file_count
account_fee_prerequisites.configured
account_fee_artifact.exists
account_fee_artifact.status
account_fee_artifact.matches_configured_user
account_fee_artifact.user_taker_fee_bps
account_fee_artifact.user_maker_fee_bps
next_actions[0].command
```

監視では `--fail-on-stale`、`--fail-on-lock-stale`、`--fail-on-progress-warning`、
archive backfillを使う場合は `--fail-on-archive-preflight`、account-specific feeを
必須にする場合は `--fail-on-account-fee-missing` を使う。
`--fail-on-account-fee-missing` は readiness の known gap だけでなく、
account fee manifest の存在、`status=pass`、maker/taker bps、env設定時の
user hash一致も直接確認する。
両方をまとめて確認する場合は `scripts/check_trade_xyz_data_prereqs.sh` を使う。
このwrapperは未設定時に `SIS_AWS_COMMAND="aws --profile <profile>"`、
`SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...`、前提設定後の
`scripts/collect_trade_xyz_data_until_ready.sh`、最終確認の
`uv run sis trade-xyz-collection-status --strict --fail-on-not-ready` を表示する。
`SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` が設定済みなら、wrapper内で
`collect-trade-xyz-account-fee` をread-only実行し、
`trade_xyz_account_fee_manifest.json` を更新してからstatusを確認する。
外部前提が未設定でも quote coverage だけ伸ばす場合は、wrapperが出す
`continue_quote_collection_without_archive_or_account_fee_command` を使う。
これは最終readyではなく、AWS/account feeが揃うまでの organic quote collection 継続用。
account fee はenv設定だけでは完了扱いにしない。`account_fee_artifact.exists=true`、
`account_fee_artifact.status=pass`、env設定時は
`account_fee_artifact.matches_configured_user=true`、かつ
`account_fee_artifact.user_taker_fee_bps` / `account_fee_artifact.user_maker_fee_bps`
が入っていることを確認する。
readiness でも、env設定時は `trade_xyz_account_fee_manifest.json` の
`user_address_sha256` と設定値のsha256一致を確認する。別アカウントの古いmanifestは
`account_specific_fee` の known gap として扱う。
archiveを今回使わないなら `SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0`、
account feeをknown gapとして許すなら `SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0` を設定する。
30日coverage到達後のgate確認では `--fail-on-not-ready` を使う。

出力:

```text
data/manifests/trade_xyz_data_collection_bundle_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/trade_xyz_reference_datasets_manifest.json
data/manifests/session_state_manifest.json
data/manifests/trade_xyz_data_readiness_manifest.json
```

`data/normalized/funding_history_events.parquet` が既にある場合は、
`funding_events_from_history.parquet` も同時に作る。ない場合は
reference data生成で作る quote由来の `funding_events.parquet` を使う。
`--funding-start-time-ms` を渡した場合は、
`funding_history_events.parquet` の取得から oracle結合まで同じbundle内で行う。
`--auto-funding-window` は対象raw quoteの最小時刻から最大時刻+1時間を使う。
`NOT_READY` の場合は `trade_xyz_data_readiness_manifest.json` の
`next_actions` に次の収集コマンドが出る。quote coverage不足の場合は、
`recommended_collection_duration_minutes`、`estimated_max_collection_days_required`、
`estimated_collection_days_required_by_symbol` も確認する。

既にmanifest群がある状態で判定だけやり直す場合:

```bash
uv run sis build-trade-xyz-data-readiness
```

出力:

```text
data/manifests/trade_xyz_data_readiness_manifest.json
```

判定:

```text
READY:
  必須artifactが揃い、known gapもない。

READY_WITH_KNOWN_GAPS:
  純粋BTへ投入できるが、account-specific fee、Trade[XYZ]内部session、
  maintenance / haltなどが未観測として明示されている。

NOT_READY:
  quote coverage、reference datasets、funding events、fee snapshots、
  session state、oracle timestamp provenance のどれかが不足している。
```

重要:

```text
READY_WITH_KNOWN_GAPS は「完全な市場真実」ではない。
wallet / signing / live order / exchange write なしで取れないものは known_gap として残す。
known_gap を許さない判定は --strict を使う。
quote coverage不足で NOT_READY の場合は、古い untraceable raw rows が
excluded_missing_raw_payload_ref_* に出ることがある。
これは旧rawを直す合図ではなく、現行collectorで traceable なfresh rowsを集め直す合図。
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
  traceable_only coverageで coverage_passed=true
  included rowsの raw_payload_ref missing rate = 0
  excluded_missing_raw_payload_ref_count は旧raw除外数として説明可能
  oracle_ts missing rateが説明可能
  coverage gapがreportに出る

strategy evaluation:
  対象timeframeに対して十分なbar数
  funding eventsが別系列で存在
  instrument registry snapshotがperiod全体を覆う
  fee fallback率が明示されている
```

## 8. Feature Panel

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

## 9. Strategy Signal Artifact

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

## 10. Evaluation Plan / Leakage Check

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

## 11. Baseline / Benchmark Data

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
  条件付き可。
  funding_events.parquet または funding_events_from_history.parquet があり、
  oracle_price_at_funding と join lag provenance を確認済みの場合に限る。

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
holiday closureを未取得のまま誤判定しない
session_calendar_manifest.jsonに未取得field countsが出る
```

現行Repoでは、registry由来の session refs と、未取得の
`external_session_open` / `internal_session_open` / `maintenance_window` /
`holiday_closure` を `session_calendar_snapshots.parquet` と
`session_calendar_manifest.json` に出せる。
これは「判定済み」ではなく「未取得を明示できる」状態である。

現行Repoでは、quote時刻に対するTrade[XYZ] session状態を
`session_state_observations.parquet` と `session_state_manifest.json` に出せる。
supported symbolsではTrade[XYZ] docs由来のspec-derived値として
`external_session_open` / `internal_session_open` / `maintenance_window` を埋める。
holiday closure は `exchange_calendars` proxyなので、公式Trade[XYZ] halt feedではない。

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

現行Repoでは、`run_backtest()` に `funding_events` DataFrame を渡せる。
`scripts/run_trade_xyz_backtest_smoke.py` は `data/normalized/funding_events.parquet` が存在する場合だけ読み込み、存在しない場合は従来どおり smoke を継続する。

重要:

```text
funding_events が渡された場合:
  - funding_rate が quote row 側にあっても課金には使わない
  - funding_events の funding_event_ts / funding_rate / oracle_price_at_funding を使う
  - breakout signal 生成用の価格行には funding event row を混ぜない
```

現行Repoでは、public `fundingHistory` 由来の
`funding_history_events.parquet` も作れる。
これは `oracle_price_at_funding` を含まないため、そのまま
`run_backtest()` の funding payment eventには使わない。
現行Repoでは、次の変換で nearest raw quote oracle price を結合し、
`funding_events_from_history.parquet` を作れる。

```bash
uv run sis build-trade-xyz-funding-events-from-history
```

このartifactは `run_backtest()` に渡せる。ただし、必ず
`funding_history_join_manifest.json` の `skipped`、
`oracle_join_lag_seconds`、`oracle_join_ts_source` を確認する。

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

加えて `fee_manifest.json` に account-specific feeが未収集である理由を残す。
public user address がある場合は `collect-trade-xyz-account-fee` で
`trade_xyz_account_fee_manifest.json` を作り、`userFees` 由来の
`user_taker_fee_bps` / `user_maker_fee_bps` を実アカウントの有効rateとして扱う。
それがない状態で `fee_snapshot` を実fee正本として扱わない。

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

現行Repoでは、まず `real_market_bars` と基本regime referenceを以下で収集する。

```bash
uv run sis collect-trade-xyz-real-market-reference --period-days 365 --interval 1d
```

出力:

```text
data/normalized/real_market_reference_bars.parquet
data/manifests/trade_xyz_real_market_reference_manifest.json
```

これはfeature panelの前段データであり、Trade[XYZ]の約定価格やfill可否の正本ではない。

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
1. SP500 30日以上の quote collection を安定運用する
2. 必要なら対象symbol全体で30日以上の quote collection を安定運用する
3. `collect-trade-xyz-real-market-reference` で対応real market referenceを収集する
4. public user addressがある場合は `collect-trade-xyz-account-fee` でaccount feeを収集する
5. builder codeを使う場合だけ、builder address前提のbuilder fee approval取得を別scopeで設計する
6. feature_panel_snapshot.v1 または既存 feature_snapshot_manifest を実データ列まで強化する
```

ただし、最初の運用改善はschema追加よりも、SP500の長期quote収集である。
`trade_xyz_quote_coverage_manifest.json` が `coverage_passed=true` になるまで、
収集runの間隔、欠損、raw_payload_ref、fee/funding/oracle_ts欠損率を確認する。
旧rawの `raw_payload_ref` 欠損は、`traceable_only=true` のcoverageでは
除外件数として記録し、READY判定の母集団に混ぜない。
日次運用は `collect-trade-xyz-data-cycle` を基本にし、収集だけを個別に調整したい
場合に限って `collect-trade-xyz-quotes` と `build-trade-xyz-data-bundle` を分ける。
