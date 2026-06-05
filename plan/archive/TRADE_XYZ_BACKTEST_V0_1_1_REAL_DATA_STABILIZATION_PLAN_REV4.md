# Trade[XYZ] Pure Backtest v0.1.1 実装計画 REV4

作成日: 2026-05-31  
対象Repo: `tsutomu-n/marketlens-strike`  
対象ブランチ: `feature/backtest-engine-roadmap`  
目的: 既存の Trade[XYZ] 純粋バックテスト v0.1 を、実データで安全に回せる状態へ安定化する。

---

## 0. 結論

この計画は、既に存在する `run_backtest()` ベースの Trade[XYZ] 純粋バックテスト v0.1 を、次の状態へ進めるための実装指示である。

```text
v0.1 現状:
  - Python API run_backtest() で直接実行できる
  - fixture では artifact / metrics / report / chart を出せる
  - SP500 など単一symbol、long-only、market-like taker fill
  - close ベースの breakout signal
  - fee / slippage / funding v0 / entry gate / accounting / artifact 出力あり

v0.1.1 目標:
  - data/normalized/quotes.parquet の実データを、ad-hoc補正なしでBT入力へ変換できる
  - quote rows から bar-like frame を生成できる
  - entry signal row だけでなく、next-row fill row の実行可否もgateできる
  - 実データ smoke run を script と skip可能test で再現できる
  - report / charts の placeholder を減らし、blocked / session / trade PnL を読める
  - scenario / parameter sweep の現状が「派生値」なのか「実再実行」なのか明確になる
```

最重要方針は以下。

```text
戦略最適化へ進む前に、実データ接続・時間足化・fill gate・artifact可読性を固める。
```

---

## 1. 現在の実装前提

現行Repoでは、以下が既に存在する前提で計画する。

### 1.1 現行API

```python
run_backtest(
    *,
    config: BacktestConfig,
    market_data: pl.DataFrame,
    out_dir: Path,
    input_data_ref: str,
    breakout: BreakoutParameters | None = None,
) -> BacktestRunResult
```

### 1.2 現行BacktestConfig

既に以下を持つ。

```text
PeriodConfig:
  warmup_start_ts
  evaluation_start_ts
  evaluation_end_ts

PositionSizingConfig:
  fixed_notional
  notional_usd
  max_position_notional_usd

ExecutionConfig:
  long_only
  market_like_taker_v0
  extra_slippage_bps
  force_close_on_end

CostConfig:
  fee_model_ref
  fee_scenario
  fee_multiplier
  funding_policy

GateConfig:
  block_reasons
  is_tradable
  max_spread_bps
  min_depth_10bps_usd
  max_bound_distance
  max_oi_cap_usage

LeverageConfig:
  disabled only

ReportConfig:
  markdown/html/svg/json chart output
```

### 1.3 現行artifact

現行runnerは、少なくとも以下を出す。

```text
backtest_run.json
config.json
config_hash.txt
input_schema_hash.txt
data_quality.json
data_manifest.json
orders.parquet
fills.parquet
trades.parquet
blocked_events.parquet
equity_curve.parquet
metrics.json
benchmark_results.json
benchmark_equity_curve.parquet
scenario_results.parquet
scenario_summary.json
split_results.json
parameter_results.parquet
parameter_summary.json
candidate_result.json
backtest_report.md
backtest_report.html
charts/*.svg
charts_data/*.json
```

---

## 2. 今回の目的

### 2.1 目的

Trade[XYZ] の実データ `data/normalized/quotes.parquet` を使って、`run_backtest()` を安全に回せるようにする。

具体的には以下を実現する。

1. `normalized quotes` を `run_backtest()` 入力用frameへ変換する正式関数を追加する。
2. quote rows を 1h などの bar-like frame へ変換できるようにする。
3. next-row fill 時点でも `is_tradable`, `block_reasons`, `market_status`, fee, price を検査する。
4. 実データがある場合のみ実行する smoke test を追加する。
5. 手動確認用の script を追加する。ただし public Typer CLI ではない。
6. report / charts のうち placeholder のままの箇所を可能な範囲で実データ化する。
7. scenario / parameter sweep が派生計算か実再実行かを artifact 上で明示し、必要なら実再実行へ進める。

