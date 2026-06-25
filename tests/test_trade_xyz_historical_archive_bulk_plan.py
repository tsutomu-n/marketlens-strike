from __future__ import annotations

from datetime import date

import pytest

from sis.venues.trade_xyz.historical_archive_bulk_plan import (
    build_bulk_plan_items,
    date_range,
    select_bulk_execution_candidates,
)


def test_date_range_includes_boundaries_and_rejects_reversed_range() -> None:
    assert date_range(date(2026, 5, 1), date(2026, 5, 3)) == [
        date(2026, 5, 1),
        date(2026, 5, 2),
        date(2026, 5, 3),
    ]

    with pytest.raises(ValueError, match="end date must be >= start date"):
        date_range(date(2026, 5, 3), date(2026, 5, 1))


def test_build_bulk_plan_items_preserves_counts_order_and_paths(tmp_path) -> None:
    l2_items, asset_ctx_items = build_bulk_plan_items(
        data_dir=tmp_path / "data",
        coins=["xyz:XYZ100", "xyz:SP500"],
        dates=[date(2026, 5, 1), date(2026, 5, 2)],
        hours=[0, 12],
        include_asset_ctxs=True,
    )

    assert len(asset_ctx_items) == 2
    assert len(l2_items) == 8
    assert asset_ctx_items[0]["s3_uri"] == ("s3://hyperliquid-archive/asset_ctxs/20260501.csv.lz4")
    assert asset_ctx_items[0]["decompressed_path"].endswith(
        "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    )
    assert l2_items[0]["coin"] == "xyz:XYZ100"
    assert l2_items[0]["hour"] == 0
    assert l2_items[0]["destination"].endswith(
        "raw/historical_archive/hyperliquid/market_data/20260501/0/l2Book/xyz:XYZ100.lz4"
    )
    assert l2_items[0]["decompressed_path"].endswith(
        "raw/historical_archive/hyperliquid/market_data/20260501/0/l2Book/xyz:XYZ100.jsonl"
    )


def test_select_bulk_execution_candidates_filters_orders_and_limits(tmp_path) -> None:
    existing = tmp_path / "data/raw/historical_archive/existing.lz4"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already-downloaded")
    plan = {
        "asset_ctx_objects": [
            {"destination": str(existing), "download_command": ["aws", "asset-existing"]},
            {
                "destination": str(tmp_path / "data/raw/historical_archive/asset-new.lz4"),
                "download_command": ["aws", "asset-new"],
            },
        ],
        "l2_objects": [
            {
                "destination": str(tmp_path / "data/raw/historical_archive/l2-new.lz4"),
                "download_command": ["aws", "l2-new"],
            }
        ],
    }

    candidates, selected, skipped_existing = select_bulk_execution_candidates(
        plan,
        include_l2=True,
        include_asset_ctxs=True,
        skip_existing=True,
        max_objects=2,
    )

    assert [item["kind"] for item in candidates] == ["asset_ctxs", "asset_ctxs", "l2"]
    assert [item["download_command"] for item in selected] == [
        ["aws", "asset-new"],
        ["aws", "l2-new"],
    ]
    assert skipped_existing == 1
