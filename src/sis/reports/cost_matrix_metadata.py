from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import polars as pl

from sis.storage.jsonl_store import read_json, read_jsonl


BASE_ROWS: list[dict[str, Any]] = [
    {
        "venue": "gtrade",
        "symbol": "SPY",
        "asset_class": "index",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "spreadP requires live probe",
    },
    {
        "venue": "gtrade",
        "symbol": "QQQ",
        "asset_class": "index",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "spreadP requires live probe",
    },
    {
        "venue": "gtrade",
        "symbol": "XAU",
        "asset_class": "commodity",
        "open_fee_bps": 5,
        "close_fee_bps": 5,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "fixed spread 1 bps; holding/borrowing requires live probe",
    },
    {
        "venue": "ostium",
        "symbol": "SPX_EQUIV",
        "asset_class": "index",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
    {
        "venue": "ostium",
        "symbol": "NDX_EQUIV",
        "asset_class": "index",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
    {
        "venue": "ostium",
        "symbol": "XAU",
        "asset_class": "commodity",
        "open_fee_bps": None,
        "close_fee_bps": None,
        "spread_p50_bps": None,
        "spread_p90_bps": None,
        "spread_p99_bps": None,
        "holding_cost_4h_bps": None,
        "holding_cost_24h_bps": None,
        "holding_cost_72h_bps": None,
        "stale_rate": None,
        "tradable_rate": None,
        "notes": "requires probe",
    },
]


def base_frame() -> pl.DataFrame:
    return pl.from_dicts([dict(row) for row in BASE_ROWS], infer_schema_length=None)


def latest_gtrade_sidecar(sidecar_root: Path | None) -> Path | None:
    if sidecar_root is None or not sidecar_root.exists():
        return None
    files = sorted(sidecar_root.glob("*.jsonl"))
    return files[-1] if files else None


def as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def as_bps_from_gtrade_fee(value: object) -> float | None:
    raw = as_float(value)
    if raw is None:
        return None
    return raw / 1e8


def worst_abs_ostium_rollover_bps(
    long_rate: object, short_rate: object, hours: float
) -> float | None:
    rates: list[float] = []
    for value in (long_rate, short_rate):
        parsed = as_float(value)
        if parsed is None:
            continue
        rates.append(abs(parsed))
    if not rates:
        return None
    # Ostium Builder SDK exposes rolloverRate as 8hr percent by side.
    return max(rates) * 100 * (hours / 8)


def gtrade_holding_bps(
    pair: dict[str, Any], snapshot: dict[str, Any], hours: float
) -> float | None:
    pair_index = pair.get("pair_index")
    if pair_index is None:
        return None
    seconds = hours * 60 * 60
    candidates: list[float] = []

    def indexed(value: object, index: int) -> object | None:
        if isinstance(value, list) and index < len(value):
            return value[index]
        if isinstance(value, dict):
            value_by_key = cast(dict[object, object], value)
            return value_by_key.get(str(index)) or value_by_key.get(index)
        return None

    for collateral in snapshot.get("raw", {}).get("collaterals", []):
        if not isinstance(collateral, dict) or collateral.get("isActive") is not True:
            continue
        borrowing_rate_raw = collateral.get("borrowingFees", {}).get("v2", {}).get("pairParams", [])
        funding_data = collateral.get("fundingFees", {}).get("pairData", [])
        funding_params = collateral.get("fundingFees", {}).get("pairParams", [])
        index = int(pair_index)
        borrow_item = indexed(borrowing_rate_raw, index)
        funding_item = indexed(funding_data, index)
        funding_param = indexed(funding_params, index)

        borrow_bps = 0.0
        if isinstance(borrow_item, dict):
            borrow_item_dict = cast(dict[str, Any], borrow_item)
            raw_rate = as_float(borrow_item_dict.get("borrowingRatePerSecondP"))
            if raw_rate is not None:
                # SDK borrowing v2 precision: raw / 1e10 is percentage per second.
                borrow_bps = raw_rate / 1e10 * seconds * 100

        funding_bps = 0.0
        if (
            isinstance(funding_item, dict)
            and isinstance(funding_param, dict)
            and cast(dict[str, Any], funding_param).get("fundingFeesEnabled") is True
        ):
            funding_item_dict = cast(dict[str, Any], funding_item)
            funding_rate = as_float(funding_item_dict.get("lastFundingRatePerSecondP"))
            if funding_rate is not None:
                # SDK funding precision: raw / 1e18 is fractional rate per second.
                funding_bps = abs(funding_rate / 1e18) * seconds * 10_000

        candidates.append(borrow_bps + funding_bps)

    return max(candidates) if candidates else None


def metadata_rows(
    *,
    gtrade_sidecar_root: Path | None = None,
    ostium_registry_path: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [dict(row) for row in BASE_ROWS]
    by_key = {(row["venue"], row["symbol"]): row for row in rows}

    sidecar_path = latest_gtrade_sidecar(gtrade_sidecar_root)
    if sidecar_path is not None:
        snapshots = list(read_jsonl(sidecar_path))
        if snapshots:
            snapshot = cast(dict[str, Any], snapshots[-1])
            for pair in snapshot.get("pairs", []):
                if not isinstance(pair, dict):
                    continue
                pair = cast(dict[str, Any], pair)
                symbol = pair.get("canonical_symbol")
                row = by_key.get(("gtrade", symbol))
                if row is None:
                    continue
                spread_bps = pair.get("spread_bps")
                if isinstance(spread_bps, int | float):
                    row["spread_p50_bps"] = float(spread_bps)
                    row["spread_p90_bps"] = float(spread_bps)
                    row["spread_p99_bps"] = float(spread_bps)
                fee_bps = as_bps_from_gtrade_fee(pair.get("total_position_size_fee_p"))
                if fee_bps is not None:
                    row["open_fee_bps"] = fee_bps
                    row["close_fee_bps"] = fee_bps
                row["holding_cost_4h_bps"] = gtrade_holding_bps(pair, snapshot, 4)
                row["holding_cost_24h_bps"] = gtrade_holding_bps(pair, snapshot, 24)
                row["holding_cost_72h_bps"] = gtrade_holding_bps(pair, snapshot, 72)
                row["notes"] = (
                    f"gTrade sidecar={sidecar_path}; fee_index={pair.get('fee_index')}; "
                    "holding cost uses max active collateral borrowing/funding rate from trading-variables"
                )

    if ostium_registry_path is not None and ostium_registry_path.exists():
        registry = read_json(ostium_registry_path)
        if isinstance(registry, list):
            for item in registry:
                if not isinstance(item, dict):
                    continue
                item = cast(dict[str, Any], item)
                if item.get("venue") != "ostium":
                    continue
                row = by_key.get(("ostium", item.get("canonical_symbol")))
                if row is None:
                    continue
                opening_fee = item.get("opening_fee_bps")
                if isinstance(opening_fee, int | float):
                    row["open_fee_bps"] = float(opening_fee)
                row["holding_cost_4h_bps"] = worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    4,
                )
                row["holding_cost_24h_bps"] = worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    24,
                )
                row["holding_cost_72h_bps"] = worst_abs_ostium_rollover_bps(
                    item.get("rollover_rate_long"),
                    item.get("rollover_rate_short"),
                    72,
                )
                row["notes"] = (
                    f"ostium registry={ostium_registry_path}; "
                    f"rollover_fee_per_block={item.get('rollover_fee_per_block')}; "
                    f"rollover_rate_long={item.get('rollover_rate_long')}; "
                    f"rollover_rate_short={item.get('rollover_rate_short')}; "
                    "holding cost uses conservative max(abs(long), abs(short)) 8hr percent conversion"
                )

    return rows
