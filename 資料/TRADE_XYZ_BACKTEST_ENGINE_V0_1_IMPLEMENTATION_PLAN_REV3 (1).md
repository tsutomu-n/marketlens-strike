# Trade[XYZ] Pure Backtest Engine v0.1 Implementation Plan REV3

作成日: 2026-05-31
対象 repo: `/home/tn/projects/marketlens-strike`
対象ブランチ: `feature/backtest-engine-roadmap`
目的: Trade[XYZ] 専用の純粋バックテスト基盤を、コーダーが実装完了できる粒度で定義する。

---

## 0. REV3 の結論

REV2 の方針は概ね正しい。ただし、実務的なバックテストとしては以下が不足していたため、REV3 で追加・修正する。

### v0.1 に必須で追加するもの

1. `BacktestConfig` / `RunConfig`
2. 期間指定。ただし `warmup_start_ts` と `evaluation_start_ts` を分ける
3. `DataManifest` / `ConfigHash` / `InputSchemaHash`
4. data quality check
5. benchmark comparison
6. scenario sensitivity
7. simple train/test split
8. parameter sweep の軽量版
9. blocked event ledger
10. session / market_status breakdown
11. human-readable report with charts
12. end-of-run open position policy
13. fee / spread / slippage / funding の二重計上防止ルール

### REV2 からの重要修正

- market-like exit では maker fee ではなく taker fee を使う。
- `funding_rate` が row に存在しても、quote row ごとに課金してはいけない。funding は hourly event として dedupe / interval assertion できる場合だけ適用する。
- period filter には indicator warmup が必要。`start_ts` だけで data を切ると lookback 指標が壊れる。
- bar fixture の OHLC は signal 用。fill は executable price column からのみ決める。
- `is_tradable=false` / `block_reasons` 非空は entry 禁止。exit は `close_only` と stale exit の扱いを明示する。
- report graph は追加依存を避けるため、v0.1 では inline SVG / SVG file を第一候補にする。PNG は optional。

---

## 1. Scope

### 対象

```text
Trade[XYZ] only
pure backtest only
SP500 first
single-symbol
long-only
market-like taker fill
fixed-notional sizing
fixture-first tests
no public CLI until engine semantics are pinned
```

### 非対象

```text
live order
wallet
signing
exchange write
nonce
cloid lifecycle
short
multi-symbol portfolio
maker fill
limit / stop / trailing order
partial fill
leverage execution
liquidation simulation
L2 replay
MT5 / IC Markets / CFD
LLM strategy judge
```

### 既存 surface との境界

触らない:

```text
src/sis/backtest/bridge.py
src/sis/backtest/costs.py
src/sis/backtest/signals.py
src/sis/paper/*
src/sis/execution/*
src/sis/cli.py  # v0.1では public CLI を追加しない
```

新規追加の中心:

```text
src/sis/backtest/engine/
src/sis/backtest/trade_xyz/
tests/backtest/
```

---

## 2. Target Capabilities After v0.1

v0.1 実装後にできること:

```text
指定期間で
指定 symbol / timeframe に対し
固定 notional の long-only 戦略を
fee / spread / slippage / funding policy / entry gate 込みで検証し
orders / fills / trades / equity / metrics / manifest / report を artifact として保存し
benchmark / scenario / split / parameter 結果を比較し
人間が読める markdown + html report + SVG chart を出す
```

ただし、これは「儲かるBot」ではない。目的は偽の勝ちを消すこと。

---

## 3. Core Design Principles

### 3.1 No live surface

Backtest engine は wallet / signing / exchange write を一切持たない。

### 3.2 Fixture first

unit test は runtime artifact に依存しない。

禁止:

```text
data/normalized/quotes.parquet が無いと unit test が落ちる
```

許可:

```text
tmp_path に deterministic DataFrame を作り Parquet 化する
integration-ish test だけ、存在時に runtime artifact を読む
```

### 3.3 No implicit symbol mapping

禁止:

```text
SPY -> SP500
QQQ -> XYZ100
```

使う場合は mapping table / provenance / session difference を別タスク化する。

### 3.4 No fee hardcode

禁止:

```text
0.04%
4.0 bps
```

fee は row resolved fee または `configs/fee_model.trade_xyz.yaml` から解決する。

### 3.5 No guessed funding

funding は row に値があるだけで適用しない。funding interval / unit / dedupe policy が明示されたときだけ計算する。

### 3.6 No same-row fill after close signal

bar close で signal を作ったなら、entry / exit fill は次の executable row で行う。