---

## 3. 制約

### 3.1 今回の対象

```text
Trade[XYZ] only
pure backtest only
Python API run_backtest() primary
real normalized quotes smoke
quote -> backtest frame
quote -> bar-like frame
long-only
single-symbol
market-like taker fill
fixture-first unit tests
runtime-data optional integration-ish test
```

### 3.2 今回の非対象

```text
public Typer CLI registration
live trading
paper trading extension
wallet
signing
exchange write
nonce / cloid lifecycle
short
multi-symbol portfolio
limit / stop / trailing order
post-only / maker fill
partial fill
L2 replay
leverage / liquidation
MT5 / IC Markets / CFD
LLM strategy judge
```

### 3.3 変更してはいけないもの

以下のpublic behaviorを壊さない。

```text
src/sis/backtest/bridge.py
src/sis/backtest/costs.py
src/sis/backtest/signals.py
src/sis/execution/*
src/sis/paper/*
src/sis/commands/strategy_authoring.py
src/sis/cli.py の既存登録
uv run sis build-backtest
uv run sis strategy-author-run --spec <path> --through backtest
```

public CLI追加は、この計画の最後でもまだ任意。原則は script と direct Python API で確認する。

---

## 4. 実装タスク一覧

---

# PR-0: 現行互換・ベースライン確認

## 目的

現在の v0.1 実装が壊れていないことを確認してから、v0.1.1 の変更へ入る。

## 対象ファイル

変更なし。

確認対象:

```text
tests/backtest/*
src/sis/backtest/engine/runner.py
src/sis/backtest/engine/config.py
src/sis/backtest/trade_xyz/schema.py
```

## 実施内容

```bash
uv run pytest tests/backtest -q
./scripts/check
```

`./scripts/check` が環境上使えない場合は、少なくとも以下を実行する。

```bash
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

## 完了条件

- `tests/backtest` が通る。
- 既存bridge / paper / execution 関連の既存testが壊れていない。
- 変更前の状態をGit commitまたは作業メモで保持する。

## Stop condition

- 既存 `build-backtest` の挙動変更が必要になった場合は中断する。
- `src/sis/cli.py` の既存command登録を触る必要が出た場合は中断する。

---

# PR-1: Trade[XYZ] quote rows -> backtest frame 変換を正式化

## 目的

現在は実データ smoke 時に `close = mid_price` を手元scriptで補う必要がある。これを正式な変換関数として実装する。

## 追加ファイル

```text
src/sis/backtest/trade_xyz/market_data.py
tests/backtest/test_trade_xyz_market_data.py
```

## 変更しないファイル

```text
src/sis/backtest/trade_xyz/schema.py
```

`schema.py` は引き続き canonical schema normalizer として残す。`close_source` の選択は `market_data.py` の責務とする。

## 実装する関数

```python
def load_normalized_quotes(path: Path) -> pl.DataFrame:
    """Read normalized Trade[XYZ] quote parquet."""
```

```python
def prepare_quote_rows_for_backtest(
    frame: pl.DataFrame,
    *,
    symbol: str,
    close_source: Literal["mid_price", "mark_price", "oracle_price", "index_price"] = "mid_price",
) -> pl.DataFrame:
    """
    Convert normalized quote rows into run_backtest-compatible rows.

    Responsibilities:
      - exact symbol filter
      - no implicit SPY->SP500 or QQQ->XYZ100 mapping
      - close = selected close_source
      - keep event source columns such as ts_client/source_ts_ms/recv_ts_ms
      - keep executable price columns
      - sort by event_ts after schema normalization
    """
```

```python
def infer_period_from_event_ts(frame: pl.DataFrame) -> tuple[datetime, datetime]:
    """Return min/max event_ts bounds for quick smoke config."""
