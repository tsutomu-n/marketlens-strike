from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

from sis.venues.trade_xyz.historical_archive_transfer import (
    HYPERLIQUID_ARCHIVE_BUCKET,
    HistoricalL2ArchiveRequest,
    download_command,
)


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end date must be >= start date")
    values: list[date] = []
    current = start
    while current <= end:
        values.append(current)
        current += timedelta(days=1)
    return values


def build_bulk_plan_items(
    *,
    data_dir: Path,
    coins: list[str],
    dates: list[date],
    hours: list[int],
    include_asset_ctxs: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    l2_items: list[dict[str, Any]] = []
    asset_ctx_items: list[dict[str, Any]] = []
    for current_date in dates:
        date_part = current_date.strftime("%Y%m%d")
        if include_asset_ctxs:
            s3_uri = f"{HYPERLIQUID_ARCHIVE_BUCKET}/asset_ctxs/{date_part}.csv.lz4"
            destination = (
                data_dir / "raw/historical_archive/hyperliquid/asset_ctxs" / f"{date_part}.csv.lz4"
            )
            asset_ctx_items.append(
                {
                    "date": current_date.isoformat(),
                    "s3_uri": s3_uri,
                    "destination": str(destination),
                    "decompressed_path": str(destination.with_suffix("")),
                    "download_command": download_command(s3_uri, destination),
                }
            )
        for hour in hours:
            for coin in coins:
                request = HistoricalL2ArchiveRequest(coin=coin, date=current_date, hour=hour)
                destination = data_dir / request.output_relative_path.with_suffix(".lz4")
                l2_items.append(
                    {
                        "date": current_date.isoformat(),
                        "hour": hour,
                        "coin": coin,
                        "s3_uri": request.s3_uri,
                        "destination": str(destination),
                        "decompressed_path": str(
                            (data_dir / request.output_relative_path).with_suffix(".jsonl")
                        ),
                        "download_command": download_command(request.s3_uri, destination),
                    }
                )
    return l2_items, asset_ctx_items


def select_bulk_execution_candidates(
    plan: dict[str, Any],
    *,
    include_l2: bool,
    include_asset_ctxs: bool,
    skip_existing: bool,
    max_objects: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    candidates: list[dict[str, Any]] = []
    if include_asset_ctxs:
        asset_ctx_objects = plan.get("asset_ctx_objects")
        for item in (
            cast(list[object], asset_ctx_objects) if isinstance(asset_ctx_objects, list) else []
        ):
            if isinstance(item, dict):
                candidates.append({"kind": "asset_ctxs", **cast(dict[str, Any], item)})
    if include_l2:
        l2_objects = plan.get("l2_objects")
        for item in cast(list[object], l2_objects) if isinstance(l2_objects, list) else []:
            if isinstance(item, dict):
                candidates.append({"kind": "l2", **cast(dict[str, Any], item)})

    selected: list[dict[str, Any]] = []
    skipped_existing = 0
    for item in candidates:
        destination = Path(str(item.get("destination") or ""))
        if skip_existing and destination.exists():
            skipped_existing += 1
            continue
        selected.append(item)
        if max_objects is not None and len(selected) >= max_objects:
            break
    return candidates, selected, skipped_existing
