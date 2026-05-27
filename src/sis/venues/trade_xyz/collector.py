from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import append_jsonl, write_json
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.normalizer import quote_from_l2_book
from sis.venues.trade_xyz.registry import mid_candidates


def _ctx_by_symbol(
    meta_payload: dict[str, Any], ctxs: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    universe = meta_payload.get("universe")
    if not isinstance(universe, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(universe):
        if idx >= len(ctxs):
            break
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            result[name.removeprefix("xyz:").upper()] = ctxs[idx]
    return result


def _has_mid(mids: dict[str, str], instrument: InstrumentSpec) -> bool:
    coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
    return bool(mid_candidates(instrument.canonical_symbol, coin) & set(mids.keys()))


def collect_trade_xyz_quotes(
    *,
    instruments: list[InstrumentSpec],
    out_path: Path,
    client: TradeXyzClient | None = None,
    all_mids_payload: dict[str, str] | None = None,
    book_payloads: dict[str, dict[str, Any]] | None = None,
    meta_and_asset_ctxs_payload: tuple[dict[str, Any], list[dict[str, Any]]] | None = None,
    now: datetime | None = None,
) -> int:
    own_client = client is None
    created_client = client or TradeXyzClient()
    ts = now or datetime.now(timezone.utc)
    mids = all_mids_payload if all_mids_payload is not None else created_client.all_mids()
    if meta_and_asset_ctxs_payload is not None:
        meta_ctxs = meta_and_asset_ctxs_payload
    elif book_payloads is not None or not hasattr(created_client, "meta_and_asset_ctxs"):
        meta_ctxs = ({}, [])
    else:
        meta_ctxs = created_client.meta_and_asset_ctxs()
    ctxs_by_symbol = _ctx_by_symbol(meta_ctxs[0], meta_ctxs[1])

    try:
        count = 0
        for instrument in instruments:
            if not instrument.active:
                continue
            coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
            try:
                payload = (
                    book_payloads[coin]
                    if book_payloads is not None and coin in book_payloads
                    else created_client.l2_book(coin)
                )
            except Exception:
                payload = {"levels": [[], []], "error": "BLOCK_API_ERROR"}

            quote = quote_from_l2_book(
                canonical_symbol=instrument.canonical_symbol,
                coin=coin,
                asset_id=instrument.asset_id,
                real_market_symbol=instrument.real_market_symbol,
                payload=payload,
                asset_ctx=ctxs_by_symbol.get(instrument.canonical_symbol.upper()),
                fee_mode=instrument.fee_mode,
                now=ts,
            )
            if not _has_mid(mids, instrument):
                quote = quote.model_copy(
                    update={
                        "is_tradable": False,
                        "block_reasons": list(
                            dict.fromkeys([*quote.block_reasons, "BLOCK_MISSING_ALL_MIDS"])
                        ),
                    }
                )
            append_jsonl(out_path, quote.model_dump(mode="json"))
            count += 1
        return count
    finally:
        if own_client:
            created_client.close()


def collect_and_normalize_trade_xyz_quotes(
    *,
    data_dir: Path,
    instruments: list[InstrumentSpec],
    client: TradeXyzClient | None = None,
    all_mids_payload: dict[str, str] | None = None,
    book_payloads: dict[str, dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> int:
    ts = now or datetime.now(timezone.utc)
    day = ts.date().isoformat()
    out_path = data_dir / f"raw/quotes/trade_xyz/{day}.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=instruments,
        out_path=out_path,
        client=client,
        all_mids_payload=all_mids_payload,
        book_payloads=book_payloads,
        now=ts,
    )
    normalize_quotes(
        data_dir / "raw/quotes",
        data_dir / "normalized/quotes.parquet",
        data_dir / "normalized/sis.duckdb",
    )
    return count


def collect_trade_xyz_quote_window(
    *,
    data_dir: Path,
    instruments: list[InstrumentSpec],
    duration_minutes: int,
    interval_seconds: int,
    normalize: bool,
    replace: bool,
    write_summary: bool,
    write_report: bool,
    output_dir: Path | None = None,
    client: TradeXyzClient | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if duration_minutes <= 0:
        raise ValueError("duration-minutes must be > 0")
    if interval_seconds <= 0:
        raise ValueError("interval-seconds must be > 0")
    if duration_minutes * 60 < interval_seconds:
        raise ValueError("duration-minutes * 60 must be >= interval-seconds")

    started = now or datetime.now(timezone.utc)
    out_root = output_dir or data_dir
    raw_path = out_root / f"raw/quotes/trade_xyz/{started.date().isoformat()}.jsonl"
    if replace and raw_path.exists():
        raw_path.unlink()

    own_client = client is None
    created_client = client or TradeXyzClient()
    rows_written = 0
    api_error_count = 0
    per_symbol: dict[str, dict[str, Any]] = {
        item.canonical_symbol: {
            "row_count": 0,
            "tradable_rows": 0,
            "missing_mark": 0,
            "missing_oracle": 0,
            "missing_funding": 0,
            "missing_open_interest": 0,
            "spreads": [],
            "bid_depths": [],
            "ask_depths": [],
        }
        for item in instruments
    }
    iterations = max(1, int((duration_minutes * 60) / interval_seconds))
    try:
        for idx in range(iterations):
            sample_ts = now or datetime.now(timezone.utc)
            mids_payload = created_client.all_mids()
            meta_ctxs_payload = (
                created_client.meta_and_asset_ctxs()
                if hasattr(created_client, "meta_and_asset_ctxs")
                else ({}, [])
            )
            before = rows_written
            rows_written += collect_trade_xyz_quotes(
                instruments=instruments,
                out_path=raw_path,
                client=created_client,
                all_mids_payload=mids_payload,
                meta_and_asset_ctxs_payload=meta_ctxs_payload,
                now=sample_ts,
            )
            if rows_written == before:
                api_error_count += 1
            if now is None and idx < iterations - 1:
                sleep(interval_seconds)
        ended = datetime.now(timezone.utc) if now is None else started
    finally:
        if own_client:
            created_client.close()

    from sis.storage.jsonl_store import read_jsonl

    observed_ts: list[datetime] = []
    observed_row_count = 0
    for row in read_jsonl(raw_path):
        symbol = row.get("canonical_symbol")
        if isinstance(row.get("ts_client"), str):
            try:
                observed_ts.append(datetime.fromisoformat(str(row["ts_client"])))
            except ValueError:
                pass
        if symbol not in per_symbol:
            continue
        observed_row_count += 1
        entry = per_symbol[str(symbol)]
        entry["row_count"] += 1
        entry["tradable_rows"] += 1 if row.get("is_tradable") is True else 0
        entry["missing_mark"] += 1 if row.get("mark_price") is None else 0
        entry["missing_oracle"] += 1 if row.get("oracle_price") is None else 0
        entry["missing_funding"] += 1 if row.get("funding_rate") is None else 0
        entry["missing_open_interest"] += 1 if row.get("open_interest_usd") is None else 0
        if isinstance(row.get("spread_bps"), (int, float)):
            entry["spreads"].append(float(row["spread_bps"]))
        if isinstance(row.get("bid_depth_10bps_usd"), (int, float)):
            entry["bid_depths"].append(float(row["bid_depth_10bps_usd"]))
        if isinstance(row.get("ask_depth_10bps_usd"), (int, float)):
            entry["ask_depths"].append(float(row["ask_depth_10bps_usd"]))

    def q(values: list[float], pct: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        return ordered[int((len(ordered) - 1) * pct)]

    per_symbol_summary: dict[str, dict[str, Any]] = {}
    for symbol, raw in per_symbol.items():
        n = int(raw["row_count"])
        per_symbol_summary[symbol] = {
            "row_count": n,
            "tradable_rate": (raw["tradable_rows"] / n) if n else 0.0,
            "missing_mark_rate": (raw["missing_mark"] / n) if n else 0.0,
            "missing_oracle_rate": (raw["missing_oracle"] / n) if n else 0.0,
            "missing_funding_rate": (raw["missing_funding"] / n) if n else 0.0,
            "missing_open_interest_rate": (raw["missing_open_interest"] / n) if n else 0.0,
            "spread_bps_p50": q(raw["spreads"], 0.5),
            "spread_bps_p90": q(raw["spreads"], 0.9),
            "bid_depth_10bps_usd_p50": q(raw["bid_depths"], 0.5),
            "ask_depth_10bps_usd_p50": q(raw["ask_depths"], 0.5),
            "funding_present_rate": 1 - ((raw["missing_funding"] / n) if n else 1.0),
        }

    normalized_path = out_root / "normalized/quotes.parquet"
    duckdb_path = out_root / "normalized/sis.duckdb"
    if normalize:
        normalize_quotes(out_root / "raw/quotes", normalized_path, duckdb_path)

    summary = {
        "venue": "trade_xyz",
        "started_at": (min(observed_ts).isoformat() if observed_ts else started.isoformat()),
        "ended_at": (max(observed_ts).isoformat() if observed_ts else ended.isoformat()),
        "duration_minutes": duration_minutes,
        "interval_seconds": interval_seconds,
        "requested_symbols": [item.canonical_symbol for item in instruments],
        "collected_symbols": [
            symbol for symbol, item in per_symbol_summary.items() if item["row_count"] > 0
        ],
        "row_count": observed_row_count,
        "api_error_count": api_error_count,
        "raw_quotes_path": str(raw_path),
        "normalized_quotes_path": str(normalized_path) if normalize else None,
        "duckdb_path": str(duckdb_path) if normalize else None,
        "per_symbol": per_symbol_summary,
    }

    if write_summary:
        write_json(out_root / "ops/trade_xyz_quote_collection_summary.json", summary)
    if write_report:
        report_path = out_root / "reports/trade_xyz_quote_collection_report.md"
        lines = [
            "# Trade[XYZ] Quote Collection Report",
            "",
            "- command: collect-trade-xyz-quotes",
            f"- duration: {duration_minutes} minutes",
            f"- symbols: {', '.join(summary['requested_symbols'])}",
            f"- row_count: {rows_written}",
            f"- API error count: {api_error_count}",
            "",
            "## Per-symbol Health",
            "",
            "| symbol | rows | tradable_rate | missing_mark | missing_oracle | missing_funding | missing_oi | spread_p50 | spread_p90 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for symbol, item in per_symbol_summary.items():
            lines.append(
                f"| {symbol} | {item['row_count']} | {item['tradable_rate']:.4f} | "
                f"{item['missing_mark_rate']:.4f} | {item['missing_oracle_rate']:.4f} | "
                f"{item['missing_funding_rate']:.4f} | {item['missing_open_interest_rate']:.4f} | "
                f"{item['spread_bps_p50']} | {item['spread_bps_p90']} |"
            )
        lines.extend(
            ["", "## Next Action", "", "- Run `uv run sis diagnose-quotes --venue trade_xyz`."]
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        summary["report_path"] = str(report_path)
    return summary