```

## 仕様

### symbol filter

- `symbol` は uppercase する。
- 入力が `canonical_symbol` を持つ場合、完全一致でfilterする。
- 入力が `symbol` を持つ場合も完全一致でfilterする。
- `SPY -> SP500` や `QQQ -> XYZ100` の暗黙変換は禁止。
- 対象symbolの行が0なら `ValueError`。

### close_source

- `close_source` は `mid_price` をdefaultとする。
- `close` が既にあっても、指定された `close_source` から `close` を明示的に作る。
- `close_source` が存在しない場合は `ValueError`。
- `close_source` が全nullの場合は `ValueError`。
- 一部nullの場合は行を落とさず、後段data qualityで検出させる。ただし `close` null count を返すreport helperを用意してもよい。

### event time

- `ts_client` または `event_ts` を使う。
- 実際のparseとtimezone検証は既存 `normalize_trade_xyz_market_data()` に任せる。
- `source_ts_ms` / `recv_ts_ms` は保持する。

### 出力

`run_backtest()` へそのまま渡せる `pl.DataFrame` を返す。

## テスト方針

`tests/backtest/test_trade_xyz_market_data.py` に以下を追加する。

1. `canonical_symbol=SP500`, `mid_price` ありのfixtureで `close` が作られる。
2. `symbol` column入力でも動く。
3. `symbol=SPY` 入力を `SP500` として扱わない。
4. `close_source` missing で `ValueError`。
5. `close_source` 全null で `ValueError`。
6. 出力が `event_ts` 昇順。
7. unit test は `data/normalized/quotes.parquet` に依存しない。

## 完了条件

- `prepare_quote_rows_for_backtest()` を使えば、実データに対する ad-hoc `close = mid_price` 補正scriptが不要になる。
- `run_backtest()` にはこの関数の出力を渡せる。

---

# PR-2: quote rows -> bar-like frame builder

## 目的

現状の `entry_lookback=20` は「20 quote rows」であり「20本の1h bar」ではない。これを解消するため、quote rows から bar-like frame を作る。

## 追加ファイル

```text
src/sis/backtest/trade_xyz/bar_builder.py
tests/backtest/test_trade_xyz_bar_builder.py
```

## 実装する関数

```python
def build_quote_bars(
    frame: pl.DataFrame,
    *,
    symbol: str,
    timeframe: Literal["30m", "1h", "4h", "1d"] = "1h",
    close_source: Literal["mid_price", "mark_price", "oracle_price", "index_price"] = "mid_price",
) -> pl.DataFrame:
    """Build conservative bar-like rows from prepared or normalized Trade[XYZ] quote rows."""
```

## 重要な時間仕様

- bar row の `event_ts` は **bar close time** とする。
- signal は bar close 時点で生成される扱い。
- 約定は next row で行われるため、次bar rowの `exec_buy_price` / `exec_sell_price` は **そのbar内の最初のexecutable price** とする。
- これにより、前barのsignalが次bar開始付近価格でfillされる。

## 集計仕様

入力は `prepare_quote_rows_for_backtest()` の出力、または同等列を持つframe。

### price OHLC

`close_source` から以下を作る。

```text
open  = first close_source in bar
high  = max close_source in bar
low   = min close_source in bar
close = last close_source in bar
```

### executable prices for next-row fill

```text
exec_buy_price:
  first non-null among exec_buy_price, best_ask, ask_price, mid + spread/2 inside the bar

exec_sell_price:
  first non-null among exec_sell_price, best_bid, bid_price, mid - spread/2 inside the bar
```

注意: `exec_buy_price` / `exec_sell_price` は bar close 価格ではない。next-row fill用のbar開始側実行価格である。

### bid/ask/mid/spread

```text
best_bid: last non-null best_bid in bar
best_ask: last non-null best_ask in bar
mid_price: last non-null mid_price in bar
spread_bps: max spread_bps in bar  # conservative for gates
```

### tradability / gates

```text
is_tradable:
  True only if all rows in bar are tradable

market_status:
  "open" only if all non-null statuses are "open"
  otherwise "mixed_or_not_open"

