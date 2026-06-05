<!--
作成日: 2026-05-31_17:20 JST
更新日: 2026-06-05_18:12 JST
-->

# Trade[XYZ] Pure Backtest v0.1

この文書は、現行コードに実装済みの Trade[XYZ] 専用バックテスト基盤を説明します。正本はコードと tests です。

## 結論

Trade[XYZ] pure backtest v0.1 は実装済みです。ただし public CLI はまだありません。現在の入口は Python API の `run_backtest()` です。

```python
from sis.backtest.engine.runner import run_backtest
```

対象コード:

- `src/sis/backtest/engine/config.py`
- `src/sis/backtest/engine/runner.py`
- `src/sis/backtest/trade_xyz/schema.py`
- `src/sis/backtest/trade_xyz/cost_model.py`
- `src/sis/backtest/trade_xyz/gates.py`
- `tests/backtest/`

## Scope

v0.1 で扱うもの:

- Trade[XYZ] only
- pure backtest only
- single-symbol
- long-only
- fixed notional sizing
- market-like taker fill
- next-row fill
- fee / extra slippage / funding v0
- data quality / manifest / metrics / report artifacts

v0.1 で扱わないもの:

- live order
- wallet
- signing
- exchange write
- public CLI
- MT5 / IC Markets / CFD
- short
- multi-symbol portfolio
- limit / stop / partial fill
- L2 order book replay

## Config Contract

`BacktestConfig` は `trade_xyz_backtest_config.v1` です。

主要 fields:

- `run_id`
- `strategy_id`
- `symbol`
- `timeframe`
- `period`
- `initial_cash_usd`
- `position_sizing`
- `execution`
- `cost`
- `gates`
- `leverage`
- `report`

`ExecutionConfig` は現在 `side_mode="long_only"` と `fill_model="market_like_taker_v0"` だけを受けます。

`CostConfig` は `configs/fee_model.trade_xyz.yaml` を既定の fee fallback として使います。`fee_mode=unknown` や fee未解決 row は block 理由になります。

## Input Data

`normalize_trade_xyz_market_data()` は既存 normalized quote に合わせて以下を補完します。

- `ts_client` -> `event_ts`
- `canonical_symbol` -> `symbol`
- `index_price` -> `external_price`
- `bid_price` -> `best_bid`
- `ask_price` -> `best_ask`

必須:

- `event_ts`
- `symbol`
- `is_tradable`
- `block_reasons`

予約列:

- `mark_price`
- `oracle_price`
- `external_price`
- `funding_rate`
- `funding_interval_minutes`
- `open_interest_usd`
- `oi_cap_usage`
- `discovery_bound_pct`
- `bound_distance`
- `session_type`
- `market_status`
- `source_confidence`
- `venue_quality_score`
- `depth_10bps_usd`
- `min_side_depth_10bps_usd`
- `taker_fee_bps`
- `maker_fee_bps`
- `fee_mode`
- `best_bid`
- `best_ask`
- `mid_price`
- `close`
- `spread_bps`
- `exec_buy_price`
- `exec_sell_price`

## Strategy

v0.1 の runner は breakout parameters を使う内蔵シグナルです。

- entry: `close` が過去 `entry_lookback` 本の最大値を上抜く
- exit: `close` が過去 `exit_lookback` 本の最小値を下抜く

シグナル行の価格では約定しません。約定は次の row で行います。最終 row に actionable signal が出た場合は `no_future_fill_row` として block します。

## Fill Model

long entry:

1. `exec_buy_price`
2. `best_ask`
3. `ask_price`
4. `mid_price + spread/2`

long exit:

1. `exec_sell_price`
2. `best_bid`
3. `bid_price`
4. `mid_price - spread/2`

OHLC の high / low を使う fill はありません。

## Gates

entry gate:

- `is_tradable`
- `block_reasons`
- fee resolved
- `market_status == open`
- optional `max_spread_bps`
- optional `min_depth_10bps_usd`
- optional `max_bound_distance`
- optional `max_oi_cap_usage`

exit gate:

- position is open
- exit signal exists
- fee resolved
- market status is `open`, `close_only`, or `unknown_if_fixture`

## Artifacts

`run_backtest()` は `out_dir / run_id` に以下を出します。

- `backtest_run.json`
- `config.json`
- `config_hash.txt`
- `data_manifest.json`
- `input_schema_hash.txt`
- `data_quality.json`
- `orders.parquet`
- `fills.parquet`
- `trades.parquet`
- `blocked_events.parquet`
- `equity_curve.parquet`
- `metrics.json`
- `benchmark_results.json`
- `benchmark_equity_curve.parquet`
- `scenario_results.parquet`
- `scenario_summary.json`
- `split_results.json`
- `parameter_results.parquet`
- `parameter_summary.json`
- `candidate_result.json`
- `backtest_report.md`
- `backtest_report.html`
- `charts/*.svg`
- `charts_data/*.json`

`backtest_run.json` は `no_live_order=true`, `wallet_used=false`, `exchange_write_used=false` を記録します。

## Minimal Usage

現時点では、`tests/backtest/test_runner_minimal.py` が最短の実行例です。実運用用CLIではなく、Python APIから直接呼びます。

```bash
uv run pytest -q tests/backtest/test_runner_minimal.py
```

実データ smoke は `data/normalized/quotes.parquet` がある場合だけ走ります。

```bash
uv run pytest -q tests/backtest/test_real_quotes_smoke.py
```

## Verification

2026-06-05 docs/runtime check:

- `uv run pytest -q tests/backtest`: current expected pass
- `./scripts/check`: canonical full gate
- `uv run python scripts/check_current_docs.py`: checked 83 current docs
- latest recorded `./scripts/check`: 830 passed in 2026-06-04 quote coverage docs
