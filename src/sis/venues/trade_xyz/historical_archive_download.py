from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.historical_archive_manifest import HistoricalArchiveManifestPlan


def execute_archive_manifest_plan(
    *,
    data_dir: Path,
    plan: HistoricalArchiveManifestPlan,
    acknowledge_requester_pays: bool,
    dry_run: bool,
    decompress: bool,
    aws_status: dict[str, Any],
    requester_pays_error: str,
    command_runner: Callable[[list[str]], None],
    decompress_lz4_fn: Callable[[Path, Path], None],
    preflight_status_fn: Callable[[Path], dict[str, Any]],
    preflight_error_fn: Callable[[dict[str, Any]], str | None],
) -> dict[str, Any]:
    manifest = plan.manifest
    if dry_run:
        write_json(plan.manifest_path, manifest)
        return manifest
    if not acknowledge_requester_pays:
        manifest["status"] = "blocked_requires_requester_pays_ack"
        write_json(plan.manifest_path, manifest)
        raise ValueError(requester_pays_error)
    if not aws_status["available"]:
        manifest["status"] = "blocked_missing_aws_command"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    preflight_status = preflight_status_fn(data_dir)
    manifest["preflight"] = preflight_status
    if preflight_error := preflight_error_fn(preflight_status):
        manifest["status"] = "blocked_preflight_failed"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(preflight_error)

    plan.lz4_path.parent.mkdir(parents=True, exist_ok=True)
    command_runner(plan.download_command)
    manifest["status"] = "downloaded"
    manifest["raw_lz4_bytes"] = plan.lz4_path.stat().st_size if plan.lz4_path.exists() else None
    if decompress:
        decompress_lz4_fn(plan.lz4_path, plan.decompressed_path)
        manifest["status"] = "downloaded_and_decompressed"
        manifest["decompressed_bytes"] = (
            plan.decompressed_path.stat().st_size if plan.decompressed_path.exists() else None
        )
    write_json(plan.manifest_path, manifest)
    return manifest