block_reasons:
  union of all block_reasons in the bar

min_side_depth_10bps_usd:
  min non-null value in the bar

open_interest_usd:
  last non-null value in bar

oi_cap_usage:
  max non-null value in bar

bound_distance:
  max non-null value in bar
```

### fee

```text
taker_fee_bps:
  last non-null taker_fee_bps in bar

maker_fee_bps:
  last non-null maker_fee_bps in bar

fee_mode:
  last non-null fee_mode in bar
```

### funding

v0.1.1では real quote bars から funding event を生成しない。

```text
funding_rate:
  last non-null funding_rate may be carried for visibility

is_funding_event:
  False by default unless input explicitly contains true event rows and test covers it
```

`fixture_hourly_v0` 用の funding event は別fixtureでのみ使う。

## テスト方針

`tests/backtest/test_trade_xyz_bar_builder.py` に以下を追加する。

1. 1h内の複数quoteから1barが作られる。
2. `event_ts` はbar close timeになる。
3. `open/high/low/close` が `close_source` から正しく作られる。
4. `exec_buy_price` がbar内の最初のask系価格になる。
5. `exec_sell_price` がbar内の最初のbid系価格になる。
6. `spread_bps` はmaxになり、`min_side_depth_10bps_usd` はminになる。
7. bar内に `is_tradable=false` が1行でもあればbarはfalse。
8. bar内の `block_reasons` がunionされる。
9. `fee_mode` / `taker_fee_bps` / `maker_fee_bps` はlast non-nullになる。
10. `close_source` missing で `ValueError`。

## 完了条件

- `build_quote_bars(..., timeframe="1h")` の出力を `run_backtest()` へ渡せる。
- `entry_lookback=20` が20 quote rowsではなく20 barsを意味する使い方が可能になる。

---

# PR-3: next-row fill row execution gate を追加

## 目的

現行runnerは、entry signal rowではgateするが、pending orderが実際にfillされる next row では価格とfee中心の確認に留まる。これだと、signal rowはtradableでも fill row が `is_tradable=false` または `block_reasons` 非空のときに約定してしまうリスクがある。

## 変更ファイル

```text
src/sis/backtest/trade_xyz/gates.py
src/sis/backtest/engine/runner.py
tests/backtest/test_fill_row_execution_gate.py
```

## 追加する関数案

`gates.py` に追加する。

```python
def evaluate_open_fill_gate(
    row: dict[str, Any],
    *,
    gates: GateConfig,
    fee: FeeResolution,
    fill_price_resolved: bool,
) -> GateResult:
    """Gate applied to the actual next-row fill for opening orders."""
```

```python
def evaluate_close_fill_gate(
    row: dict[str, Any],
    *,
    fee: FeeResolution,
    fill_price_resolved: bool,
) -> GateResult:
    """Gate applied to the actual next-row fill for closing orders."""
```

## open fill gate仕様

opening fill rowでは以下を検査する。

```text
fill_price_resolved
fee.resolved
is_tradable == true unless config allows otherwise
block_reasons empty unless config allows otherwise
market_status == open
spread_bps <= max_spread_bps if configured
min_side_depth_10bps_usd >= min_depth_10bps_usd if configured
bound_distance <= max_bound_distance if configured
oi_cap_usage <= max_oi_cap_usage if configured
```

reason名はentry gateと区別するため、prefixを付ける。

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

## close fill gate仕様

closing fill rowでは以下を検査する。

```text
fill_price_resolved
fee.resolved
market_status in {open, close_only, unknown_if_fixture}
```

v0.1.1では、close fill rowで `is_tradable=false` をどう扱うかを厳密化しすぎない。理由は、OI cap到達時など「新規不可・決済可」の状態があり得るため。`market_status=close_only` を許可する。

ただし、`block_reasons` に `HALT`, `NO_QUOTES`, `FILL_PRICE_MISSING` 等がある場合は price unresolved か別reasonで止める。block reasonの詳細分類はv0.2以降。

## runner.py変更

`_fill_order()` 内で、価格とfeeを解決した後、position_effectに応じてfill row gateを呼ぶ。

```text
if order.position_effect == "open":
  evaluate_open_fill_gate(...)

