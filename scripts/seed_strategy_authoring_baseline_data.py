#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

from sis.settings import get_settings


BASELINE_FEATURE_PATH = "research/strategy_authoring_baseline_feature_panel.parquet"
BASELINE_QUOTES_PATH = "research/strategy_authoring_baseline_quotes.parquet"
BASELINE_COST_PATH = "research/strategy_authoring_baseline_venue_cost_matrix.csv"


def _baseline_times() -> list[datetime]:
    start = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
    return [start + timedelta(hours=4 * index) for index in range(8)]


def _write_feature_panel(data_dir: Path) -> Path:
    out = data_dir / BASELINE_FEATURE_PATH
    rows: list[dict[str, object]] = []
    for index, ts in enumerate(_baseline_times()[:-1]):
        rows.append(
            {
                "ts": ts,
                "canonical_symbol": "QQQ",
                "research_close": 100.0 + index,
                "research_return_4h": 0.010 + index * 0.001,
                "research_return_1d": 0.020 + index * 0.001,
                "research_return_3d": 0.030 + index * 0.001,
                "sma_20": 95.0 + index,
                "sma_50": 90.0 + index,
                "close_above_sma20": True,
                "realized_vol_20": 0.15,
                "dgs10": 4.00,
                "dgs2": 4.50,
                "t10y2y": -0.50,
                "vix_level": 20.0,
                "dxy_proxy": 100.0,
                "is_event_blackout": False,
                "minutes_to_next_event": None,
                "minutes_since_last_event": None,
                "venue": "research_fixture",
                "venue_mark_price": None,
                "venue_index_price": None,
                "venue_spread_bps": None,
                "venue_stale_rate": None,
                "venue_tradable_rate": None,
                "trade_allowed": True,
                "blocked_reason": None,
                "source_confidence": 0.95,
                "venue_quality_score": 0.95,
            }
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(out)
    return out


def _write_quotes(data_dir: Path) -> Path:
    out = data_dir / BASELINE_QUOTES_PATH
    rows: list[dict[str, object]] = []
    for index, ts in enumerate(_baseline_times()):
        price = 30_000.0 + index * 25.0
        rows.append(
            {
                "ts_client": ts.isoformat().replace("+00:00", "Z"),
                "venue": "trade_xyz",
                "canonical_symbol": "XYZ100",
                "venue_symbol": "XYZ100",
                "exec_buy_price": price + 1.0,
                "exec_sell_price": price - 1.0,
                "mark_price": price,
                "mid_price": price,
                "oracle_price": price,
                "index_price": price,
                "spread_bps": 1.0,
                "min_side_depth_10bps_usd": 100_000.0,
                "oracle_ts_ms": int(ts.timestamp() * 1000),
                "market_status": "open",
                "is_tradable": True,
            }
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(out)
    return out


def _write_cost_matrix(data_dir: Path) -> Path:
    out = data_dir / BASELINE_COST_PATH
    rows = [
        {
            "venue": "trade_xyz",
            "symbol": "XYZ100",
            "asset_class": "equity_index",
            "open_fee_bps": 0.0,
            "close_fee_bps": 0.0,
            "spread_p50_bps": 1.0,
            "spread_p90_bps": 1.0,
            "holding_cost_4h_bps": 0.0,
            "holding_cost_24h_bps": 0.0,
            "holding_cost_72h_bps": 0.0,
            "notes": "deterministic Strategy Authoring baseline fixture; not live venue evidence",
        }
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_csv(out)
    return out


def build_baseline_data(data_dir: Path) -> dict[str, Path]:
    return {
        "feature_panel": _write_feature_panel(data_dir),
        "quote_data": _write_quotes(data_dir),
        "cost_matrix": _write_cost_matrix(data_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed deterministic local artifacts for the Strategy Authoring example."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=get_settings().data_dir,
        help="Repository data directory. Defaults to SIS settings data_dir.",
    )
    args = parser.parse_args()

    artifacts = build_baseline_data(args.data_dir)
    for name, path in artifacts.items():
        print(f"{name}_path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
