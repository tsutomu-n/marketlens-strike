# Trade[XYZ] Pure Backtest v0.1.2 実データ Hardening 計画 REV5

作成日: 2026-05-31  
対象Repo: `tsutomu-n/marketlens-strike`  
対象: Trade[XYZ] 専用の純粋バックテスト Python API 実装  
前提: v0.1 は `run_backtest()` Python API として存在し、CLI公開はまだしない。

---

## 0. 結論

REV4 は方向性として妥当だが、実務的には次の誤謬リスクが残る。

1. **bar集約で signal 用情報と fill 用情報が混ざる。**
2. **`entry_lookback=20` を 20 quote rows / 20 bars / 20 hours のどれとして扱うかが曖昧になる。**
3. **実データ970 rowsのカバレッジ不足を、戦略成績として誤読しやすい。**
4. **end-of-run の open position を、約定不能な価格で強制決済してしまう余地がある。**
5. **scenario / parameter sweep の派生値を、実再実行の検証結果として誤読しやすい。**
6. **GitHub上の公開ブランチとローカル実装ブランチが一致しない可能性がある。**

REV5 では、これらを潰すために、次の方針に修正する。

```text
v0.1.2 の目的:
  実データで回ることではなく、実データで回した結果を誤読しないこと。

最優先:
  - code-truth / branch / commit の確認
  - quote rows -> backtest frame の正式化
  - bar signal fields と fill execution snapshot の分離
  - fill row gate の厳格化
  - data coverage / quality / manifest の強化
  - report に「評価可能性」と「非評価理由」を出す
```

---

## 1. 現状でできること

ユーザー提供の現状では、Repoには以下が実装済みとする。

```text
入口:
  src/sis/backtest/engine/runner.py::run_backtest()
  src/sis/backtest/engine/config.py
  src/sis/backtest/trade_xyz/schema.py

できること:
  - SP500 など単一symbolの long-only / single-symbol BT
  - close ベースの breakout signal
  - next-row market-like taker fill
  - fee / slippage / funding v0
  - entry gate
  - portfolio accounting
  - orders/fills/trades/equity/metrics/report/chart artifact 出力

できないこと:
  - CLI公開
  - short / multi-symbol
  - limit / stop / post-only / maker fill
  - partial fill / L2 replay
  - leverage / liquidation
  - live / paper / wallet / signing / exchange write
  - MT5 / IC Markets / CFD
```

この計画は、上記を前提にした **次PR群** である。

---

## 2. 制約

### 2.1 対象

```text
Trade[XYZ] only
pure backtest only
Python API run_backtest() primary
real normalized quotes smoke
quote -> backtest frame
quote -> bar-like frame
fill execution snapshot separation
long-only
single-symbol
market-like taker fill
fixture-first unit tests
runtime-data optional integration-ish test
```

### 2.2 非対象

```text
public Typer CLI registration  # 最後のoptionalのみ
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

### 2.3 変更してはいけない既存surface

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

---

## 3. 事前確認タスク: code-truth / branch / commit

## 目的

GitHub URLだけでは、実装済みの `run_backtest()` が公開ブランチ上に存在するとは限らない。コーダーは、作業前に必ず code-truth を確認する。

## 実施内容

```bash
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short

find src/sis/backtest -maxdepth 4 -type f | sort
find tests/backtest -maxdepth 2 -type f | sort