if order.position_effect == "close":
  evaluate_close_fill_gate(...)
```

gateが不許可なら `Fill` を作らず `BlockedEvent` を返す。

BlockedEvent:

```text
action:
  open -> "open_fill"
  close -> "close_fill"

reason:
  first gate reason or all reasons as separate events
```

既存entry gateと同じく、複数reasonを別イベントとして記録してよい。

## テスト方針

`tests/backtest/test_fill_row_execution_gate.py` に以下を追加する。

1. signal rowはtradable、next fill rowが `is_tradable=false` ならfillされずblockedになる。
2. next fill rowが `block_reasons=["BLOCK_FUNDING_MISSING"]` ならopen fillされない。
3. next fill rowの `market_status="closed"` ならopen fillされない。
4. next fill rowのfee unresolvedならfillされない。
5. close fillでは `market_status="close_only"` を許可する。
6. force close on end も close fill gateを通る。
7. blocked_eventsに `fill_row_*` reasonが出る。

## 完了条件

- entry gateだけではなく、実際のfill rowでも安全条件が確認される。
- untradable rowでopen fillできない。
- close-only rowでcloseは可能。

---

# PR-4: 実データ smoke script と optional integration test

## 目的

`data/normalized/quotes.parquet` が存在するローカル環境で、実データを使って `run_backtest()` を手動確認できるようにする。

unit testはruntime artifactに依存しない。実データtestは存在時のみskip解除される integration-ish test とする。

## 追加ファイル

```text
scripts/run_trade_xyz_backtest_smoke.py
tests/backtest/test_real_quotes_smoke.py
```

## smoke script仕様

public Typer CLIではなく、単独scriptにする。

実行例:

```bash
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --out data/backtests \
  --entry-lookback 20 \
  --exit-lookback 10
