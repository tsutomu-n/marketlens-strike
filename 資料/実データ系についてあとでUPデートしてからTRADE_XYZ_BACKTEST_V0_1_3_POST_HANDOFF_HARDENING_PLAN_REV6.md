# Trade[XYZ] Pure Backtest v0.1.3 Post-Handoff Hardening Plan REV6

作成日: 2026-05-31
対象 repo: `https://github.com/tsutomu-n/marketlens-strike`
確認対象パッケージ: `trade_xyz_repo_state_handoff_2026-05-31_211743.zip`
確認 branch: `main`
確認 HEAD: `6645688519c72eefedc963b1be1e98d7c05a9221`

## 0. 結論

現状の v0.1 は、テストと実データ smoke は通っている。

確認済み:

- `uv run pytest tests/backtest -q`: `66 passed`
- `./scripts/check`: `662 passed`
- real quote smoke: exit code `0`
- 実データ: `data/normalized/quotes.parquet`, 970 rows
- SP500 rows: 122 rows
- 1h bar smoke output: 4 bars only
- smoke result: orders/fills/trades は 0 件
- smoke result: `insufficient_coverage_for_strategy=true`

したがって、次は戦略最適化ではない。次の目的は、**実データを使った backtest input / fill provenance / report / smoke 判定をさらに信用できる状態にすること**。

最優先の修正は以下。

1. `bar_builder.py` で raw `exec_buy_price` / `exec_sell_price` を合成しない。
2. `fill_price_source` が本当の価格ソースを示すようにする。
3. HTML report に chart を埋め込む。
4. `cumulative_costs` chart/data を fills ベースの累積コストに修正する。
5. docs のテスト件数・ファイル名・branch 前提を現状へ更新する。
6. real-data smoke を「成功」ではなく「smoke only / not strategy usable」と明確に扱う。
7. 実戦略評価にはデータ不足なので、data collection / data adequacy gate を追加する。

## 1. 現状の事実

### 1.1 Git state

```text
branch: main
head: 6645688519c72eefedc963b1be1e98d7c05a9221
status: untracked docs/集めるべき実データ0531-2108/
```

注意:

- 以前の設計資料では `feature/backtest-engine-roadmap` が前提だった。
- 今回の handoff package は `main`。
- コーダーへ渡す次タスクでは `main@6645688519c72eefedc963b1be1e98d7c05a9221` を code-truth とする。
- untracked docs directory は、PR / commit 前に「追加する」か「除外する」かを決める。

### 1.2 Test state

```text
uv run pytest tests/backtest -q
  66 passed

./scripts/check
  662 passed
```

注意:

- `docs/backtest/README.md` と `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md` には古い `54 passed` / `650 passed` の記述が残る。
- docs は現状に更新するか、固定件数を書かず「latest packageでpass」と表現する。

### 1.3 Real data state

`data/normalized/quotes.parquet`:

```text
rows: 970
symbols: 11
SP500 rows: 122
SP500 range: 2026-05-27T02:23:16.768478Z to 2026-05-28T14:45:01.519891Z
close column: missing
mid_price/best_bid/best_ask: no nulls
exec_buy_price/exec_sell_price: Null dtype in current snapshot
block_reasons: List(Null) because all lists are empty in current snapshot
```

1h smoke:

```text
bar_count: 4
required_min_bars: 7 because auto-small-lookback set entry=2 exit=2
insufficient_coverage_for_strategy: true
orders: 0
fills: 0
trades: 0
blocked: no_future_fill_row = 1
```

Interpretation:

- real-data smoke は runtime integration と artifact generation の確認には成功。
- strategy evaluation としては未成立。
- no fills なので fee/fill/accounting の実データ側検証にもまだ弱い。

## 2. Scope

### 2.1 今回 v0.1.3 でやること

- existing v0.1 public Python API を維持する。
- real-data smoke の意味を明確化する。
- bar builder の fill provenance を修正する。
- report / charts を人間が読める最低ラインへ上げる。
- docs と tests を code-truth に合わせる。
- data adequacy gate を追加する。