---

## 4. BacktestConfig

新規ファイル:

```text
src/sis/backtest/engine/config.py
```

### 4.1 Pydantic model

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class PeriodConfig(BaseModel):
    warmup_start_ts: datetime | None = None
    evaluation_start_ts: datetime
    evaluation_end_ts: datetime


class PositionSizingConfig(BaseModel):
    mode: Literal["fixed_notional"] = "fixed_notional"
    notional_usd: float = Field(gt=0)
    max_position_notional_usd: float | None = Field(default=None, gt=0)


class ExecutionConfig(BaseModel):
    side_mode: Literal["long_only"] = "long_only"
    fill_model: Literal["market_like_taker_v0"] = "market_like_taker_v0"
    extra_slippage_bps: float = Field(default=0.0, ge=0)
    force_close_on_end: bool = False


class CostConfig(BaseModel):
    fee_model_ref: str = "configs/fee_model.trade_xyz.yaml"
    fee_scenario: Literal["row_resolved", "standard", "growth"] = "row_resolved"
    fee_multiplier: float = Field(default=1.0, gt=0)
    funding_policy: Literal[
        "disabled_v0",
        "nullable_zero_v0",
        "fixture_hourly_v0",
    ] = "nullable_zero_v0"


class GateConfig(BaseModel):
    allow_entry_when_block_reasons_non_empty: bool = False
    allow_entry_when_is_tradable_false: bool = False
    max_spread_bps: float | None = Field(default=None, gt=0)
    min_depth_10bps_usd: float | None = Field(default=None, gt=0)
    max_bound_distance: float | None = Field(default=None, ge=0)
    max_oi_cap_usage: float | None = Field(default=None, ge=0)


class LeverageConfig(BaseModel):
    mode: Literal["disabled"] = "disabled"
    requested_leverage: None = None
    max_leverage: None = None
    liquidation_model: Literal["not_implemented"] = "not_implemented"


class ReportConfig(BaseModel):
    write_markdown: bool = True
    write_html: bool = True
    write_svg_charts: bool = True
    write_charts_data_json: bool = True


class BacktestConfig(BaseModel):
    schema_version: Literal["trade_xyz_backtest_config.v1"] = "trade_xyz_backtest_config.v1"
    run_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    period: PeriodConfig
    initial_cash_usd: float = Field(gt=0)
    position_sizing: PositionSizingConfig
    execution: ExecutionConfig = ExecutionConfig()
    cost: CostConfig = CostConfig()
    gates: GateConfig = GateConfig()
    leverage: LeverageConfig = LeverageConfig()
    report: ReportConfig = ReportConfig()
    deterministic_seed: int = 0

    @model_validator(mode="after")
    def validate_config(self) -> "BacktestConfig":
        if self.period.evaluation_start_ts >= self.period.evaluation_end_ts:
            raise ValueError("evaluation_start_ts must be < evaluation_end_ts")
        if (
            self.period.warmup_start_ts is not None
            and self.period.warmup_start_ts > self.period.evaluation_start_ts
        ):
            raise ValueError("warmup_start_ts must be <= evaluation_start_ts")
        if self.position_sizing.max_position_notional_usd is not None:
            if self.position_sizing.notional_usd > self.position_sizing.max_position_notional_usd:
                raise ValueError("notional_usd must be <= max_position_notional_usd")
        self.symbol = self.symbol.strip().upper()
        return self