```

引数:

```text
--input: default data/normalized/quotes.parquet
--symbol: default SP500
--timeframe: raw_quote_rows | 30m | 1h | 4h | 1d
--close-source: mid_price | mark_price | oracle_price | index_price
--out: default data/backtests
--entry-lookback: default 20
--exit-lookback: default 10
--initial-cash-usd: default 10000
--notional-usd: default 1000
--max-spread-bps: optional
--min-depth-10bps-usd: optional
--force-close-on-end: bool flag
```

処理:

```text
1. load_normalized_quotes(input)
2. prepare_quote_rows_for_backtest(...)
3. if timeframe != raw_quote_rows: build_quote_bars(...)
4. infer period from event_ts
5. BacktestConfigを作る
6. run_backtest()
7. run_dir と主要metricsをstdoutへ出す
```

stdout例:

```text
run_dir: data/backtests/sp500-1h-smoke-20260531T...
rows: 120
trades: 3
net_return_after_cost: ...
max_drawdown: ...
report: .../backtest_report.html
```

## test_real_quotes_smoke.py仕様

- `data/normalized/quotes.parquet` がなければ `pytest.skip()`。
- `SP500` rows がなければ `pytest.skip()`。
- `prepare_quote_rows_for_backtest()` を使う。
- row数が少ない場合は `entry_lookback=2`, `exit_lookback=2` など小さい値で smokeする。
- performance数値の良否はassertしない。

assert:

```text
run_dir exists
metrics.json exists
backtest_report.html exists
orders/fills/trades/equity parquet exist
data_quality.status in {pass, warn}
```

## 完了条件

- 実データがあるローカルではsmoke scriptが動く。
- 実データがないfresh checkoutではtestがskipされ、unit testが落ちない。

---

# PR-5: report / charts の可読性改善

## 目的

現行artifactはHTML/Markdown/SVG/JSONを出すが、一部chartがplaceholderである。人間が読むため、最低限の実データchartへ置き換える。

## 変更ファイル

```text
src/sis/backtest/engine/artifacts.py
src/sis/backtest/engine/charts.py
src/sis/backtest/engine/report.py
tests/backtest/test_report_artifacts.py
```

## 実装内容

### 1. trade_pnl_histogram.svg

- trades_frame が空なら「No trades」placeholder。
- trades_frame に `net_pnl` があれば bins を作ってSVG棒グラフを出す。
- 追加依存は禁止。標準ライブラリでSVG生成。

### 2. blocked_reasons.svg

- blocked_frame の `reason` を集計して棒グラフ。
- blocked_frame が空なら「No blocked events」。

### 3. session_breakdown.svg

- equity_frame または trades_frame の `session_type` ごとに count / pnl を集計。
- 最初は `trade_count by session` でよい。
- trades_frameがsession_typeを持たない場合は equity_frame の row count by session で代替し、reportにその旨を表示。

### 4. cumulative_costs.svg

現行は各fillのcost値をline化しているが、累積になっていない。以下に修正する。

```text
cumulative_cost[i] = sum(fee_amount + extra_slippage_amount up to i)
```

### 5. charts_data JSON

以下を追加または明確化する。

```text
charts_data/cumulative_costs.json
charts_data/session_breakdown.json
```

## テスト方針

`tests/backtest/test_report_artifacts.py` を追加または拡張。

assert:

```text
charts/trade_pnl_histogram.svg contains <svg
charts/blocked_reasons.svg contains known blocked reason label when blocked exists
charts/session_breakdown.svg contains session label
charts/cumulative_costs.svg uses cumulative increasing values for positive costs
charts_data/session_breakdown.json exists
```

## 完了条件

- report HTMLを開けば、少なくとも equity, drawdown, trade PnL, cumulative costs, blocked reasons, session breakdown が読める。
- placeholderはデータが空の場合だけ許可。

---

# PR-6: scenario / parameter sweep を「派生値」から「実再実行」へ分離

## 目的

現行runnerの `scenario_results.parquet` は `cost_derived_v0`、`parameter_results.parquet` はbase metricsからの簡易差分であり、戦略評価には使えない。これをartifact contractとして明確化し、必要なら実再実行を実装する。

## 変更ファイル

```text
src/sis/backtest/engine/runner.py
src/sis/backtest/engine/scenarios.py
src/sis/backtest/engine/parameter_sweep.py
tests/backtest/test_scenario_sensitivity.py
tests/backtest/test_parameter_sweep.py
```

## 実装方針

### 6.1 まず既存methodを明示

既存派生値を残す場合、artifactに明確に書く。

```text
scenario_method = cost_derived_v0
parameter_method = derived_placeholder_v0
usable_for_strategy_selection = false
```

### 6.2 実再実行モードを追加

BacktestConfigに以下を追加するか、runner引数で受ける。

```python
class SensitivityConfig(BaseModel):
    scenario_mode: Literal["derived_v0", "rerun_v1"] = "derived_v0"
    parameter_mode: Literal["derived_v0", "rerun_v1"] = "derived_v0"
```

ただし、config肥大化を避けるなら、v0.1.1では `run_sensitivity_reruns: bool = False` を runner の optional 引数にしてもよい。

推奨は、BacktestConfigに入れる。

### 6.3 内部core分離

artifactを書かずに1回分のloopを実行する内部関数を切る。

```python
@dataclass(frozen=True)
class BacktestCoreResult:
    orders_frame: pl.DataFrame
    fills_frame: pl.DataFrame
    trades_frame: pl.DataFrame
    blocked_frame: pl.DataFrame
    equity_frame: pl.DataFrame
    metrics: dict[str, object]


def _run_backtest_loop(
    *,
    config: BacktestConfig,
    filtered_rows: pl.DataFrame,
    breakout: BreakoutParameters,
) -> BacktestCoreResult:
    ...
