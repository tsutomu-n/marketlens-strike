from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sis.venues.trade_xyz.historical_archive_normalization import archive_quote_output_path


@dataclass(frozen=True)
class BulkQuoteNormalizationCandidate:
    item: dict[str, Any]
    l2_path: Path
    asset_ctxs_path: Path | None
    output_path: Path
    coin: str | None


def asset_ctx_paths_by_date(plan: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    asset_ctx_objects = plan.get("asset_ctx_objects")
    for item in (
        cast(list[object], asset_ctx_objects) if isinstance(asset_ctx_objects, list) else []
    ):
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        archive_date = str(item.get("date") or "")
        decompressed_path = item.get("decompressed_path")
        if archive_date and isinstance(decompressed_path, str):
            path = Path(decompressed_path)
            if path.exists():
                paths[archive_date] = path
    return paths


def select_bulk_quote_normalization_candidates(
    *,
    data_dir: Path,
    plan: dict[str, Any],
    skip_existing_raw_quotes: bool,
) -> tuple[list[BulkQuoteNormalizationCandidate], dict[str, int]]:
    asset_ctx_by_date = asset_ctx_paths_by_date(plan)
    selected: list[BulkQuoteNormalizationCandidate] = []
    skipped: dict[str, int] = {
        "missing_l2_jsonl": 0,
        "missing_asset_ctxs": 0,
        "raw_quote_output_exists": 0,
    }
    l2_objects = plan.get("l2_objects")
    for item in cast(list[object], l2_objects) if isinstance(l2_objects, list) else []:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        l2_path_value = item.get("decompressed_path")
        if not isinstance(l2_path_value, str):
            skipped["missing_l2_jsonl"] += 1
            continue
        l2_path = Path(l2_path_value)
        if not l2_path.exists():
            skipped["missing_l2_jsonl"] += 1
            continue
        archive_date = str(item.get("date") or "")
        asset_ctxs_path = asset_ctx_by_date.get(archive_date)
        if asset_ctxs_path is None:
            skipped["missing_asset_ctxs"] += 1
        output_path = archive_quote_output_path(data_dir, item)
        if skip_existing_raw_quotes and output_path.exists():
            skipped["raw_quote_output_exists"] += 1
            continue
        selected.append(
            BulkQuoteNormalizationCandidate(
                item=item,
                l2_path=l2_path,
                asset_ctxs_path=asset_ctxs_path,
                output_path=output_path,
                coin=str(item.get("coin") or "") or None,
            )
        )
    return selected, skipped