### 2.2 今回やらないこと

- public CLI `sis backtest-trade-xyz run`
- short
- multi-symbol portfolio
- leverage / liquidation
- maker fill
- limit / stop / post-only
- partial fill
- L2 orderbook replay
- live / paper / wallet / signing / exchange write
- MT5 / IC Markets / CFD
- parameter optimization for strategy selection

## 3. Critical Risks Found

### R1. `bar_builder.py` currently synthesizes `exec_buy_price` and `exec_sell_price`

Current behavior:

- `build_quote_bars()` sets `exec_buy_price = _exec_buy(fill_row)`.
- `_exec_buy()` falls back to `best_ask`, `ask_price`, then `mid + spread/2`.
- Later `resolve_market_like_fill_price()` sees `exec_buy_price` and reports source as `exec_buy_price`.

Problem:

- The fill price may actually come from `best_ask` or `mid + spread/2`, but artifact says `exec_buy_price`.
- This damages `fill_price_source`, which is one of the core evidence fields.
- Current raw normalized quotes have `exec_buy_price` / `exec_sell_price` as Null dtype. Synthesizing them in bar builder hides that fact.

Required fix:

- `bar_builder.py` must not synthesize `exec_buy_price` / `exec_sell_price`.
- It should copy raw `exec_buy_price` / `exec_sell_price` only if they exist on the selected fill snapshot row.
- If raw exec fields are null, leave them null.
- Let `resolve_market_like_fill_price()` choose `fill_best_ask`, `fill_best_bid`, `fill_mid_plus_half_spread`, or `fill_mid_minus_half_spread`.

Expected behavior:

```text
raw exec_buy_price null + best_ask present
  -> Fill.fill_price_source == "fill_best_ask"

raw exec_sell_price null + best_bid present
  -> Fill.fill_price_source == "fill_best_bid"

raw exec fields null + no bid/ask + mid/spread present
  -> Fill.fill_price_source == "fill_mid_plus_half_spread" or "fill_mid_minus_half_spread"
```

### R2. Current real-data smoke has no fills

Problem:

- The smoke output has no orders/fills/trades.
- This is acceptable for artifact smoke, but it does not prove real-data fill/accounting behavior.

Required fix:

- Keep current smoke as `real_quote_artifact_smoke`.
- Add a second fixture-driven or deterministic smoke for at least one round trip.
- Do not manipulate real market data to force strategy evaluation.

Acceptable approaches:

1. Unit fixture round-trip test remains primary.
2. Add `scripts/run_trade_xyz_backtest_smoke.py --timeframe raw_quote_rows --auto-small-lookback` run, but do not require fills.
3. Add a separate `tests/backtest/test_real_quotes_fill_source_smoke.py` that selects real rows and directly validates fill resolution/cost/gate without relying on breakout signals.

### R3. HTML report currently does not embed charts

Current behavior:

- `backtest_report.html` is generated from markdown lines.
- `charts/*.svg` exist separately.
- HTML does not include `<img>` links or embedded chart sections.

Required fix:

- Add chart links or inline `<img src="charts/equity_curve.svg">` sections to report HTML.
- Include at least:
  - equity curve
  - drawdown
  - cumulative costs
  - blocked reasons
  - session breakdown

### R4. `cumulative_costs` chart/data is inconsistent

Current behavior:

- SVG uses per-fill cost values, not cumulative values.
- JSON chart data uses trades-based fees, so open-entry fees may be missing.

Required fix:

- Build cumulative costs from `fills_frame`, not `trades_frame`.
- Include fee + extra slippage + funding delta if present.
- SVG and JSON should use the same source.

### R5. `drawdown` chart data currently stores equity, not drawdown

Current behavior:

- `charts_data/drawdown.json` contains `event_ts` and `equity`.

Required fix:

- Store actual drawdown values:

```json
{"event_ts": "...", "drawdown": -0.0123}
```

### R6. Docs are stale against current test counts and filenames

Current docs mention:

- `54 passed` / `650 passed`
- `tests/backtest/test_real_data_smoke.py`