```

`run_backtest()` は以下を担当する。

```text
normalize
quality check
manifest
period filter
_run_backtest_loop
benchmark
scenario/parameter
artifact write
```

### 6.4 scenario rerun

`scenario_mode="rerun_v1"` の場合:

- `default_scenarios(config)` でscenario configを作る。
- 各configで `_run_backtest_loop()` を再実行する。
- `net_return_after_cost`, `max_drawdown`, `trade_count`, `fee_impact`, `slippage_impact`, `funding_impact` をscenario_resultsに入れる。

### 6.5 parameter rerun

`parameter_mode="rerun_v1"` の場合:

- `default_breakout_parameter_grid()` の各parameterで `_run_backtest_loop()` を再実行する。
- `entry_lookback`, `exit_lookback`, `net_return_after_cost`, `max_drawdown`, `trade_count`, `profit_factor` を出す。
- reportには `best_parameter_is_in_sample_only=true` を引き続き表示する。

## テスト方針

### scenario

1. `derived_v0` では `scenario_method=cost_derived_v0`。
2. `rerun_v1` では `scenario_method=rerun_v1`。
3. `fee_multiplier=2.0` のscenarioでfillsのfee_bpsが2倍になる。
4. rerun結果のtrade_countが実run由来である。

### parameter

1. `derived_v0` では `parameter_method=derived_placeholder_v0`。
2. `rerun_v1` では各parameterが実行される。
3. entry_lookback差でtrade_countが変わり得るfixtureを作る。
4. `best_parameter_is_in_sample_only=true` は残る。

## 完了条件

- 現行placeholderのままでも、それが選定用ではないと明記される。
- `rerun_v1` を有効化すれば、実際の再バックテスト結果が出る。

---

# PR-7: public CLI公開は任意・最後に行う

## 目的

Python APIとsmoke scriptで安定した後、必要なら `uv run sis backtest-trade-xyz run ...` を追加する。

## 対象ファイル

```text
src/sis/commands/backtest_trade_xyz.py
src/sis/cli.py
tests/test_backtest_trade_xyz_cli.py
```

## CLI仕様案

```bash
uv run sis backtest-trade-xyz run \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --start 2026-05-01T00:00:00Z \
  --end 2026-05-31T23:59:59Z \
  --entry-lookback 20 \
  --exit-lookback 10 \
  --out data/backtests