```

### 4.2 Key rule

`warmup_start_ts` は indicator 計算用。metrics / trades / benchmark は `evaluation_start_ts` 以降だけで評価する。

---

## 5. Market Data Schema

新規ファイル:

```text
src/sis/backtest/trade_xyz/schema.py
```

### 5.1 Required columns

```text
event_ts
symbol
mid_price or close
best_bid / best_ask or spread_bps
taker_fee_bps or fee_mode
maker_fee_bps optional
is_tradable
block_reasons
```

### 5.2 Reserved / nullable columns

```text
source_ts_ms
recv_ts_ms
mark_price
oracle_price
external_price  # current source: index_price
funding_rate
funding_interval_minutes
open_interest_usd
oi_cap_usd
oi_cap_usage
discovery_bound_pct
bound_distance
session_type
market_status
source_confidence
venue_quality_score
depth_10bps_usd
min_side_depth_10bps_usd
```

### 5.3 Naming map from current normalized quotes

```text
BT schema           Current normalized quote
------------------  -------------------------
event_ts            ts_client parsed as timezone-aware datetime
symbol              canonical_symbol
external_price       index_price first
best_bid            best_bid or bid_price
best_ask            best_ask or ask_price
```

### 5.4 Schema behavior

- `block_reasons` contract は `list[str]`。
- Parquet artifact が `List(Null)` になるケースは empty list only snapshot として扱う。
- symbol mismatch は hard error。
- negative price / zero price は hard error。

---

## 6. Data Quality

新規ファイル:

```text
src/sis/backtest/engine/data_quality.py
```

### 6.1 Checks

```text
required columns exist
timestamps parseable
timestamps sorted
duplicate event_ts per symbol count
row count after period filter > 0
price > 0
best_bid <= best_ask if both present
spread_bps >= 0 if present
fee_bps >= 0 if present
is_tradable not null
block_reasons not null
symbol exactly matches config.symbol
critical null counts
cadence gap summary
```

### 6.2 DataQualityReport fields

```text
status: pass | warn | fail
input_row_count
filtered_row_count
first_event_ts
last_event_ts
duplicate_ts_count
out_of_order_count
critical_null_counts
invalid_price_count
bid_ask_cross_count
cadence_gap_count
warnings
errors
```

### 6.3 Stop conditions

- required columns missing -> fail
- no rows after evaluation filter -> fail
- invalid price in executable rows -> fail
- fee unresolved on entry candidate -> blocked event, not silent zero

---

## 7. Data Manifest / Hashes

新規ファイル:

```text
src/sis/backtest/engine/manifest.py
src/sis/backtest/engine/hashing.py
```

### 7.1 Artifacts

```text
data_manifest.json
config_hash.txt
input_schema_hash.txt
```

### 7.2 DataManifest fields

```text
schema_version: trade_xyz_backtest_data_manifest.v1
run_id
input_data_ref
input_data_sha256
input_schema_hash
config_hash
input_row_count
filtered_row_count
first_event_ts
last_event_ts
symbols
timeframe
event_time_source
warmup_start_ts
evaluation_start_ts
evaluation_end_ts
data_quality_summary
```

### 7.3 Hash rule

- config hash uses deterministic JSON dump with sorted keys.
- input schema hash includes column names and dtypes.
- for runtime artifact path missing in unit test, use fixture DataFrame hash instead of filesystem dependency.

---

## 8. Fee / Cost Model

新規ファイル:

```text
src/sis/backtest/trade_xyz/cost_model.py
```

### 8.1 Fee resolution order

1. row `taker_fee_bps` / `maker_fee_bps`
2. `configs/fee_model.trade_xyz.yaml` fallback by `fee_mode`
3. unresolved -> entry blocked

### 8.2 Market-like fee rule

v0.1 はすべて taker 相当。

```text
long entry fee = fill_notional * taker_fee_bps / 10_000
long exit fee  = fill_notional * taker_fee_bps / 10_000
```

`maker_fee_bps` は artifact に残すが、v0.1 fill では使わない。

### 8.3 Spread / slippage rule

- `exec_buy_price` / `exec_sell_price` がある場合: spread is implicit.
- `best_ask` / `best_bid` fallback: spread is implicit.
- `mid ± spread/2` fallback: spread is implicit.
- `extra_slippage_bps` は明示設定時だけ fill price に追加。
- spread cost と slippage cost を別に控除して二重計上しない。

### 8.4 Funding rule

funding は quote row ごとに課金しない。

Allowed policies:

```text
disabled_v0:
  funding_cost = 0
  metricsに policy を残す

nullable_zero_v0:
  funding_rate null -> 0
  funding_rate not null でも interval assertion が無ければ 0 とし warning を残す

fixture_hourly_v0:
  input rows are asserted as hourly funding events
  funding_payment = position_qty * oracle_price * funding_rate
  long with positive funding pays; long with negative funding receives