Current package has:

- `66 passed` / `662 passed`
- `tests/backtest/test_real_quotes_smoke.py`

Required fix:

- Update docs.
- Prefer removing exact pass counts from long-lived docs, or move them to dated status docs.

### R7. Data adequacy is not enough for strategy research

Current smoke has 4 1h bars for SP500. This is not enough.

Required fix:

- Add explicit `evaluation_suitability` output.
- Do not allow `candidate_result.usable_for_strategy_selection=true` unless minimum coverage and minimum completed trade criteria pass.

Suggested default gates:

```text
smoke_ok:
  artifact generation succeeds

analysis_ok:
  evaluation_bar_count >= max(required_min_bars, 50)
  completed_trades >= 1

strategy_candidate_ok:
  evaluation_bar_count >= 200
  completed_trades >= 5
  insufficient_coverage_for_strategy == false
  smoke_only == false
```

These thresholds are deliberately conservative but not final trading requirements.

## 4. Implementation Tasks

## P0. Code-truth and docs hygiene

### Purpose

Prevent implementation against stale assumptions.

### Target files

- `docs/backtest/README.md`
- `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md`
- `README.md`
- optional: `docs/CODE_STATUS.md`
- optional: `docs/CURRENT_STATE.md`

### Changes

1. Replace `54 passed` / `650 passed` with current status or remove exact counts.
2. Fix `test_real_data_smoke.py` to `test_real_quotes_smoke.py`.
3. Record current code-truth:

```text
branch: main
head: 6645688519c72eefedc963b1be1e98d7c05a9221
```

4. Clarify:

```text
real quote smoke currently proves artifact generation only.
It is not strategy evaluation.
```

### Tests

```bash
uv run python scripts/check_current_docs.py
./scripts/check
```

### Completion criteria

- Docs no longer cite stale test counts or wrong filenames.
- Docs say `run_backtest()` Python API remains current entry.
- No docs imply strategy selection is possible from current 970-row smoke.

---

## P1. Fix fill provenance in `bar_builder.py`

### Purpose

Ensure `fill_price_source` in artifacts reflects the actual source used by the fill model.

### Target files

- `src/sis/backtest/trade_xyz/bar_builder.py`
- `tests/backtest/test_trade_xyz_bar_builder.py`
- `tests/backtest/test_fill_model.py`

### Required changes

1. In bar output, do not set synthesized `exec_buy_price` / `exec_sell_price` from `_exec_buy()` / `_exec_sell()`.
2. Preserve raw exec fields only:

```python
"exec_buy_price": fill_row.get("exec_buy_price"),
"exec_sell_price": fill_row.get("exec_sell_price"),
```

3. Keep these fields:

```text
fill_best_bid
fill_best_ask
fill_mid_price
fill_spread_bps
fill_taker_fee_bps
fill_maker_fee_bps
fill_fee_mode
```

4. Let `resolve_market_like_fill_price()` select fallback.

### Tests

Add/modify tests:

```text
test_build_quote_bars_preserves_raw_exec_nulls
test_bar_fill_source_uses_fill_best_ask_when_exec_missing
test_bar_fill_source_uses_fill_mid_plus_half_spread_when_bid_ask_missing
```

Expected assertions:

```text
bar["exec_buy_price"] is null when raw exec_buy_price is null
resolve_market_like_fill_price(bar, side="buy") -> source == "fill_best_ask"
resolve_market_like_fill_price(bar, side="sell") -> source == "fill_best_bid"
```

### Completion criteria

- No synthesized exec price is written by `bar_builder.py`.
- Fill source provenance is correct in bar mode.
- Existing tests pass.

---

## P2. Add execution-quality smoke using real rows without strategy judgment

### Purpose

The current real quote smoke has no fills. Add a smoke that checks real-row fill/cost/gate compatibility without claiming strategy evaluation.

### Target files

- `tests/backtest/test_real_quotes_smoke.py`
- optional: `tests/backtest/test_real_quotes_fill_resolution.py`

### Required behavior