```

## CLI制約

- wallet / signing / exchange write は一切使わない。
- command名に `trade-xyz` と `backtest` を明示する。
- 既存 `build-backtest` と混同させないhelp文にする。

Help文例:

```text
Run the pure Trade[XYZ] backtest engine. This is not Strategy Lab build-backtest, not paper, and not live execution.
```

## テスト方針

- Typer CLI smoke test。
- tmp_path fixtureを入力に使う。
- runtime artifactに依存しない。
- CLIで出たrun_dirにartifactが存在する。

## 完了条件

- CLI公開前にPR-1〜PR-6が完了している。
- `uv run sis --help` に新commandが出る。
- 既存commandが壊れていない。

---

## 5. 実行順序

実装順は以下で固定する。

```text
P0: 現行互換確認
P1: market_data.py
P2: bar_builder.py
P3: fill-row execution gate
P4: real data smoke script/test
P5: report/chart可読性改善
P6: scenario/parameter rerunの明確化または実装
P7: CLI公開 optional
```

P7は必須ではない。P1〜P5が終わった時点で、Python APIとしては実データ検証へ進める。

---

## 6. テスト方針

### 6.1 unit tests

- `tests/backtest/*` は基本的に `tmp_path` または小さいDataFrame fixtureで完結する。
- `data/normalized/quotes.parquet` に依存しない。
- binary fixtureを増やさない。

### 6.2 optional integration-ish tests

- 実データがある場合だけ走る。
- ない場合はskip。
- performance数値をassertしない。
- artifact存在、data_quality status、report存在だけを確認する。

### 6.3 実行コマンド

必須:

```bash
uv run pytest tests/backtest -q
```

全体確認:

```bash
./scripts/check
```

実データがある場合:

```bash
uv run pytest tests/backtest/test_real_quotes_smoke.py -q
uv run python scripts/run_trade_xyz_backtest_smoke.py --symbol SP500 --timeframe 1h
```

---

## 7. 完了条件

この計画は、以下を満たしたら完了とする。

### 機能完了条件

- `prepare_quote_rows_for_backtest()` が実装され、実normalized quote rowsからBT入力を作れる。
- `build_quote_bars()` が実装され、1h bar-like frameを作れる。
- `run_backtest()` はbar-like frameでも動く。
- next-row fill rowの実行gateがopen fillに適用される。
- real quote smoke scriptが動く。
- 実データがない環境では、real quote smoke testはskipされる。
- report chartのplaceholderが、データありケースでは実chartへ置き換わる。

### 安全完了条件

- `SPY -> SP500` の暗黙変換をしない。
- `data/normalized/quotes.parquet` が無いfresh checkoutでunit testが落ちない。
- `fee_mode=unknown` かつ fee unresolved のentry/open fillができない。
- `is_tradable=false` または `block_reasons` 非空のfill rowでopen fillできない。
- `close` をfill価格として暗黙利用しない。
- fundingをquote rowごとに課金しない。
- live / paper / wallet / signing / exchange write を追加しない。

### 互換完了条件

- 既存 `uv run sis build-backtest` を壊さない。
- 既存 Strategy Authoring through-backtest を壊さない。
- 既存 paper/execution tests を壊さない。
- `src/sis/cli.py` を変更する場合はP7のみ。

### Artifact完了条件

smoke run後に以下がある。

```text
backtest_run.json
config.json
config_hash.txt
input_schema_hash.txt
data_quality.json
data_manifest.json
orders.parquet
fills.parquet
trades.parquet
blocked_events.parquet
equity_curve.parquet
metrics.json
benchmark_results.json
scenario_results.parquet
parameter_results.parquet
backtest_report.md
backtest_report.html
charts/equity_curve.svg
charts/drawdown.svg
charts/cumulative_costs.svg
charts/blocked_reasons.svg
charts/session_breakdown.svg
charts_data/equity_curve.json
charts_data/blocked_reasons.json
```

---

## 8. 誤謬リスクと対策

| リスク | 対策 |
|---|---|
| quote rowの20本を20時間と誤解する | `bar_builder.py` でbar-like frameを作る。reportにtimeframeを残す。 |
| `close=mid_price` をscriptごとにad-hoc補正する | `market_data.py` に正式化する。 |
| signal rowだけgateしてfill rowが不正でも約定する | fill-row execution gateを追加する。 |
| fundingをrowごとに課金する | `nullable_zero_v0` では課金しない。`fixture_hourly_v0` のみ明示eventで課金。 |
| placeholder scenarioを実検証と誤解する | `scenario_method` / `parameter_method` をartifactに明記し、必要ならrerun_v1へ進める。 |
| parameter sweep bestを採用して過学習する | `best_parameter_is_in_sample_only=true` を維持する。 |
| CLIを急いで既存surfaceと混ぜる | CLIはP7 optional。まずscript/APIで確認する。 |
| 実データ依存でfresh checkout testが落ちる | real quote testは存在時のみskip解除。 |

---

## 9. コーダーへの実装メモ

- 追加依存は原則禁止。SVGは既存の標準ライブラリ実装を拡張する。
- `polars` を使う。
- `uv` 前提で実行する。
- `pydantic` modelを増やす場合は、現行 `BacktestConfig` と整合させる。
- 大きな汎用化をしない。Trade[XYZ]専用として実データ接続を優先する。
- MT5/CFD用の `swap`, `contract size`, `point`, `digits`, `margin mode` は入れない。
- 実装で迷ったら、まず `tests/backtest/test_runner_minimal.py` の意味を壊さないことを優先する。

---

## 10. 最終判断

このREV4の範囲では、次を達成する。

```text
Trade[XYZ]実データ970行程度から、quote rows または 1h bar-like frameを作り、
run_backtest()でSP500 long-only breakoutを回し、
fill rowの安全条件を守り、
artifactと人間向けreportを出せる。
```

これが完了してから、戦略最適化、CLI公開、multi-symbol、short、leverage、L2 replayへ進む。