grep -R "def run_backtest" -n src/sis/backtest || true
grep -R "class BacktestConfig" -n src/sis/backtest || true
```

## 完了条件

`docs` または作業メモに以下を残す。

```text
repo_url:
branch:
commit_sha:
has_run_backtest: true/false
has_backtest_config: true/false
has_trade_xyz_schema: true/false
```

## Stop condition

- `run_backtest()` が見つからない。
- `BacktestConfig` が見つからない。
- `tests/backtest` が存在しない。
- GitHub上のブランチとローカル実装ブランチが違うのに、その差分を確認できない。

この場合、REV5の実装に入らず、まずRepo状態を同期する。

---

## 4. PR-0: 現行互換・ベースライン確認

## 目的

v0.1の既存実装が壊れていないことを確認してから変更する。

## 対象ファイル

変更なし。

確認対象:

```text
tests/backtest/*
src/sis/backtest/engine/runner.py
src/sis/backtest/engine/config.py
src/sis/backtest/trade_xyz/schema.py
src/sis/backtest/trade_xyz/cost_model.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
```

## 実行

```bash
uv run pytest tests/backtest -q
./scripts/check
```

`./scripts/check` が環境上使えない場合は最低限:

```bash
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

## 完了条件

- `tests/backtest` が通る。
- 既存bridge / paper / execution 関連のtestが壊れていない。
- 変更前commitを記録している。

---

## 5. PR-1: normalized quote rows -> backtest frame 変換を正式化

## 目的

実データ smoke のたびに `close = mid_price` を手元scriptで補う状態をやめる。

## 追加ファイル

```text
src/sis/backtest/trade_xyz/market_data.py
tests/backtest/test_trade_xyz_market_data.py
```

## 実装する関数

```python
from pathlib import Path
from typing import Literal
import polars as pl

CloseSource = Literal["mid_price", "mark_price", "oracle_price", "index_price"]
EventTimeSource = Literal["ts_client", "source_ts_ms", "recv_ts_ms"]


def load_normalized_quotes(path: Path) -> pl.DataFrame:
    """Read normalized Trade[XYZ] quote parquet."""


def prepare_quote_rows_for_backtest(
    frame: pl.DataFrame,
    *,
    symbol: str,
    close_source: CloseSource = "mid_price",
    event_time_source: EventTimeSource = "ts_client",
) -> pl.DataFrame:
    """
    Convert normalized Trade[XYZ] quote rows into run_backtest-compatible rows.
    """


def infer_period_from_event_ts(frame: pl.DataFrame) -> tuple[datetime, datetime]:
    """Return min/max event_ts bounds."""
```

## 仕様

### symbol filter

- `symbol` は大文字化して完全一致。
- 入力が `canonical_symbol` を持つ場合は `canonical_symbol == symbol`。
- 入力が `symbol` を持つ場合は `symbol == symbol`。
- `SPY -> SP500`, `QQQ -> XYZ100` の暗黙変換は禁止。
- 対象symbol行が0なら `ValueError`。

### close_source

- `close_source="mid_price"` をdefaultとする。
- 入力に `close` が既にあっても、指定された `close_source` から `close` を明示生成する。
- `close_source` が存在しなければ `ValueError`。
- `close_source` が全nullなら `ValueError`。
- 一部nullは落とさず、後段 `data_quality` で検出する。

### event time

- default は `ts_client`。
- `source_ts_ms` / `recv_ts_ms` を選べるようにするが、v0.1.2のdefaultは変えない。
- 出力の `event_ts` はtimezone-aware UTC相当に正規化する。
- `source_ts_ms` / `recv_ts_ms` は保持する。
- event time sourceは `data_manifest.json` と `backtest_run.json` に残す。

### required executable columns

以下は可能な限り保持する。

```text
exec_buy_price
exec_sell_price
best_bid
best_ask
bid_price
ask_price
mid_price
spread_bps
```

存在しない列はschema側でnullable予約列として補う。fillできるかどうかはfill model / gateが判定する。

### depth column fallback

入力に `min_side_depth_10bps_usd` がない場合、以下から作る。

```text
if bid_depth_10bps_usd and ask_depth_10bps_usd:
  min_side_depth_10bps_usd = min(bid_depth_10bps_usd, ask_depth_10bps_usd)
elif depth_10bps_usd exists:
  min_side_depth_10bps_usd = depth_10bps_usd
else:
  min_side_depth_10bps_usd = null
```

## テスト

`tests/backtest/test_trade_xyz_market_data.py`

1. `canonical_symbol=SP500`, `mid_price`ありで `close` が作られる。
2. `symbol` column入力でも動く。
3. `SPY` は `SP500` として扱われない。
4. `close_source` missingで `ValueError`。
5. `close_source` 全nullで `ValueError`。
6. 出力が `event_ts` 昇順。
7. `event_time_source="source_ts_ms"` を指定した場合にevent_tsが作られる。
8. `min_side_depth_10bps_usd` が bid/ask depthから作られる。
9. unit testは `data/normalized/quotes.parquet` に依存しない。

## 完了条件

- `prepare_quote_rows_for_backtest()` の出力を `run_backtest()` へ渡せる。
- 実データsmoke script側で ad-hoc `close = mid_price` を書かなくてよい。

---

## 6. PR-2: quote rows -> bar-like frame builder。ただし signal fields と fill snapshot を分離する

## 目的

`entry_lookback=20` を20 quote rowsではなく、20本のbarとして扱えるようにする。

REV4の `bar内のfirst executable price` と `bar全体のblock_reasons union` を同じrowに混ぜる設計は、実務上危険である。REV5では、bar rowに **signal用fields** と **fill実行snapshot fields** を分けて持たせる。

## 追加ファイル

```text
src/sis/backtest/trade_xyz/bar_builder.py
tests/backtest/test_trade_xyz_bar_builder.py
```

## 実装する関数

```python
from typing import Literal
import polars as pl

Timeframe = Literal["30m", "1h", "4h", "1d"]


def build_quote_bars(
    frame: pl.DataFrame,
    *,
    symbol: str,
    timeframe: Timeframe = "1h",
    close_source: CloseSource = "mid_price",
) -> pl.DataFrame:
    """Build bar-like rows from prepared or normalized Trade[XYZ] quote rows."""
```

## 出力rowの意味

bar rowの `event_ts` は **bar close time** とする。

bar rowは2種類の情報を持つ。

```text
signal fields:
  open/high/low/close
  signal_is_tradable
  signal_market_status
  signal_block_reasons
  session_type

fill snapshot fields:
  exec_buy_price / exec_sell_price
  fill_best_bid / fill_best_ask
  fill_mid_price
  fill_spread_bps
  fill_is_tradable
  fill_market_status
  fill_block_reasons
  fill_min_side_depth_10bps_usd
  fill_bound_distance
  fill_oi_cap_usage
  fill_taker_fee_bps
  fill_maker_fee_bps
  fill_fee_mode
```

互換のため、既存runnerが読む通常列も残す。ただしrunnerはPR-3でfill時には `fill_*` を優先する。

## 集計仕様

### signal price OHLC

`close_source` から作る。

```text
open  = first close_source in bar
high  = max close_source in bar
low   = min close_source in bar
close = last close_source in bar
```

### signal gate fields

bar close時点の状態を使う。

```text
signal_is_tradable = last non-null is_tradable in bar
signal_market_status = last non-null market_status in bar
signal_block_reasons = last non-null block_reasons in bar
session_type = last non-null session_type in bar
```

理由: signalはbar close時点で生成されるため。

### fill execution snapshot

このbarが「次row fill」として使われるとき、fillはbar開始付近で起きる扱いにする。

```text
fill snapshot = first quote row in the bar that has any executable price candidate
```

実行価格:

```text
exec_buy_price:
  first non-null among exec_buy_price, best_ask, ask_price, mid_price + spread/2 at fill snapshot

exec_sell_price:
  first non-null among exec_sell_price, best_bid, bid_price, mid_price - spread/2 at fill snapshot
```

fill gate fields:

```text
fill_is_tradable = is_tradable at fill snapshot
fill_market_status = market_status at fill snapshot
fill_block_reasons = block_reasons at fill snapshot
fill_spread_bps = spread_bps at fill snapshot
fill_min_side_depth_10bps_usd = min_side_depth_10bps_usd at fill snapshot
fill_bound_distance = bound_distance at fill snapshot
fill_oi_cap_usage = oi_cap_usage at fill snapshot
fill_taker_fee_bps = taker_fee_bps at fill snapshot
fill_maker_fee_bps = maker_fee_bps at fill snapshot
fill_fee_mode = fee_mode at fill snapshot
```

### conservative aggregate fields

report用に以下を追加してもよい。

```text
bar_max_spread_bps
bar_min_side_depth_10bps_usd
bar_block_reason_union
```

ただし、これらをfill約定可否の主判定に使わない。

### funding

real quote barsからfunding eventを生成しない。

```text
funding_rate = last non-null funding_rate for visibility only
is_funding_event = false unless explicit fixture event
```

## テスト

`tests/backtest/test_trade_xyz_bar_builder.py`

1. 1h内の複数quoteから1barが作られる。
2. `event_ts` はbar close time。
3. `open/high/low/close` が `close_source` 由来。
4. `signal_*` fields はbarのlast quote由来。
5. `fill_*` fields はbarのfirst executable quote由来。
6. `fill_block_reasons` はbar全体unionではなくfill snapshot由来。
7. `bar_block_reason_union` はreport用に別列として存在する。
8. `exec_buy_price` はfill snapshotのask系価格。
9. `exec_sell_price` はfill snapshotのbid系価格。
10. `close_source` missingで `ValueError`。

## 完了条件

- 1h bar-like frameを `run_backtest()` へ渡せる。
- `entry_lookback=20` は20 barsとして使える。
- bar全体の未来情報でfill gateしない。

---

## 7. PR-3: fill row execution gateを `fill_*` fields対応にする

## 目的

pending orderがnext rowでfillされるとき、fill rowの実行可否を確認する。

bar modeでは、fill rowの通常列ではなく `fill_*` snapshot fields を優先する。

## 変更ファイル

```text
src/sis/backtest/trade_xyz/gates.py
src/sis/backtest/engine/runner.py
tests/backtest/test_fill_row_execution_gate.py
```

## 追加関数

```python
def execution_value(row: Mapping[str, Any], field: str) -> Any:
    """
    Return fill_<field> if present and non-null, otherwise field.
    Example: execution_value(row, "is_tradable") checks fill_is_tradable first.
    """
```

```python
def evaluate_open_fill_gate(row: Mapping[str, Any], *, gates: GateConfig, fee: FeeResolution, fill_price_resolved: bool) -> GateResult:
    """Gate applied to actual next-row open fill."""
```

```python
def evaluate_close_fill_gate(row: Mapping[str, Any], *, fee: FeeResolution, fill_price_resolved: bool) -> GateResult:
    """Gate applied to actual next-row close fill."""
```

## open fill gate仕様

opening fillでは以下を確認する。

```text
fill_price_resolved
fee.resolved
execution is_tradable == true
execution block_reasons empty
execution market_status in open-like statuses
execution spread_bps <= max_spread_bps if configured
execution min_side_depth_10bps_usd >= min_depth_10bps_usd if configured
execution bound_distance <= max_bound_distance if configured
execution oi_cap_usage <= max_oi_cap_usage if configured
```

reason名:

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

closeでは新規entryより緩くする。

```text
required:
  fill_price_resolved
  fee.resolved

allowed market_status:
  open
  close_only
  unknown_if_fixture
```

v0.1.2では `is_tradable=false` のcloseを一律禁止しない。理由: OI cap等では「新規不可・決済可」があり得るため。価格やfeeが解決できない場合はcloseも禁止する。

## runner.py変更

`_fill_order()` 内で、価格とfee解決後、position effectに応じてfill gateを呼ぶ。

```text
open order:
  evaluate_open_fill_gate(...)

close order:
  evaluate_close_fill_gate(...)
```

不許可なら `Fill` を作らず `BlockedEvent` を作る。

## テスト

1. signal rowはtradable、fill rowが `fill_is_tradable=false` ならopen fillされない。
2. fill rowが `fill_block_reasons=[...]` ならopen fillされない。
3. fill rowの通常 `is_tradable=true` でも `fill_is_tradable=false` が優先される。
4. fill rowのfee unresolvedならopen fillされない。
5. close fillでは `market_status=close_only` を許可する。
6. force close on endもclose gateを通る。
7. blocked_eventsに `fill_row_*` reasonが出る。

## 完了条件

- raw quote modeでもbar modeでも、実際のfill rowで安全条件を確認できる。
- fill snapshot列がある場合はそれを優先する。

---

## 8. PR-4: end-of-run open position policyを明確化する

## 目的

`force_close_on_end=True` のとき、約定不能な最終rowで無理に決済してはいけない。

## 変更ファイル

```text
src/sis/backtest/engine/config.py
src/sis/backtest/engine/runner.py
tests/backtest/test_end_of_run_position_policy.py
```

## 追加設定

```python
EndPositionPolicy = Literal[
    "force_close_if_executable",
    "mark_to_market_only",
    "error_if_open",
]
```

`ExecutionConfig` に追加。

```python
end_position_policy: EndPositionPolicy = "force_close_if_executable"
```

既存 `force_close_on_end` は互換のため残す場合、以下に読み替える。

```text
force_close_on_end=True  -> force_close_if_executable
force_close_on_end=False -> mark_to_market_only
```

## 仕様

### force_close_if_executable

- 最終rowでclose fill gateを通れば決済fillを作る。
- 価格またはfeeが解決できない場合、決済fillを作らない。
- その場合、`open_position_at_end=true` をmetrics/reportに残す。

### mark_to_market_only

- 最終rowで決済fillを作らない。
- equityは `mark_price -> mid_price -> close` の順で評価する。
- `open_position_at_end=true` を残す。

### error_if_open

- 終了時にpositionが残っていれば `BacktestError`。
- unit test / deterministic validation向け。

## テスト

1. 最終rowでclose price/feeが解決できる場合だけforce closeされる。
2. 最終rowがprice unresolvedならfillを作らず `open_position_at_end=true`。
3. `mark_to_market_only` はfillを作らない。
4. `error_if_open` はopen positionで例外。

## 完了条件

- 終了時に偽の決済fillを作らない。
- reportにopen positionの有無が出る。

---

## 9. PR-5: data coverage / quality / manifestを強化する

## 目的

970 rows程度の実データを戦略評価として誤読しないよう、データ量・期間・bar数・欠損を明示する。

## 変更ファイル

```text
src/sis/backtest/engine/data_quality.py
src/sis/backtest/engine/manifest.py
src/sis/backtest/engine/report.py
tests/backtest/test_data_quality.py
tests/backtest/test_data_manifest.py
```

## 追加項目

`data_quality.json` に追加。

```json
{
  "status": "pass|warn|fail",
  "input_row_count": 970,
  "filtered_row_count": 120,
  "bar_count": 18,
  "evaluation_bar_count": 12,
  "symbol_count": 1,
  "first_event_ts": "...",
  "last_event_ts": "...",
  "coverage_seconds": 0,
  "median_event_gap_seconds": 0,
  "max_event_gap_seconds": 0,
  "duplicate_event_ts_count": 0,
  "out_of_order_count": 0,
  "null_critical_field_counts": {},
  "insufficient_coverage_for_strategy": true,
  "required_min_rows": 0,
  "required_min_bars": 0
}
```

`data_manifest.json` に追加。

```json
{
  "input_data_ref": "data/normalized/quotes.parquet",
  "input_file_sha256": "... or null",
  "input_schema_hash": "...",
  "event_time_source": "ts_client",
  "close_source": "mid_price",
  "timeframe": "1h",
  "bar_builder": "quote_bar_v1",
  "data_is_runtime_artifact": true
}
```

## 重要仕様

- `input_file_sha256` はpathが存在するファイルなら計算する。
- DataFrameがメモリfixture由来なら `input_file_sha256=null` でよいが、`input_schema_hash` は必須。
- `required_min_bars = warmup + entry_lookback + exit_lookback + 3` を目安に出す。
- 不足時はBacktest自体を止めるのではなく、`data_quality.status="warn"` とし、reportに「戦略評価に不足」と表示する。
- unit testで `data/normalized/quotes.parquet` を必須にしない。

## テスト

1. duplicate timestampを検出する。
2. out-of-order rowsを検出する。
3. null critical fieldsを数える。
4. insufficient coverageをwarnにする。
5. input file hashが記録される。
6. in-memory fixtureではfile hash nullだがschema hashあり。

## 完了条件

- reportだけ読んでも「このrunが戦略評価に足るデータ量か」が分かる。

---

## 10. PR-6: 実データ smoke script と optional integration-ish test

## 目的

ローカルに `data/normalized/quotes.parquet` がある場合だけ、実データで `run_backtest()` を確認できるようにする。

## 追加ファイル

```text
scripts/run_trade_xyz_backtest_smoke.py
tests/backtest/test_real_quotes_smoke.py
```

## script仕様

```bash
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --event-time-source ts_client \
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
--event-time-source: ts_client | source_ts_ms | recv_ts_ms
--out: default data/backtests
--entry-lookback: default 20
--exit-lookback: default 10
--initial-cash-usd: default 10000
--notional-usd: default 1000
--max-spread-bps: optional
--min-depth-10bps-usd: optional
--end-position-policy: default force_close_if_executable
--auto-small-lookback: smoke専用。データ不足時にentry/exitを2へ下げる。reportに必ず記録。
```

`--auto-small-lookback` は戦略評価ではなく smoke専用。使った場合、`candidate_result.json` に以下を入れる。

```json
{
  "smoke_only": true,
  "auto_small_lookback_used": true,
  "usable_for_strategy_selection": false
}
```

## test_real_quotes_smoke.py仕様

- `data/normalized/quotes.parquet` がなければ `pytest.skip()`。
- `SP500` rowsがなければ `pytest.skip()`。
- performanceの良否はassertしない。

assert:

```text
run_dir exists
metrics.json exists
backtest_report.html exists
orders/fills/trades/equity parquet exist
data_quality.status in {pass, warn}
if auto-small-lookback used, usable_for_strategy_selection=false
```

## 完了条件

- 実データがある環境ではsmoke scriptが動く。
- 実データがないfresh checkoutではtestがskipされる。

---

## 11. PR-7: report / charts の可読性改善

## 目的

人間が読んで異常を見つけられるreportにする。

## 変更ファイル

```text
src/sis/backtest/engine/artifacts.py
src/sis/backtest/engine/charts.py
src/sis/backtest/engine/report.py
tests/backtest/test_report_artifacts.py
```

## 追加・修正するcharts

```text
charts/equity_curve.svg
charts/drawdown.svg
charts/trade_pnl_histogram.svg
charts/cumulative_costs.svg
charts/blocked_reasons.svg
charts/session_breakdown.svg
charts/data_quality_timeline.svg  # optional
```

追加JSON:

```text
charts_data/cumulative_costs.json
charts_data/session_breakdown.json
charts_data/blocked_reasons.json
charts_data/data_quality.json
```

## reportに必ず出す項目

```text
run_id
strategy_id
symbol
timeframe
close_source
event_time_source
input_data_ref
input_file_sha256
row_count / bar_count / coverage
usable_for_strategy_selection true/false
smoke_only true/false
scenario_method
parameter_method
open_position_at_end
end_position_policy
fee_source_summary
funding_policy
fill_model
```

## 重要仕様

- HTMLは外部CSS/JS/remote imageに依存しない。
- SVGは標準ライブラリで生成する。追加依存は原則禁止。
- データが空の場合のみplaceholderを許可する。

## テスト

1. report HTMLに `usable_for_strategy_selection` が出る。
2. blocked reason chartがreason labelを含む。
3. session chartがsession labelを含む。
4. cumulative costsが累積値になる。
5. 外部URL参照を含まない。

## 完了条件

- HTMLを開くだけで、runの評価可能性・制約・異常が分かる。

---

## 12. PR-8: scenario / parameter sweep の意味を明確化し、必要ならrerun化

## 目的

派生計算と実再実行の混同を防ぐ。

## 変更ファイル

```text
src/sis/backtest/engine/runner.py
src/sis/backtest/engine/scenarios.py
src/sis/backtest/engine/parameter_sweep.py
tests/backtest/test_scenario_sensitivity.py
tests/backtest/test_parameter_sweep.py
```

## 段階1: 現状のmethodをartifactに明示

```json
{
  "scenario_method": "cost_derived_v0",
  "parameter_method": "derived_placeholder_v0",
  "usable_for_strategy_selection": false
}
```

## 段階2: rerun_v1を追加

内部APIを切る。

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

`run_backtest()` はartifact writerとして残す。

## scenario rerun

- `fee_multiplier`, `extra_slippage_bps`, `funding_policy` を変えたconfigで `_run_backtest_loop()` を再実行。
- `scenario_results.parquet` に `scenario_method="rerun_v1"`。

## parameter rerun

- `entry_lookback`, `exit_lookback` gridで `_run_backtest_loop()` を再実行。
- `best_parameter_is_in_sample_only=true` を維持。

## テスト

1. derived_v0ではstrategy selection不可。
2. rerun_v1では各scenario/parameterが実run由来。
3. fee_multiplier=2.0でfeeが2倍になる。
4. parameter差でtrade_countが変わるfixtureを作る。

## 完了条件

- placeholderを実検証と誤読できない。
- rerun_v1を使えば実再実行結果になる。

---

## 13. PR-9: public CLI公開 optional

## 目的

Python APIとsmoke scriptが安定した後、必要ならCLI公開する。

## 対象ファイル

```text
src/sis/commands/backtest_trade_xyz.py
src/sis/cli.py
tests/test_backtest_trade_xyz_cli.py
```

## CLI案

```bash
uv run sis backtest-trade-xyz run \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --event-time-source ts_client \
  --start 2026-05-01T00:00:00Z \
  --end 2026-05-31T23:59:59Z \
  --entry-lookback 20 \
  --exit-lookback 10 \
  --out data/backtests
```

## help文

```text
Run the pure Trade[XYZ] backtest engine. This is not Strategy Lab build-backtest, not paper trading, and not live execution.
```

## 完了条件

- PR-1〜PR-8完了後のみ追加する。
- 既存 `build-backtest` と混同しない。
- wallet / signing / exchange write を一切触らない。

---

## 14. 実装順序

```text
P-1: code-truth / branch / commit確認
P0: 現行互換確認
P1: market_data.py
P2: bar_builder.py with signal/fill split
P3: fill-row execution gate with fill_* precedence
P4: end-of-run open position policy
P5: data coverage / quality / manifest強化
P6: real data smoke script/test
P7: report/chart可読性改善
P8: scenario/parameter meaning or rerun
P9: CLI optional
```

P9は必須ではない。P1〜P7で、Python APIとして実データ検証に進める。

---

## 15. テスト方針

### unit tests

- `tests/backtest/*` は `tmp_path` または小さいDataFrame fixtureで完結。
- `data/normalized/quotes.parquet` に依存しない。
- binary fixtureを増やさない。

### optional integration-ish tests

- 実データがある場合だけ走る。
- ない場合はskip。
- 成績数値をassertしない。
- artifact存在、data_quality status、report存在を確認する。

### 実行コマンド

```bash
uv run pytest tests/backtest -q
./scripts/check
```

実データがある場合:

```bash
uv run pytest tests/backtest/test_real_quotes_smoke.py -q
uv run python scripts/run_trade_xyz_backtest_smoke.py --symbol SP500 --timeframe 1h
```

---

## 16. 完了条件

### 機能完了条件

- `prepare_quote_rows_for_backtest()` で実normalized quote rowsからBT入力を作れる。
- `build_quote_bars()` で1h bar-like frameを作れる。
- bar rowはsignal fieldsとfill snapshot fieldsを分離している。
- `run_backtest()` はraw quote rowsでもbar-like frameでも動く。
- fill row gateがopen fillに適用される。
- end-of-run open position policyが明示される。
- real quote smoke scriptが動く。
- report/chartがデータありケースで実チャートを出す。

### 安全完了条件

- `SPY -> SP500` の暗黙変換をしない。
- `data/normalized/quotes.parquet` が無いfresh checkoutでunit testが落ちない。
- `fee_mode=unknown` かつ fee unresolved のentry/open fillができない。
- `is_tradable=false` または `block_reasons` 非空のfill rowでopen fillできない。
- `close` をfill価格として暗黙利用しない。
- fundingをquote rowごとに課金しない。
- 約定不能な最終rowで偽のforce closeを作らない。
- live / paper / wallet / signing / exchange write を追加しない。

### 互換完了条件

- 既存 `uv run sis build-backtest` を壊さない。
- 既存 Strategy Authoring through-backtest を壊さない。
- 既存 paper/execution tests を壊さない。
- `src/sis/cli.py` 変更はPR-9のみ。

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
candidate_result.json
backtest_report.md
backtest_report.html
charts/equity_curve.svg
charts/drawdown.svg
charts/cumulative_costs.svg
charts/blocked_reasons.svg
charts/session_breakdown.svg
charts_data/equity_curve.json
charts_data/blocked_reasons.json
charts_data/session_breakdown.json
```

---

## 17. 誤謬リスクと対策

| リスク | 対策 |
|---|---|
| GitHub mainを見て、実装済みv0.1がないと誤解する | 作業前にbranch/commit/code-truthを確認する。 |
| quote rowの20本を20時間と誤解する | `bar_builder.py` を作り、reportにtimeframeとbar_countを残す。 |
| bar全体のfuture情報でfill gateする | signal fieldsとfill snapshot fieldsを分離する。 |
| `close=mid_price` をscriptごとにad-hoc補正する | `market_data.py` に正式化する。 |
| signal rowだけgateしてfill rowが不正でも約定する | fill-row execution gateを追加する。 |
| fundingをrowごとに課金する | `nullable_zero_v0` では課金しない。`fixture_hourly_v0` のみ明示eventで課金。 |
| 最終rowで約定不能なのにforce closeする | end-of-run open position policyを追加する。 |
| placeholder scenarioを実検証と誤読する | `scenario_method` / `parameter_method` をartifactに明記し、必要ならrerun_v1。 |
| parameter sweep bestを採用して過学習する | `best_parameter_is_in_sample_only=true` を維持する。 |
| CLIを急いで既存surfaceと混ぜる | CLIはPR-9 optional。まずscript/APIで確認する。 |
| 実データ依存でfresh checkout testが落ちる | real quote testは存在時のみskip解除。 |

---

## 18. コーダーへの実装メモ

- 追加依存は原則禁止。SVGは標準ライブラリ実装を拡張する。
- `polars` を使う。
- `uv` 前提で実行する。
- 大きな汎用化をしない。Trade[XYZ]実データ接続を優先する。
- MT5/CFD用の `swap`, `contract size`, `point`, `digits`, `margin mode` は入れない。
- 実装で迷ったら、`tests/backtest/test_runner_minimal.py` の意味を壊さないことを優先する。
- 成績改善より、artifactの正直さを優先する。

---

## 19. 最終判断

このREV5の範囲では、次を達成する。

```text
Trade[XYZ]実データから quote rows または 1h bar-like frame を作り、
run_backtest()でSP500 long-only breakoutを回し、
signalとfillの時間情報を混同せず、
fill rowの安全条件を守り、
open position end policyを明示し、
artifactと人間向けreportを出せる。
```

これが完了してから、戦略最適化、CLI公開、multi-symbol、short、leverage、L2 replayへ進む。