If `data/normalized/quotes.parquet` exists and SP500 rows exist:

1. Prepare rows with `prepare_quote_rows_for_backtest()` or `build_quote_bars()`.
2. Select first row that has executable buy price fallback and fee resolution.
3. Call:

```python
resolve_market_like_fill_price(row, side="buy")
resolve_fee_bps(row, fee_model_path="configs/fee_model.trade_xyz.yaml", fee_scenario="row_resolved")
evaluate_open_fill_gate(...)
```

4. Assert either:

- all resolved and gate allowed, or
- explicit reason why not, such as `fee_unresolved`.

Do not require trades.
Do not mark usable for strategy selection.

### Completion criteria

- Real data test explains fill/cost/gate compatibility.
- Test skips if runtime data is absent.
- Test does not fail fresh checkout.

---

## P3. Add fee scenario option to smoke script

### Purpose

The current real data has some rows with `fee_mode=unknown` or null fee on bar output. For smoke, users need to test both row-resolved and config fallback scenarios.

### Target files

- `scripts/run_trade_xyz_backtest_smoke.py`
- `tests/backtest/test_real_quotes_smoke.py`

### Required changes

Add CLI options:

```text
--fee-scenario row_resolved|standard|growth
--funding-policy disabled_v0|nullable_zero_v0|fixture_hourly_v0
--extra-slippage-bps FLOAT
```

Wire them into `BacktestConfig.cost` and `BacktestConfig.execution`.

### Completion criteria

- Default remains `row_resolved` and `nullable_zero_v0`.
- Script can be run with:

```bash
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --fee-scenario standard \
  --auto-small-lookback
```

- Artifacts record selected fee scenario and funding policy.

---

## P4. Improve report HTML and chart embedding

### Purpose

`backtest_report.html` should be readable by a human without manually browsing chart files.

### Target files

- `src/sis/backtest/engine/report.py`
- `src/sis/backtest/engine/artifacts.py`
- `tests/backtest/test_report_artifacts.py`

### Required changes

1. Add chart path list to `render_backtest_html()` or create a report payload object.
2. Embed chart links:

```html
<img src="charts/equity_curve.svg" alt="Equity Curve">
<img src="charts/drawdown.svg" alt="Drawdown">
<img src="charts/cumulative_costs.svg" alt="Cumulative Costs">
<img src="charts/blocked_reasons.svg" alt="Blocked Reasons">
<img src="charts/session_breakdown.svg" alt="Session Breakdown">
```

3. Keep HTML dependency-free.

### Tests

Assert HTML contains:

```text
charts/equity_curve.svg
charts/drawdown.svg
charts/cumulative_costs.svg
charts/blocked_reasons.svg
```

### Completion criteria

- Opening `backtest_report.html` shows chart references.
- `backtest_report.md` remains plain text usable.

---

## P5. Fix chart data semantics

### Purpose

Make chart SVG and JSON data represent the same quantities.

### Target files

- `src/sis/backtest/engine/artifacts.py`
- `tests/backtest/test_report_artifacts.py`

### Required changes

1. Create helper:

```python
def _cumulative_cost_rows_from_fills(fills_frame: pl.DataFrame) -> list[dict[str, object]]:
    ...
```

2. Use fills for cumulative cost:

```text
fee_amount + extra_slippage_amount + abs(funding_amount_delta if needed)
```

3. Chart SVG `cumulative_costs.svg` must plot cumulative values, not per-fill values.
4. `charts_data/cumulative_costs.json` must use the same cumulative rows.
5. `charts_data/drawdown.json` must include `drawdown`, not raw equity only.

### Tests

Add assertions with two fills:

```text
costs [1.0, 2.0] -> cumulative [1.0, 3.0]
drawdown field exists
```

### Completion criteria

- Chart semantics are consistent.
- JSON names match values.

---

## P6. Add data adequacy policy

### Purpose

Prevent smoke artifacts from being mistaken for strategy evidence.

### Target files

