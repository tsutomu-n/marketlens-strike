from __future__ import annotations

from datetime import UTC, date, datetime

from sis.venues.trade_xyz.historical_archive_manifest import (
    build_asset_ctxs_archive_manifest,
)
from sis.venues.trade_xyz.historical_archive_manifest import build_l2_archive_manifest
from sis.venues.trade_xyz.historical_archive_transfer import HistoricalL2ArchiveRequest


def test_build_l2_archive_manifest_preserves_requester_pays_paths_and_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "aws --profile fixture")
    data_dir = tmp_path / "data"

    plan = build_l2_archive_manifest(
        data_dir=data_dir,
        request=HistoricalL2ArchiveRequest(
            coin="xyz:XYZ100",
            date=date(2026, 5, 1),
            hour=9,
        ),
        acknowledge_requester_pays=False,
        dry_run=True,
        decompress=True,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert (
        plan.manifest_path == data_dir / "manifests/trade_xyz_historical_l2_archive_manifest.json"
    )
    assert plan.lz4_path == (
        data_dir / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.lz4"
    )
    assert plan.decompressed_path == (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl"
    )
    assert plan.manifest["schema_version"] == "trade_xyz_historical_l2_archive_manifest.v1"
    assert plan.manifest["generated_at"] == "2026-05-31T00:00:00+00:00"
    assert plan.manifest["source"] == "hyperliquid_archive.market_data.l2Book"
    assert plan.manifest["s3_uri"] == (
        "s3://hyperliquid-archive/market_data/20260501/9/l2Book/xyz:XYZ100.lz4"
    )
    assert plan.manifest["requester_pays_acknowledged"] is False
    assert plan.manifest["dry_run"] is True
    assert plan.manifest["decompress_requested"] is True
    assert plan.manifest["aws_command_source"] == "SIS_AWS_COMMAND"
    assert plan.manifest["download_command"][:3] == ["aws", "--profile", "fixture"]
    assert plan.manifest["download_command"][-2:] == ["--request-payer", "requester"]
    assert plan.manifest["status"] == "planned"


def test_build_asset_ctxs_archive_manifest_preserves_requester_pays_paths_and_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SIS_AWS_COMMAND", "aws --profile fixture")
    data_dir = tmp_path / "data"

    plan = build_asset_ctxs_archive_manifest(
        data_dir=data_dir,
        archive_date=date(2026, 5, 1),
        acknowledge_requester_pays=True,
        dry_run=False,
        decompress=False,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert plan.manifest_path == (
        data_dir / "manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json"
    )
    assert (
        plan.lz4_path == data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv.lz4"
    )
    assert (
        plan.decompressed_path
        == data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    )
    assert plan.manifest["schema_version"] == "trade_xyz_historical_asset_ctxs_archive_manifest.v1"
    assert plan.manifest["generated_at"] == "2026-05-31T00:00:00+00:00"
    assert plan.manifest["source"] == "hyperliquid_archive.asset_ctxs"
    assert plan.manifest["s3_uri"] == "s3://hyperliquid-archive/asset_ctxs/20260501.csv.lz4"
    assert plan.manifest["date"] == "2026-05-01"
    assert plan.manifest["requester_pays_acknowledged"] is True
    assert plan.manifest["dry_run"] is False
    assert plan.manifest["decompress_requested"] is False
    assert plan.manifest["decompressed_path"] is None
    assert plan.manifest["aws_command_source"] == "SIS_AWS_COMMAND"
    assert plan.manifest["download_command"][:3] == ["aws", "--profile", "fixture"]
    assert plan.manifest["download_command"][-2:] == ["--request-payer", "requester"]
    assert plan.manifest["status"] == "planned"