```

Runtime normalized quotes に funding_rate があるだけでは `fixture_hourly_v0` を使わない。

---

## 9. Gates

新規ファイル:

```text
src/sis/backtest/trade_xyz/gates.py
```

### 9.1 Entry gate

Entry is blocked when:

```text
is_tradable is false
block_reasons non-empty
fee unresolved
market_status not open
spread_bps > max_spread_bps when configured
min_side_depth_10bps_usd < threshold when configured
bound_distance > max_bound_distance when configured
oi_cap_usage > max_oi_cap_usage when configured
```

### 9.2 Exit gate

v0.1 exit is allowed when:

```text
position is open
exit signal exists
exit executable price is resolvable
fee is resolvable
market_status in {open, close_only, unknown_if_fixture}
```

If exit cannot be resolved:

```text
record blocked_event with action=exit
keep position open
mark end_open_position_count > 0
```

Optional `force_close_on_end` is disabled by default. If enabled, use last executable sell price and record `exit_reason=forced_end_close`.

### 9.3 BlockedEvent artifact

Add:

```text
blocked_events.parquet
```

Columns:

```text
event_ts
symbol
action
reason
reason_detail
strategy_id
signal_id
row_index
```

---

## 10. Order / Fill / Portfolio Contracts

New files:

```text
src/sis/backtest/engine/order.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
```

### 10.1 Order

```text
order_id
client_order_id optional
created_ts
symbol
side: buy | sell
position_effect: open | close
order_type: market_like
requested_notional_usd
requested_qty optional
limit_price optional null
reduce_only
strategy_id
signal_id optional
```

### 10.2 Fill

```text
fill_id
order_id
event_ts
symbol
side
position_effect
qty
fill_price
fill_notional_usd
fee_bps
fee_amount
extra_slippage_bps
extra_slippage_amount
funding_amount_delta
liquidity_flag: taker
fill_price_source
```

### 10.3 Portfolio

```text
cash_usd
position_qty
avg_entry_price
realized_pnl
unrealized_pnl
fees_paid
slippage_paid
funding_pnl
equity
```

### 10.4 Invariants

- flat start explicit
- first long entry sets avg price = fill price
- cash decreases by notional + fee
- exit realizes gross pnl minus explicit costs
- flat exit returns qty to zero
- no fill when blocked
- no negative qty in long-only mode

Use tolerance for float accounting: `abs(actual - expected) <= 1e-9` or a documented epsilon.

---

## 11. Fill Model

New file:

```text
src/sis/backtest/engine/fill.py
```

### 11.1 Fill price priority

Long entry:

```text
exec_buy_price -> best_ask -> ask_price -> mid_price + spread_bps/2
```

Long exit:

```text
exec_sell_price -> best_bid -> bid_price -> mid_price - spread_bps/2
```

### 11.2 fill_price_source required

Values:

```text
exec_buy_price
exec_sell_price
best_ask
best_bid
ask_price
bid_price
mid_plus_half_spread
mid_minus_half_spread
```

### 11.3 No OHLC fill

`open/high/low/close` must not be used as executable price unless a separate `bar_executable_price_policy` is explicitly added. For v0.1, no implicit OHLC fill.

---

## 12. Runner Semantics

New file:

```text
src/sis/backtest/engine/runner.py
```

### 12.1 Event order

```text
1. load config
2. load market data
3. apply warmup/evaluation filter
4. validate schema and data quality
5. compute strategy signals using warmup-inclusive data
6. for each row in chronological order:
   a. update mark-to-market equity
   b. if existing order scheduled for this row, attempt fill
   c. process exit signal first if position open
   d. process entry signal if flat
   e. apply funding only if policy permits and row is a funding event
   f. record equity snapshot
7. handle end-of-run open position policy
8. write artifacts
```

### 12.2 Signal/fill separation

If signal is generated from row `i`, fill can only use row `i+1` or later.

---

## 13. Metrics

New file:

```text
src/sis/backtest/engine/metrics.py
```

### 13.1 Core metrics

```text
net_return_after_cost
total_return
max_drawdown
trade_count
win_rate
profit_factor
sharpe_like_metric
median_trade_pnl
worst_trade_pnl
exposure_time
turnover
cost_drag_bps
end_open_position_count
end_unrealized_pnl
```

### 13.2 Trade[XYZ] metrics

```text
fee_impact
funding_impact
slippage_impact
taker_fill_ratio
maker_fill_ratio  # always 0 in v0.1
blocked_reason_counts
session_breakdown
market_status_breakdown
source_confidence_gate_pass_rate
venue_quality_gate_pass_rate
```

### 13.3 Do not overclaim Sharpe

If sampling cadence and annualization are not fixed, output `sharpe_like_metric`, not annualized Sharpe.

---

## 14. Benchmark

New file:

```text
src/sis/backtest/engine/benchmark.py
```

### 14.1 Required benchmarks

```text
cash_only
buy_and_hold_like
```

### 14.2 buy_and_hold_like rule

- Buy at first executable row in evaluation period.
- Sell at last executable row if `force_close_on_end_benchmark=true`.
- Use the same fill model and taker fee logic.
- If first or last fill unavailable, benchmark status is `unavailable`, not zero.

### 14.3 Output

```text
benchmark_results.json
benchmark_equity_curve.parquet
```

---

## 15. Scenario Sensitivity

New file:

```text
src/sis/backtest/engine/scenarios.py
```

### 15.1 Default scenarios

```yaml
base:
  fee_multiplier: 1.0
  extra_slippage_bps: 0