- `src/sis/backtest/engine/data_quality.py`
- `src/sis/backtest/engine/artifacts.py`
- `tests/backtest/test_data_quality.py`
- `tests/backtest/test_artifact_contract.py`

### Required changes

Add to data quality and/or candidate result:

```text
evaluation_suitability:
  smoke_ok
  analysis_ok
  strategy_candidate_ok
```

Suggested logic:

```python
smoke_ok = data_quality.status in {"pass", "warn"}
analysis_ok = evaluation_bar_count >= max(required_min_bars, 50) and trade_count >= 1
strategy_candidate_ok = (
    evaluation_bar_count >= 200
    and trade_count >= 5
    and not insufficient_coverage_for_strategy
    and not smoke_only
)
```

Exact thresholds may be config constants, but defaults must be conservative.

### Completion criteria

- `candidate_result.json` clearly says current smoke is not usable for strategy selection.
- `data_quality.json` explains insufficient coverage.
- Tests cover insufficient and sufficient cases.

---

## P7. Add data collection target note / operator doc

### Purpose

The current dataset is too small. The next useful engineering step requires more continuous data.

### Target files

- `docs/backtest/README.md`
- optional: `docs/backtest/REAL_DATA_READINESS.md`
- optional: `docs/集めるべき実データ0531-2108/README.md` if that untracked folder is intended

### Required content

Document minimum data targets:

```text
smoke:
  any rows that pass schema and artifact generation

analysis candidate:
  at least 50 evaluation bars and at least 1 completed trade

strategy candidate:
  at least 200 evaluation bars and at least 5 completed trades

research candidate:
  multiple days/weeks, several market sessions, enough trades for parameter stability
```

Also state:

```text
Current 2026-05-31 package has only 4 SP500 1h bars after aggregation.
Do not use it to judge strategy edge.
```

### Completion criteria

- Future developer does not mistake 970 quote rows / 4 1h bars for strategy evidence.

---

## P8. Optional: add public CLI only after P1-P7

### Purpose

Avoid exposing a public operator surface before data semantics are fixed.

### Target files if implemented later

- `src/sis/commands/backtest_trade_xyz.py`
- `src/sis/cli.py`
- `tests/test_cli_backtest_trade_xyz.py`

### Rule

Do not implement public CLI until:

- fill provenance fixed
- chart/report fixed
- smoke docs fixed
- data adequacy policy in place

## 5. Stop Conditions

Stop and update the plan if any of these occur:

- `bar_builder.py` continues to synthesize `exec_buy_price` / `exec_sell_price` from fallback prices.
- `fill_price_source` says `exec_buy_price` when raw exec price was null.
- HTML report claims charts but does not link/embed them.
- `candidate_result.usable_for_strategy_selection=true` for current 4-bar smoke.
- Any test starts depending on `data/normalized/quotes.parquet` without skip.
- CLI is exposed before P1-P7 are complete.
- `fee_mode=unknown` can enter without explicit fee scenario fallback.
- Funding is charged per quote row rather than explicit funding event.
- live / paper / wallet / signing / exchange write enters the pure backtest code path.

## 6. Final Completion Criteria

v0.1.3 is complete when:

```text
- tests/backtest pass
- ./scripts/check passes
- bar_builder preserves raw exec nulls
- fill_price_source provenance is correct
- real quote smoke still passes
- smoke candidate_result is not usable for strategy selection
- report HTML embeds charts
- cumulative_costs chart/data are cumulative and fills-based
- drawdown chart_data contains drawdown values
- docs match current branch/head/test names
- current small dataset is documented as insufficient for strategy evaluation
```

## 7. Recommended next command sequence after implementation

```bash
uv run pytest tests/backtest -q
./scripts/check
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --close-source mid_price \
  --event-time-source ts_client \
  --fee-scenario standard \
  --auto-small-lookback \
  --out .tmp/trade_xyz_backtest_smoke
```

Then inspect:

```text
backtest_report.html
candidate_result.json
data_quality.json
data_manifest.json
fills.parquet
blocked_events.parquet
charts_data/cumulative_costs.json
charts_data/drawdown.json
```

