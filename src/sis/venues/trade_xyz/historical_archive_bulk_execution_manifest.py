from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["build_bulk_execution_manifest"]


def build_bulk_execution_manifest(
    *,
    generated: datetime,
    plan_path: Path,
    dry_run: bool,
    acknowledge_requester_pays: bool,
    aws_status: dict[str, Any],
    include_l2: bool,
    include_asset_ctxs: bool,
    skip_existing: bool,
    decompress: bool,
    max_objects: int | None,
    candidates: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    skipped_existing: int,
    downloaded: int,
    decompressed: int,
    command_errors: list[dict[str, Any]],
    preflight_status: dict[str, Any],
    blocked_preflight: bool = False,
) -> dict[str, Any]:
    status = (
        "blocked_preflight_failed"
        if blocked_preflight
        else "planned"
        if dry_run
        else "completed_with_errors"
        if command_errors
        else "completed"
    )
    notes = (
        [
            "Bulk execution was blocked before download because AWS preflight did not pass.",
            "Run check-trade-xyz-historical-archive-preflight after configuring AWS credentials.",
        ]
        if blocked_preflight
        else [
            "Bulk execution reads a prebuilt requester-pays plan and never infers extra S3 objects.",
            "Use max_objects to download in small batches before running the full plan.",
            "Downloaded archive data still requires quote normalization before readiness coverage changes.",
        ]
    )
    return {
        "schema_version": "trade_xyz_historical_archive_bulk_execution_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.bulk_execution",
        "plan_path": str(plan_path),
        "dry_run": dry_run,
        "requester_pays_acknowledged": acknowledge_requester_pays,
        "aws_available": aws_status["available"],
        "aws_command_source": aws_status["source"],
        "aws_command_prefix": aws_status["command_prefix"],
        "aws_requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
        "include_l2": include_l2,
        "include_asset_ctxs": include_asset_ctxs,
        "skip_existing": skip_existing,
        "decompress_requested": decompress,
        "max_objects": max_objects,
        "candidate_object_count": len(candidates),
        "selected_object_count": len(selected),
        "skipped_existing_count": skipped_existing,
        "downloaded_object_count": downloaded,
        "decompressed_object_count": decompressed,
        "command_error_count": len(command_errors),
        "command_errors": command_errors,
        "selected_objects": selected,
        "preflight": preflight_status,
        "status": status,
        "notes": notes,
    }
