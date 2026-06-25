from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sis.venues.trade_xyz.historical_archive_transfer import (
    HYPERLIQUID_ARCHIVE_BUCKET,
    HistoricalL2ArchiveRequest,
)
from sis.venues.trade_xyz.historical_archive_transfer import (
    aws_download_command_status,
    download_command,
)

HISTORICAL_L2_ARCHIVE_SOURCE = "hyperliquid_archive.market_data.l2Book"
HISTORICAL_ASSET_CTXS_ARCHIVE_SOURCE = "hyperliquid_archive.asset_ctxs"


@dataclass(frozen=True)
class HistoricalArchiveManifestPlan:
    manifest_path: Path
    lz4_path: Path
    decompressed_path: Path
    download_command: list[str]
    manifest: dict[str, Any]


def build_l2_archive_manifest(
    *,
    data_dir: Path,
    request: HistoricalL2ArchiveRequest,
    acknowledge_requester_pays: bool,
    dry_run: bool,
    decompress: bool,
    generated_at: datetime,
) -> HistoricalArchiveManifestPlan:
    relative_output = request.output_relative_path
    lz4_path = data_dir / relative_output.with_suffix(".lz4")
    decompressed_path = data_dir / relative_output.with_suffix(".jsonl")
    manifest_path = data_dir / "manifests/trade_xyz_historical_l2_archive_manifest.json"
    aws_status = aws_download_command_status()
    command = download_command(request.s3_uri, lz4_path)

    return HistoricalArchiveManifestPlan(
        manifest_path=manifest_path,
        lz4_path=lz4_path,
        decompressed_path=decompressed_path,
        download_command=command,
        manifest={
            "schema_version": "trade_xyz_historical_l2_archive_manifest.v1",
            "generated_at": generated_at.isoformat(),
            "source": HISTORICAL_L2_ARCHIVE_SOURCE,
            "s3_uri": request.s3_uri,
            "coin": request.coin,
            "date": request.date.isoformat(),
            "hour": request.hour,
            "requester_pays_acknowledged": acknowledge_requester_pays,
            "dry_run": dry_run,
            "decompress_requested": decompress,
            "aws_available": aws_status["available"],
            "aws_command_source": aws_status["source"],
            "aws_command_prefix": aws_status["command_prefix"],
            "aws_requires_network_for_tool_install": aws_status[
                "requires_network_for_tool_install"
            ],
            "raw_lz4_path": str(lz4_path),
            "decompressed_path": str(decompressed_path) if decompress else None,
            "download_command": command,
            "status": "planned",
            "notes": [
                "Hyperliquid historical l2Book archive is requester-pays S3 data.",
                "Archive uploads are approximately monthly and may be missing or stale.",
                "Raw archive data is not normalized into quote snapshots by this command.",
            ],
        },
    )


def build_asset_ctxs_archive_manifest(
    *,
    data_dir: Path,
    archive_date: date,
    acknowledge_requester_pays: bool,
    dry_run: bool,
    decompress: bool,
    generated_at: datetime,
) -> HistoricalArchiveManifestPlan:
    date_part = archive_date.strftime("%Y%m%d")
    s3_uri = f"{HYPERLIQUID_ARCHIVE_BUCKET}/asset_ctxs/{date_part}.csv.lz4"
    relative_output = Path("raw/historical_archive/hyperliquid/asset_ctxs") / f"{date_part}.csv"
    lz4_path = data_dir / relative_output.with_suffix(".csv.lz4")
    decompressed_path = data_dir / relative_output
    manifest_path = data_dir / "manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json"
    aws_status = aws_download_command_status()
    command = download_command(s3_uri, lz4_path)

    return HistoricalArchiveManifestPlan(
        manifest_path=manifest_path,
        lz4_path=lz4_path,
        decompressed_path=decompressed_path,
        download_command=command,
        manifest={
            "schema_version": "trade_xyz_historical_asset_ctxs_archive_manifest.v1",
            "generated_at": generated_at.isoformat(),
            "source": HISTORICAL_ASSET_CTXS_ARCHIVE_SOURCE,
            "s3_uri": s3_uri,
            "date": archive_date.isoformat(),
            "requester_pays_acknowledged": acknowledge_requester_pays,
            "dry_run": dry_run,
            "decompress_requested": decompress,
            "aws_available": aws_status["available"],
            "aws_command_source": aws_status["source"],
            "aws_command_prefix": aws_status["command_prefix"],
            "aws_requires_network_for_tool_install": aws_status[
                "requires_network_for_tool_install"
            ],
            "raw_lz4_path": str(lz4_path),
            "decompressed_path": str(decompressed_path) if decompress else None,
            "download_command": command,
            "status": "planned",
            "notes": [
                "Hyperliquid historical asset_ctxs archive is requester-pays S3 data.",
                "Archive uploads are approximately monthly and may be missing or stale.",
                "Asset contexts help recover mark/oracle/funding context for historical L2 data.",
            ],
        },
    )
