from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Literal

from sis.backtest.engine.config import (
    BacktestConfig,
    ExecutionConfig,
    GateConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.runner import BreakoutParameters, run_backtest
from sis.backtest.trade_xyz.bar_builder import build_quote_bars
from sis.backtest.trade_xyz.market_data import (
    CloseSource,
    EventTimeSource,
    load_normalized_quotes,
    prepare_quote_rows_for_backtest,
)
from sis.backtest.trade_xyz.ws_ingestion import build_bbo_bars_with_active_asset_state

SmokeTimeframe = Literal["raw_quote_rows", "30m", "1h", "4h", "1d"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local Trade[XYZ] real-data backtest smoke without exposing a public CLI."
    )
    parser.add_argument("--input", default="data/normalized/quotes.parquet")
    parser.add_argument("--funding-events", default="data/normalized/funding_events.parquet")
    parser.add_argument("--symbol", default="SP500")
    parser.add_argument(
        "--timeframe",
        default="1h",
        choices=["raw_quote_rows", "30m", "1h", "4h", "1d"],
    )
    parser.add_argument(
        "--close-source",
        default="mid_price",
        choices=["mid_price", "mark_price", "oracle_price", "index_price"],
    )
    parser.add_argument(
        "--event-time-source",
        default="ts_client",
        choices=["ts_client", "source_ts_ms", "recv_ts_ms"],
    )
    parser.add_argument("--out", default="data/backtests")
    parser.add_argument("--entry-lookback", type=int, default=20)
    parser.add_argument("--exit-lookback", type=int, default=10)
    parser.add_argument("--initial-cash-usd", type=float, default=10_000)
    parser.add_argument("--notional-usd", type=float, default=1_000)
    parser.add_argument("--max-spread-bps", type=float, default=None)
    parser.add_argument("--min-depth-10bps-usd", type=float, default=None)
    parser.add_argument(
        "--end-position-policy",
        default="force_close_if_executable",
        choices=["force_close_if_executable", "mark_to_market_only", "error_if_open"],
    )
    parser.add_argument(
        "--auto-small-lookback",
        action="store_true",
        help="Smoke-only: lower entry/exit lookbacks to 2 when local data is too small.",
    )
    parser.add_argument(
        "--ws-bbo-state",
        action="store_true",
        help="Smoke-only: build bars from WS BBO rows and no-lookahead activeAssetCtx state.",
    )
    return parser


def _frame_for_smoke(
    *,
    input_path: Path,
    symbol: str,
    timeframe: SmokeTimeframe,
    close_source: CloseSource,
    event_time_source: EventTimeSource,
    ws_bbo_state: bool,
):
    raw = load_normalized_quotes(input_path)
    if ws_bbo_state:
        if timeframe == "raw_quote_rows":
            raise ValueError("--ws-bbo-state requires a bar timeframe")
        return build_bbo_bars_with_active_asset_state(
            raw,
            symbol=symbol,
            timeframe=timeframe,  # type: ignore[arg-type]
        )
    if timeframe == "raw_quote_rows":
        return prepare_quote_rows_for_backtest(
            raw,
            symbol=symbol,
            close_source=close_source,
            event_time_source=event_time_source,
        )
    return build_quote_bars(
        raw,
        symbol=symbol,
        timeframe=timeframe,  # type: ignore[arg-type]
        close_source=close_source,
        event_time_source=event_time_source,
    )


def _mark_smoke_artifacts(
    *,
    run_dir: Path,
    auto_small_lookback_used: bool,
    entry_lookback: int,
    exit_lookback: int,
) -> None:
    for name in ("candidate_result.json", "backtest_run.json"):
        path = run_dir / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["smoke_only"] = True
        payload["auto_small_lookback_used"] = auto_small_lookback_used
        payload["usable_for_strategy_selection"] = False
        payload["entry_lookback"] = entry_lookback
        payload["exit_lookback"] = exit_lookback
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parser().parse_args()
    input_path = Path(args.input)
    frame = _frame_for_smoke(
        input_path=input_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        close_source=args.close_source,
        event_time_source=args.event_time_source,
        ws_bbo_state=args.ws_bbo_state,
    )
    if frame.is_empty():
        raise SystemExit(f"no rows for symbol={args.symbol}")
    funding_events_path = Path(args.funding_events) if args.funding_events else None
    funding_events = (
        load_normalized_quotes(funding_events_path)
        if funding_events_path is not None and funding_events_path.exists()
        else None
    )

    entry_lookback = args.entry_lookback
    exit_lookback = args.exit_lookback
    auto_small_lookback_used = False
    if args.auto_small_lookback and frame.height < entry_lookback + exit_lookback + 3:
        entry_lookback = 2
        exit_lookback = 2
        auto_small_lookback_used = True

    first_ts = frame.get_column("event_ts").min()
    last_ts = frame.get_column("event_ts").max()
    if first_ts is None or last_ts is None:
        raise SystemExit("event_ts is empty")

    run_id = (
        f"trade-xyz-smoke-{args.symbol.strip().upper()}-"
        f"{args.timeframe}-{args.close_source}-{args.event_time_source}"
    )
    if args.ws_bbo_state:
        run_id += "-ws_bbo_state"
    config = BacktestConfig(
        run_id=run_id,
        strategy_id="sp500_breakout_v0",
        symbol=args.symbol,
        timeframe=args.timeframe,
        period=PeriodConfig(
            evaluation_start_ts=first_ts,
            evaluation_end_ts=last_ts + timedelta(microseconds=1),
        ),
        initial_cash_usd=args.initial_cash_usd,
        position_sizing=PositionSizingConfig(notional_usd=args.notional_usd),
        execution=ExecutionConfig(end_position_policy=args.end_position_policy),
        gates=GateConfig(
            max_spread_bps=args.max_spread_bps,
            min_depth_10bps_usd=args.min_depth_10bps_usd,
        ),
    )
    result = run_backtest(
        config=config,
        market_data=frame,
        funding_events=funding_events,
        funding_events_ref=str(funding_events_path) if funding_events is not None else None,
        out_dir=Path(args.out),
        input_data_ref=str(input_path),
        breakout=BreakoutParameters(entry_lookback=entry_lookback, exit_lookback=exit_lookback),
    )
    _mark_smoke_artifacts(
        run_dir=result.run_dir,
        auto_small_lookback_used=auto_small_lookback_used,
        entry_lookback=entry_lookback,
        exit_lookback=exit_lookback,
    )
    print(result.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