fee_2x:
  fee_multiplier: 2.0
  extra_slippage_bps: 0

slippage_5bps:
  fee_multiplier: 1.0
  extra_slippage_bps: 5

conservative:
  fee_multiplier: 2.0
  extra_slippage_bps: 10
```

### 15.2 Output

```text
scenario_results.parquet
scenario_summary.json
```

### 15.3 Acceptance signal

Report must show if strategy only works in base scenario.

---

## 16. Split Validation

New file:

```text
src/sis/backtest/engine/validation.py
```

### 16.1 v0.1 simple split

```text
train_ratio = 0.7
test_ratio = 0.3
```

### 16.2 Warmup rule

Test period may use warmup rows before test start for indicator calculation, but metrics count only test window.

### 16.3 Output

```text
split_results.json
```

Fields:

```text
train_return
test_return
train_max_drawdown
test_max_drawdown
train_trade_count
test_trade_count
oos_validation_done: true
```

---

## 17. Parameter Sweep

New file:

```text
src/sis/backtest/engine/parameter_sweep.py
```

### 17.1 v0.1 grid

For sample breakout only:

```yaml
entry_lookback: [10, 20, 40]
exit_lookback: [5, 10, 20]
```

### 17.2 Output

```text
parameter_results.parquet
parameter_summary.json
```

### 17.3 Warning

Report must state:

```text
best_parameter_is_in_sample_only: true
```

unless split validation has been run for each parameter set.

---

## 18. Report / Charts

New file:

```text
src/sis/backtest/engine/report.py
src/sis/backtest/engine/charts.py
```

### 18.1 Artifacts

```text
backtest_report.md
backtest_report.html
charts/equity_curve.svg
charts/drawdown.svg
charts/trade_pnl_histogram.svg
charts/cumulative_costs.svg
charts/blocked_reasons.svg
charts/session_breakdown.svg
charts_data/equity_curve.json
charts_data/drawdown.json
charts_data/trades.json
charts_data/blocked_reasons.json
```

### 18.2 Dependency policy

v0.1 should generate SVG with stdlib/string templates. Do not add `matplotlib` unless explicitly accepted.

### 18.3 Required report sections

```text
Run Summary
Scope and Non-Scope
Config Summary
Data Manifest
Data Quality
Strategy Summary
Performance Summary
Benchmark Comparison
Scenario Sensitivity
Split Validation
Parameter Sweep
Trade List Summary
Blocked Events
Session / Market Status Breakdown
Cost Breakdown
Open Position at End
Warnings / Known Limitations
Artifact Paths
```

---

## 19. Artifact Contract

Output directory:

```text
<out_dir>/<run_id>/
```

Required artifacts:

```text
backtest_run.json
config.json
config_hash.txt
data_manifest.json
input_schema_hash.txt
data_quality.json
orders.parquet
fills.parquet
trades.parquet
blocked_events.parquet
equity_curve.parquet
metrics.json
benchmark_results.json
scenario_results.parquet
split_results.json
parameter_results.parquet
candidate_result.json
backtest_report.md
backtest_report.html
charts/*.svg
charts_data/*.json
```

### 19.1 backtest_run.json required fields

```text
run_id
created_at
strategy_id
symbol
timeframe
warmup_start_ts
evaluation_start_ts
evaluation_end_ts
input_data_ref
config_hash
input_schema_hash
fee_model_ref
funding_policy
fill_model
leverage_mode
no_live_order=true
wallet_used=false
exchange_write_used=false
```

---

## 20. Sample Strategy

New file:

```text
src/sis/backtest/trade_xyz/sample_strategies.py
```

### 20.1 SP500 breakout v0

```text
symbol: SP500
entry: close breaks above previous N-bar high
exit: close breaks below previous M-bar low
side: long-only
signal timing: bar close
fill timing: next executable row
```

### 20.2 Important

Close is signal-only. It is not an executable fill price.

---

## 21. Tests

### 21.1 Existing compatibility tests

Do not break:

```text
tests/test_backtest_bridge.py
tests/test_backtest_fixed_horizon.py
tests/strategy_authoring/*
```

### 21.2 New tests

```text
tests/backtest/test_backtest_config.py
tests/backtest/test_period_filter.py
tests/backtest/test_data_quality.py
tests/backtest/test_data_manifest.py
tests/backtest/test_trade_xyz_schema.py
tests/backtest/test_trade_xyz_cost_model.py
tests/backtest/test_entry_exit_gates.py
tests/backtest/test_fill_model.py
tests/backtest/test_portfolio_accounting.py
tests/backtest/test_no_lookahead.py
tests/backtest/test_runner_minimal.py
tests/backtest/test_metrics.py
tests/backtest/test_benchmark.py
tests/backtest/test_scenario_sensitivity.py
tests/backtest/test_split_validation.py
tests/backtest/test_parameter_sweep.py
tests/backtest/test_report_artifacts.py
tests/backtest/test_blocked_reason_report.py
tests/backtest/test_session_breakdown.py
```

### 21.3 High-priority tests

1. `test_no_lookahead.py`
2. `test_portfolio_accounting.py`
3. `test_trade_xyz_cost_model.py`
4. `test_fill_model.py`
5. `test_data_quality.py`
6. `test_report_artifacts.py`

---

## 22. Revised PR Plan

```text
PR-0: Compatibility lock
  - run existing bridge / strategy_authoring tests
  - document existing bridge unchanged

PR-1: Config and contracts
  - config.py
  - order.py
  - fill.py
  - portfolio.py
  - accounting tests

PR-2: Trade[XYZ] schema and data quality
  - schema.py
  - data_quality.py
  - period filter
  - schema/data quality tests

PR-3: Manifest and hashing
  - manifest.py
  - hashing.py
  - config_hash/input_schema_hash/data_manifest tests

PR-4: Cost model and gates
  - cost_model.py
  - gates.py
  - fee, slippage, funding policy tests

PR-5: Fill model and no-lookahead
  - fill.py
  - no-lookahead tests
  - blocked_events ledger tests

PR-6: Minimal runner
  - runner.py
  - deterministic fixture run
  - orders/fills/trades/equity artifacts

PR-7: Metrics and benchmark
  - metrics.py
  - benchmark.py
  - metrics/benchmark artifacts

PR-8: Report and charts
  - report.py
  - charts.py
  - markdown/html/svg/json report tests

PR-9: Scenario/split/parameter sweep
  - scenarios.py
  - validation.py
  - parameter_sweep.py

PR-10: Sample strategy adapter
  - sample_strategies.py
  - SP500 breakout fixture tests

PR-11: CLI exposure optional
  - only after above semantics are pinned
```

---

## 23. Completion Criteria

### 23.1 Functional

- Can run SP500 long-only breakout fixture through runner.
- Can specify evaluation period.
- Can produce all required artifacts.
- Can compare strategy vs cash and buy-and-hold-like benchmark.
- Can run default sensitivity scenarios.
- Can produce markdown + HTML report with SVG charts.

### 23.2 Safety

- No wallet / signing / exchange write dependency.
- Existing `bridge.py` behavior unchanged.
- `fee_mode=unknown` with unresolved fee blocks entry.
- `is_tradable=false` blocks entry.
- `block_reasons` non-empty blocks entry.
- Signal row is not used for fill.
- Funding is not applied per quote row by accident.

### 23.3 Test

- New `tests/backtest/*` pass.
- Existing backtest bridge tests pass.
- `./scripts/check` passes or all failures are unrelated and documented.

### 23.4 Artifact quality

- `config_hash`, `input_schema_hash`, and `data_manifest` exist.
- `fill_price_source` is present for every fill.
- `blocked_reason_counts` are present in metrics and report.
- `funding_policy`, `fill_model`, `fee_model_ref`, `leverage_mode` are present in run metadata.

---

## 24. Stop Conditions

Stop and update plan if any occurs:

```text
Backtest engine needs wallet/signing/exchange write
existing bridge.py must be changed
fee unresolved but entry continues
funding_rate is applied per quote row without interval assertion
same-row close/high/low is used as fill price
runtime data/ artifact is required for unit tests
CLI is required to test engine
SPY -> SP500 mapping is implicit
leverage/liquidation enters v0.1 implementation
L2 replay/partial fill enters v0.1 implementation
matplotlib or heavy chart dependency is added without explicit acceptance
```

---

## 25. v0.2+ Reserved Work

```text
public CLI
short
multi-symbol portfolio
limit/stop/trailing orders
maker fills
partial fills
L2 replay
leverage and liquidation
mark-price based margin
real funding event ingestion
MT5 / IC Markets CFD profile
```
