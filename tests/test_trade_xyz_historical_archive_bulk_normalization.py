from __future__ import annotations

from sis.venues.trade_xyz.historical_archive_bulk_normalization import (
    asset_ctx_paths_by_date,
)
from sis.venues.trade_xyz.historical_archive_bulk_normalization import (
    select_bulk_quote_normalization_candidates,
)


def test_asset_ctx_paths_by_date_uses_only_existing_decompressed_files(tmp_path) -> None:
    existing = tmp_path / "data/raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    existing.parent.mkdir(parents=True)
    existing.write_text("coin,markPx\nxyz:XYZ100,100\n", encoding="utf-8")
    missing = tmp_path / "data/raw/historical_archive/hyperliquid/asset_ctxs/20260502.csv"
    plan = {
        "asset_ctx_objects": [
            {"date": "2026-05-01", "decompressed_path": str(existing)},
            {"date": "2026-05-02", "decompressed_path": str(missing)},
            {"date": "", "decompressed_path": str(existing)},
            {"date": "2026-05-03", "decompressed_path": 123},
            "invalid",
        ]
    }

    assert asset_ctx_paths_by_date(plan) == {"2026-05-01": existing}


def test_select_bulk_quote_normalization_candidates_counts_skips_and_outputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    l2_existing = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl"
    )
    l2_existing.parent.mkdir(parents=True)
    l2_existing.write_text('{"time":1770000000000,"levels":[[],[]]}\n', encoding="utf-8")
    l2_existing_without_ctx = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260503/9/l2Book/xyz:XYZ100.jsonl"
    )
    l2_existing_without_ctx.parent.mkdir(parents=True)
    l2_existing_without_ctx.write_text(
        '{"time":1770000000000,"levels":[[],[]]}\n', encoding="utf-8"
    )
    l2_output_exists = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260504/9/l2Book/xyz:XYZ100.jsonl"
    )
    l2_output_exists.parent.mkdir(parents=True)
    l2_output_exists.write_text('{"time":1770000000000,"levels":[[],[]]}\n', encoding="utf-8")
    ctx_existing = data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    ctx_existing.parent.mkdir(parents=True)
    ctx_existing.write_text("coin,markPx\nxyz:XYZ100,100\n", encoding="utf-8")
    preexisting_output = (
        data_dir / "raw/quotes/trade_xyz/historical_archive_20260504_9_xyz_XYZ100.jsonl"
    )
    preexisting_output.parent.mkdir(parents=True)
    preexisting_output.write_text("already-normalized\n", encoding="utf-8")
    plan = {
        "asset_ctx_objects": [{"date": "2026-05-01", "decompressed_path": str(ctx_existing)}],
        "l2_objects": [
            {
                "date": "2026-05-01",
                "hour": 9,
                "coin": "xyz:XYZ100",
                "decompressed_path": str(l2_existing),
            },
            {
                "date": "2026-05-02",
                "hour": 9,
                "coin": "xyz:XYZ100",
                "decompressed_path": str(data_dir / "missing.jsonl"),
            },
            {
                "date": "2026-05-03",
                "hour": 9,
                "coin": "xyz:XYZ100",
                "decompressed_path": str(l2_existing_without_ctx),
            },
            {
                "date": "2026-05-04",
                "hour": 9,
                "coin": "xyz:XYZ100",
                "decompressed_path": str(l2_output_exists),
            },
            {"date": "2026-05-05", "hour": 9, "coin": "xyz:XYZ100"},
            "invalid",
        ],
    }

    selected, skipped = select_bulk_quote_normalization_candidates(
        data_dir=data_dir,
        plan=plan,
        skip_existing_raw_quotes=True,
    )

    assert skipped == {
        "missing_l2_jsonl": 2,
        "missing_asset_ctxs": 2,
        "raw_quote_output_exists": 1,
    }
    assert len(selected) == 2
    assert selected[0].l2_path == l2_existing
    assert selected[0].asset_ctxs_path == ctx_existing
    assert selected[0].coin == "xyz:XYZ100"
    assert selected[0].output_path == (
        data_dir / "raw/quotes/trade_xyz/historical_archive_20260501_9_xyz_XYZ100.jsonl"
    )
    assert selected[1].l2_path == l2_existing_without_ctx
    assert selected[1].asset_ctxs_path is None
    assert selected[1].output_path == (
        data_dir / "raw/quotes/trade_xyz/historical_archive_20260503_9_xyz_XYZ100.jsonl"
    )


def test_select_bulk_quote_normalization_candidates_can_include_existing_outputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    l2_path = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl"
    )
    l2_path.parent.mkdir(parents=True)
    l2_path.write_text('{"time":1770000000000,"levels":[[],[]]}\n', encoding="utf-8")
    output_path = data_dir / "raw/quotes/trade_xyz/historical_archive_20260501_9_xyz_XYZ100.jsonl"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("already-normalized\n", encoding="utf-8")

    selected, skipped = select_bulk_quote_normalization_candidates(
        data_dir=data_dir,
        plan={
            "l2_objects": [
                {
                    "date": "2026-05-01",
                    "hour": 9,
                    "coin": "xyz:XYZ100",
                    "decompressed_path": str(l2_path),
                }
            ]
        },
        skip_existing_raw_quotes=False,
    )

    assert len(selected) == 1
    assert selected[0].output_path == output_path
    assert skipped["raw_quote_output_exists"] == 0
