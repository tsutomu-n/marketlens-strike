from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from sis.models import InstrumentSpec
from sis.research.providers import PriceProvider, ResearchFetchRequest, YahooFinancePriceProvider
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

DEFAULT_REGIME_REFERENCE_SYMBOLS = ["^VIX", "UUP", "USDJPY=X", "EURUSD=X"]


def _active_trade_xyz_instruments(
    registry_path: Path,
    *,
    symbols: list[str] | None,
) -> list[InstrumentSpec]:
    requested = {item.strip().upper() for item in symbols or [] if item.strip()}
    instruments = [
        item
        for item in load_trade_xyz_registry(registry_path)
        if item.venue.value == "trade_xyz" and item.active
    ]
    if requested:
        instruments = [item for item in instruments if item.canonical_symbol.upper() in requested]
    if not instruments:
        raise ValueError("no active Trade[XYZ] instruments found for real-market reference")
    return instruments


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _mapping_rows(instruments: list[InstrumentSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        real_symbol = (item.real_market_symbol or "").strip().upper()
        if not real_symbol:
            continue
        rows.append(
            {
                "real_market_symbol": real_symbol,
                "canonical_symbol": item.canonical_symbol.upper(),
                "venue_symbol": item.venue_symbol,
                "coin": item.coin,
                "asset_class": item.asset_class,
            }
        )
    return rows


def _request_symbols(
    mapping_rows: list[dict[str, Any]],
    *,
    include_regime_symbols: bool,
    extra_symbols: list[str] | None,
) -> list[str]:
    mapped = [str(item["real_market_symbol"]) for item in mapping_rows]
    regime = DEFAULT_REGIME_REFERENCE_SYMBOLS if include_regime_symbols else []
    return _unique_ordered([*mapped, *regime, *(extra_symbols or [])])


def _normalize_reference_frame(
    frame: pl.DataFrame,
    *,
    mapping_rows: list[dict[str, Any]],
    requested_symbols: list[str],
    provider_name: str,
    interval: str,
) -> tuple[pl.DataFrame, dict[str, Any]]:
    if frame.is_empty():
        normalized = pl.DataFrame(
            schema={
                "ts": pl.Datetime(time_zone="UTC"),
                "real_market_symbol": pl.Utf8,
                "canonical_symbol": pl.Utf8,
                "data_role": pl.Utf8,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Float64,
                "provider": pl.Utf8,
                "provider_symbol": pl.Utf8,
                "interval": pl.Utf8,
                "adjustment": pl.Utf8,
            }
        )
    else:
        mapping = (
            pl.DataFrame(mapping_rows)
            if mapping_rows
            else pl.DataFrame(
                schema={
                    "real_market_symbol": pl.Utf8,
                    "canonical_symbol": pl.Utf8,
                    "venue_symbol": pl.Utf8,
                    "coin": pl.Utf8,
                    "asset_class": pl.Utf8,
                }
            )
        )
        source = frame.with_columns(
            pl.col("symbol").cast(pl.Utf8).str.to_uppercase().alias("real_market_symbol"),
            pl.col("ts").cast(pl.Datetime(time_zone="UTC")),
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64),
            pl.col("volume").cast(pl.Float64)
            if "volume" in frame.columns
            else pl.lit(None).cast(pl.Float64).alias("volume"),
            pl.lit(provider_name).alias("provider")
            if "provider" not in frame.columns
            else pl.col("provider").cast(pl.Utf8),
            pl.col("provider_symbol").cast(pl.Utf8)
            if "provider_symbol" in frame.columns
            else pl.col("symbol").cast(pl.Utf8).alias("provider_symbol"),
            pl.lit(interval).alias("interval")
            if "interval" not in frame.columns
            else pl.col("interval").cast(pl.Utf8),
            pl.lit("none").alias("adjustment")
            if "adjustment" not in frame.columns
            else pl.col("adjustment").cast(pl.Utf8),
        )
        normalized = (
            source.join(mapping, on="real_market_symbol", how="left")
            .with_columns(
                pl.when(pl.col("canonical_symbol").is_null())
                .then(pl.lit("regime_reference"))
                .otherwise(pl.lit("underlying_reference"))
                .alias("data_role")
            )
            .select(
                "ts",
                "real_market_symbol",
                "canonical_symbol",
                "data_role",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "provider",
                "provider_symbol",
                "interval",
                "adjustment",
            )
            .sort(["real_market_symbol", "ts"])
        )

    returned_symbols = (
        sorted(str(item).upper() for item in normalized.get_column("real_market_symbol").unique())
        if not normalized.is_empty()
        else []
    )
    mapped_symbols = sorted({str(item["real_market_symbol"]) for item in mapping_rows})
    missing_mapped = sorted(set(mapped_symbols) - set(returned_symbols))
    missing_requested = sorted(set(requested_symbols) - set(returned_symbols))
    per_symbol: dict[str, Any] = {}
    if not normalized.is_empty():
        for symbol, group in normalized.group_by("real_market_symbol", maintain_order=True):
            symbol_value = str(symbol[0] if isinstance(symbol, tuple) else symbol)
            per_symbol[symbol_value] = {
                "row_count": group.height,
                "first_ts": group.get_column("ts").min(),
                "last_ts": group.get_column("ts").max(),
                "canonical_symbols": sorted(
                    {
                        str(item)
                        for item in group.get_column("canonical_symbol").drop_nulls().unique()
                    }
                ),
                "data_roles": sorted(str(item) for item in group.get_column("data_role").unique()),
            }
    summary = {
        "requested_symbols": requested_symbols,
        "returned_symbols": returned_symbols,
        "mapped_symbols": mapped_symbols,
        "missing_mapped_symbols": missing_mapped,
        "missing_requested_symbols": missing_requested,
        "per_symbol": per_symbol,
    }
    return normalized, summary


def collect_trade_xyz_real_market_reference(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    symbols: list[str] | None = None,
    extra_symbols: list[str] | None = None,
    include_regime_symbols: bool = True,
    interval: str = "1d",
    start: date | None = None,
    end: date | None = None,
    period_days: int = 365,
    provider: PriceProvider | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    if period_days <= 0 and (start is None or end is None):
        raise ValueError("period_days must be > 0 when start/end are not both provided")
    generated = generated_at or datetime.now(UTC)
    resolved_registry = registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    instruments = _active_trade_xyz_instruments(resolved_registry, symbols=symbols)
    mappings = _mapping_rows(instruments)
    requested_symbols = _request_symbols(
        mappings,
        include_regime_symbols=include_regime_symbols,
        extra_symbols=extra_symbols,
    )
    if not requested_symbols:
        raise ValueError("no real-market symbols resolved from Trade[XYZ] registry")

    effective_end = end or generated.date() + timedelta(days=1)
    effective_start = start or effective_end - timedelta(days=period_days)
    if effective_start >= effective_end:
        raise ValueError("start must be earlier than end")

    selected_provider = provider or YahooFinancePriceProvider()
    request = ResearchFetchRequest(
        symbols=requested_symbols,
        start=effective_start,
        end=effective_end,
        interval=interval,
    )
    frame = selected_provider.fetch_ohlcv(request)
    normalized, summary = _normalize_reference_frame(
        frame,
        mapping_rows=mappings,
        requested_symbols=requested_symbols,
        provider_name=selected_provider.name,
        interval=interval,
    )

    raw_path = (
        data_dir / f"raw/real_market/{selected_provider.name}/trade_xyz_reference_bars.parquet"
    )
    normalized_path = data_dir / "normalized/real_market_reference_bars.parquet"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_parquet(raw_path)
    normalized.write_parquet(normalized_path)

    row_count = normalized.height
    status = "pass" if row_count > 0 and not summary["missing_mapped_symbols"] else "fail"
    manifest = {
        "schema_version": "trade_xyz_real_market_reference_manifest.v1",
        "generated_at": generated.isoformat(),
        "status": status,
        "data_dir": str(data_dir),
        "registry_path": str(resolved_registry),
        "provider": selected_provider.name,
        "interval": interval,
        "start": effective_start.isoformat(),
        "end": effective_end.isoformat(),
        "period_days": period_days,
        "include_regime_symbols": include_regime_symbols,
        "extra_symbols": _unique_ordered(extra_symbols or []),
        "row_count": row_count,
        "mapped_instrument_count": len(mappings),
        "requested_symbol_count": len(requested_symbols),
        "returned_symbol_count": len(summary["returned_symbols"]),
        "artifacts": {
            "raw_provider_frame": str(raw_path),
            "normalized_reference_bars": str(normalized_path),
        },
        **summary,
        "notes": [
            "This is read-only reference-market data for research/backtest context.",
            "yfinance data is not live-trading grade and must not be treated as execution data.",
            "Trade[XYZ] execution quotes remain the source for fill simulation.",
        ],
    }
    manifest_path = data_dir / "manifests/trade_xyz_real_market_reference_manifest.json"
    write_json(manifest_path, manifest)

    report_path = data_dir / "reports/trade_xyz_real_market_reference.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Trade[XYZ] Real Market Reference",
        "",
        f"- status: {manifest['status']}",
        f"- provider: {manifest['provider']}",
        f"- interval: {manifest['interval']}",
        f"- start: {manifest['start']}",
        f"- end: {manifest['end']}",
        f"- row_count: {manifest['row_count']}",
        f"- missing_mapped_symbols: {','.join(summary['missing_mapped_symbols']) or 'none'}",
        "",
        "## Artifacts",
        "",
        f"- raw_provider_frame: `{raw_path}`",
        f"- normalized_reference_bars: `{normalized_path}`",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest["report_path"] = str(report_path)
    write_json(manifest_path, manifest)
    return manifest
