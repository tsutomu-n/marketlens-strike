from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import shutil
import subprocess
from typing import Any, cast

from sis.storage.jsonl_store import append_jsonl
from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz import historical_archive_normalization
from sis.venues.trade_xyz.historical_archive_bulk_normalization import (
    select_bulk_quote_normalization_candidates,
)
from sis.venues.trade_xyz.historical_archive_bulk_execution_manifest import (
    build_bulk_execution_manifest,
)
from sis.venues.trade_xyz.historical_archive_manifest import (
    build_asset_ctxs_archive_manifest,
)
from sis.venues.trade_xyz.historical_archive_manifest import build_l2_archive_manifest
from sis.venues.trade_xyz.historical_archive_quote_rows import (
    HISTORICAL_QUOTE_SOURCE,
    build_historical_archive_quote_row,
)
from sis.venues.trade_xyz.historical_archive_transfer import (
    CommandRunner,
    HistoricalL2ArchiveRequest,
    PreflightRunner,
)
from sis.venues.trade_xyz.historical_archive_transfer import (
    aws_download_command_status,
    decompress_lz4,
    historical_archive_preflight_error,
    historical_archive_preflight_status,
    run_command,
)
from sis.venues.trade_xyz.historical_archive_bulk_plan import (
    build_bulk_plan_items,
    date_range,
    select_bulk_execution_candidates,
)
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

HISTORICAL_L2_ARCHIVE_SOURCE = "hyperliquid_archive.market_data.l2Book"
HISTORICAL_ASSET_CTXS_ARCHIVE_SOURCE = "hyperliquid_archive.asset_ctxs"

_normalize_symbol = historical_archive_normalization.normalize_symbol
_load_l2_rows = historical_archive_normalization.load_l2_rows
_coerce_asset_ctx_value = historical_archive_normalization.coerce_asset_ctx_value
_load_asset_ctxs = historical_archive_normalization.load_asset_ctxs
_resolve_instrument = historical_archive_normalization.resolve_instrument
_run_command = run_command
_historical_archive_preflight_status = historical_archive_preflight_status
_historical_archive_preflight_error = historical_archive_preflight_error
_decompress_lz4 = decompress_lz4


def check_hyperliquid_historical_archive_preflight(
    *,
    data_dir: Path,
    command_runner: PreflightRunner | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    aws_status = aws_download_command_status()
    command = [*aws_status["command_prefix"], "sts", "get-caller-identity"]
    if not aws_status["available"]:
        return_code = 127
        stdout = ""
        stderr = "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
    elif command_runner is not None:
        return_code, stdout, stderr = command_runner(command)
    else:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    manifest = {
        "schema_version": "trade_xyz_historical_archive_preflight_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.preflight",
        "data_dir": str(data_dir),
        "aws_available": aws_status["available"],
        "aws_command_source": aws_status["source"],
        "aws_command_prefix": aws_status["command_prefix"],
        "aws_requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
        "preflight_command": command,
        "return_code": return_code,
        "status": "pass" if return_code == 0 else "fail",
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "notes": [
            "This preflight checks AWS identity before requester-pays archive download.",
            "It does not download historical archive objects.",
        ],
    }
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json",
        manifest,
    )
    return manifest


def collect_hyperliquid_historical_l2_archive(
    *,
    data_dir: Path,
    request: HistoricalL2ArchiveRequest,
    acknowledge_requester_pays: bool = False,
    decompress: bool = True,
    dry_run: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    aws_status = aws_download_command_status()
    plan = build_l2_archive_manifest(
        data_dir=data_dir,
        request=request,
        acknowledge_requester_pays=acknowledge_requester_pays,
        dry_run=dry_run,
        decompress=decompress,
        generated_at=generated,
    )
    manifest = plan.manifest

    if dry_run:
        write_json(plan.manifest_path, manifest)
        return manifest
    if not acknowledge_requester_pays:
        manifest["status"] = "blocked_requires_requester_pays_ack"
        write_json(plan.manifest_path, manifest)
        raise ValueError(
            "historical L2 archive is requester-pays; pass --acknowledge-requester-pays to download"
        )
    if not aws_status["available"]:
        manifest["status"] = "blocked_missing_aws_command"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    preflight_status = _historical_archive_preflight_status(data_dir)
    manifest["preflight"] = preflight_status
    if preflight_error := _historical_archive_preflight_error(preflight_status):
        manifest["status"] = "blocked_preflight_failed"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(preflight_error)

    plan.lz4_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command(plan.download_command)
    manifest["status"] = "downloaded"
    manifest["raw_lz4_bytes"] = plan.lz4_path.stat().st_size if plan.lz4_path.exists() else None
    if decompress:
        _decompress_lz4(plan.lz4_path, plan.decompressed_path)
        manifest["status"] = "downloaded_and_decompressed"
        manifest["decompressed_bytes"] = (
            plan.decompressed_path.stat().st_size if plan.decompressed_path.exists() else None
        )
    write_json(plan.manifest_path, manifest)
    return manifest


def collect_hyperliquid_historical_asset_ctxs_archive(
    *,
    data_dir: Path,
    archive_date: date,
    acknowledge_requester_pays: bool = False,
    decompress: bool = True,
    dry_run: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    aws_status = aws_download_command_status()
    plan = build_asset_ctxs_archive_manifest(
        data_dir=data_dir,
        archive_date=archive_date,
        acknowledge_requester_pays=acknowledge_requester_pays,
        dry_run=dry_run,
        decompress=decompress,
        generated_at=generated,
    )
    manifest = plan.manifest
    if dry_run:
        write_json(plan.manifest_path, manifest)
        return manifest
    if not acknowledge_requester_pays:
        manifest["status"] = "blocked_requires_requester_pays_ack"
        write_json(plan.manifest_path, manifest)
        raise ValueError(
            "historical asset_ctxs archive is requester-pays; pass "
            "--acknowledge-requester-pays to download"
        )
    if not aws_status["available"]:
        manifest["status"] = "blocked_missing_aws_command"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    preflight_status = _historical_archive_preflight_status(data_dir)
    manifest["preflight"] = preflight_status
    if preflight_error := _historical_archive_preflight_error(preflight_status):
        manifest["status"] = "blocked_preflight_failed"
        write_json(plan.manifest_path, manifest)
        raise RuntimeError(preflight_error)

    plan.lz4_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command(plan.download_command)
    manifest["status"] = "downloaded"
    manifest["raw_lz4_bytes"] = plan.lz4_path.stat().st_size if plan.lz4_path.exists() else None
    if decompress:
        _decompress_lz4(plan.lz4_path, plan.decompressed_path)
        manifest["status"] = "downloaded_and_decompressed"
        manifest["decompressed_bytes"] = (
            plan.decompressed_path.stat().st_size if plan.decompressed_path.exists() else None
        )
    write_json(plan.manifest_path, manifest)
    return manifest


def build_hyperliquid_historical_archive_bulk_plan(
    *,
    data_dir: Path,
    coins: list[str],
    start_date: date,
    end_date: date,
    hours: list[int] | None = None,
    include_asset_ctxs: bool = True,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    if not coins:
        raise ValueError("at least one coin is required")
    effective_hours = sorted(hours if hours is not None else list(range(24)))
    invalid_hours = [hour for hour in effective_hours if hour < 0 or hour > 23]
    if invalid_hours:
        raise ValueError(f"hours must be between 0 and 23: {invalid_hours}")
    generated = generated_at or datetime.now(UTC)
    dates = date_range(start_date, end_date)
    l2_items, asset_ctx_items = build_bulk_plan_items(
        data_dir=data_dir,
        coins=coins,
        dates=dates,
        hours=effective_hours,
        include_asset_ctxs=include_asset_ctxs,
    )

    manifest = {
        "schema_version": "trade_xyz_historical_archive_bulk_plan_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.bulk_plan",
        "data_dir": str(data_dir),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "date_count": len(dates),
        "coins": coins,
        "hours": effective_hours,
        "include_asset_ctxs": include_asset_ctxs,
        "requester_pays_ack_required": True,
        "estimated_l2_object_count": len(l2_items),
        "estimated_asset_ctx_object_count": len(asset_ctx_items),
        "estimated_total_object_count": len(l2_items) + len(asset_ctx_items),
        "l2_objects": l2_items,
        "asset_ctx_objects": asset_ctx_items,
        "notes": [
            "This is a dry-run bulk plan for requester-pays Hyperliquid S3 archive data.",
            "Execute commands only after accepting transfer cost and installing/configuring aws CLI.",
            "Downloaded archive data still requires normalization before it contributes to quote coverage.",
        ],
    }
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json", manifest
    )
    return manifest


def execute_hyperliquid_historical_archive_bulk_plan(
    *,
    data_dir: Path,
    plan_path: Path | None = None,
    acknowledge_requester_pays: bool = False,
    dry_run: bool = True,
    max_objects: int | None = None,
    include_l2: bool = True,
    include_asset_ctxs: bool = True,
    skip_existing: bool = True,
    decompress: bool = True,
    command_runner: CommandRunner | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_plan_path = (
        plan_path or data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json"
    )
    if not effective_plan_path.exists():
        raise FileNotFoundError(f"historical archive bulk plan not found: {effective_plan_path}")
    plan = read_json(effective_plan_path)
    if not isinstance(plan, dict):
        raise ValueError(f"historical archive bulk plan is not an object: {effective_plan_path}")
    plan = cast(dict[str, Any], plan)
    if not dry_run and not acknowledge_requester_pays:
        raise ValueError(
            "historical archive bulk execution is requester-pays; pass "
            "--acknowledge-requester-pays to execute"
        )
    aws_status = aws_download_command_status()
    if not dry_run and command_runner is None and not aws_status["available"]:
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    if decompress and not dry_run and shutil.which("lz4") is None:
        raise RuntimeError(
            "lz4 executable not found; install lz4 before decompressing archive data"
        )

    candidates, selected, skipped_existing = select_bulk_execution_candidates(
        plan,
        include_l2=include_l2,
        include_asset_ctxs=include_asset_ctxs,
        skip_existing=skip_existing,
        max_objects=max_objects,
    )

    preflight_status = _historical_archive_preflight_status(data_dir)
    preflight_error = (
        None
        if dry_run or command_runner is not None
        else _historical_archive_preflight_error(preflight_status)
    )
    if preflight_error is not None:
        generated = generated_at or datetime.now(UTC)
        manifest = build_bulk_execution_manifest(
            generated=generated,
            plan_path=effective_plan_path,
            dry_run=dry_run,
            acknowledge_requester_pays=acknowledge_requester_pays,
            aws_status=aws_status,
            include_l2=include_l2,
            include_asset_ctxs=include_asset_ctxs,
            skip_existing=skip_existing,
            decompress=decompress,
            max_objects=max_objects,
            candidates=candidates,
            selected=selected,
            skipped_existing=skipped_existing,
            downloaded=0,
            decompressed=0,
            command_errors=[],
            preflight_status=preflight_status,
            blocked_preflight=True,
        )
        write_json(
            data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json",
            manifest,
        )
        raise RuntimeError(preflight_error)

    runner = command_runner or _run_command
    downloaded = 0
    decompressed = 0
    command_errors: list[dict[str, Any]] = []
    for item in selected:
        command = item.get("download_command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            command_errors.append({"item": item, "error": "invalid_download_command"})
            continue
        destination = Path(str(item["destination"]))
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            try:
                runner(command)
                downloaded += 1
                decompressed_path = item.get("decompressed_path")
                if decompress and isinstance(decompressed_path, str):
                    _decompress_lz4(destination, Path(decompressed_path))
                    decompressed += 1
            except RuntimeError as exc:
                command_errors.append({"item": item, "error": str(exc)})
                break

    generated = generated_at or datetime.now(UTC)
    manifest = build_bulk_execution_manifest(
        generated=generated,
        plan_path=effective_plan_path,
        dry_run=dry_run,
        acknowledge_requester_pays=acknowledge_requester_pays,
        aws_status=aws_status,
        include_l2=include_l2,
        include_asset_ctxs=include_asset_ctxs,
        skip_existing=skip_existing,
        decompress=decompress,
        max_objects=max_objects,
        candidates=candidates,
        selected=selected,
        skipped_existing=skipped_existing,
        downloaded=downloaded,
        decompressed=decompressed,
        command_errors=command_errors,
        preflight_status=preflight_status,
    )
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json",
        manifest,
    )
    return manifest


def normalize_historical_archive_to_trade_xyz_quotes(
    *,
    data_dir: Path,
    l2_jsonl_path: Path,
    registry_path: Path | None = None,
    asset_ctxs_path: Path | None = None,
    canonical_symbol: str | None = None,
    coin: str | None = None,
    output_path: Path | None = None,
    normalize: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    if not l2_jsonl_path.exists():
        raise FileNotFoundError(f"historical l2 archive jsonl not found: {l2_jsonl_path}")
    effective_registry_path = (
        registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    instrument = _resolve_instrument(
        load_trade_xyz_registry(effective_registry_path),
        canonical_symbol=canonical_symbol,
        coin=coin,
    )
    effective_coin = coin or instrument.coin or f"xyz:{instrument.canonical_symbol}"
    archive_rows = _load_l2_rows(l2_jsonl_path)
    asset_ctxs = _load_asset_ctxs(asset_ctxs_path)
    asset_ctx = asset_ctxs.get(instrument.canonical_symbol.upper()) or asset_ctxs.get(
        _normalize_symbol(effective_coin) or ""
    )
    effective_output_path = output_path or (
        data_dir
        / "raw/quotes/trade_xyz"
        / f"historical_archive_{l2_jsonl_path.stem}_{instrument.canonical_symbol}.jsonl"
    )

    rows_written = 0
    skipped: dict[str, int] = {
        "invalid_json_object": 0,
        "missing_levels": 0,
        "missing_source_ts_ms": 0,
    }
    missing_asset_ctx_count = 0
    for row in archive_rows:
        result = build_historical_archive_quote_row(
            row=row,
            instrument=instrument,
            effective_coin=effective_coin,
            asset_ctx=asset_ctx,
            output_path=effective_output_path,
            row_index=rows_written,
        )
        if result.skip_reason is not None:
            skipped[result.skip_reason] += 1
            continue
        if result.missing_asset_ctx:
            missing_asset_ctx_count += 1
        if result.quote is None:
            continue
        append_jsonl(effective_output_path, result.quote)
        rows_written += 1

    normalized_path = data_dir / "normalized/quotes.parquet"
    duckdb_path = data_dir / "normalized/sis.duckdb"
    normalized_row_count = None
    if normalize and rows_written:
        normalized_row_count = normalize_quotes(
            data_dir / "raw/quotes", normalized_path, duckdb_path
        )

    manifest = {
        "schema_version": "trade_xyz_historical_archive_quote_normalization_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": HISTORICAL_QUOTE_SOURCE,
        "data_dir": str(data_dir),
        "l2_jsonl_path": str(l2_jsonl_path),
        "asset_ctxs_path": str(asset_ctxs_path) if asset_ctxs_path is not None else None,
        "registry_path": str(effective_registry_path),
        "canonical_symbol": instrument.canonical_symbol,
        "coin": effective_coin,
        "raw_quote_output_path": str(effective_output_path),
        "normalize_requested": normalize,
        "normalized_quotes_path": str(normalized_path)
        if normalized_row_count is not None
        else None,
        "duckdb_path": str(duckdb_path) if normalized_row_count is not None else None,
        "archive_row_count": len(archive_rows),
        "rows_written": rows_written,
        "normalized_row_count": normalized_row_count,
        "skipped": skipped,
        "asset_ctx_matched": asset_ctx is not None,
        "missing_asset_ctx_count": missing_asset_ctx_count,
        "notes": [
            "Historical archive quotes are traceable raw quote rows, but they are derived from S3 archive files.",
            "Do not mix historical archive rows with live quote coverage unless provenance and missing context are acceptable.",
            "L2-only rows without asset_ctxs are marked not tradable with BLOCK_HISTORICAL_ASSET_CTX_MISSING.",
        ],
    }
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_quote_normalization_manifest.json",
        manifest,
    )
    return manifest


def normalize_historical_archive_bulk_to_trade_xyz_quotes(
    *,
    data_dir: Path,
    plan_path: Path | None = None,
    registry_path: Path | None = None,
    max_files: int | None = None,
    skip_existing_raw_quotes: bool = True,
    normalize: bool = True,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_plan_path = (
        plan_path or data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json"
    )
    if not effective_plan_path.exists():
        raise FileNotFoundError(f"historical archive bulk plan not found: {effective_plan_path}")
    plan = read_json(effective_plan_path)
    if not isinstance(plan, dict):
        raise ValueError(f"historical archive bulk plan is not an object: {effective_plan_path}")
    plan = cast(dict[str, Any], plan)

    generated = generated_at or datetime.now(UTC)
    normalized_files: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    candidates, skipped = select_bulk_quote_normalization_candidates(
        data_dir=data_dir,
        plan=plan,
        skip_existing_raw_quotes=skip_existing_raw_quotes,
    )
    for candidate in candidates:
        try:
            child = normalize_historical_archive_to_trade_xyz_quotes(
                data_dir=data_dir,
                l2_jsonl_path=candidate.l2_path,
                registry_path=registry_path,
                asset_ctxs_path=candidate.asset_ctxs_path,
                coin=candidate.coin,
                output_path=candidate.output_path,
                normalize=False,
                generated_at=generated,
            )
        except (FileNotFoundError, ValueError) as exc:
            errors.append(
                {
                    "l2_jsonl_path": str(candidate.l2_path),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        normalized_files.append(child)
        if max_files is not None and len(normalized_files) >= max_files:
            break

    normalized_path = data_dir / "normalized/quotes.parquet"
    duckdb_path = data_dir / "normalized/sis.duckdb"
    normalized_row_count = None
    if normalize and normalized_files:
        normalized_row_count = normalize_quotes(
            data_dir / "raw/quotes", normalized_path, duckdb_path
        )

    manifest = {
        "schema_version": "trade_xyz_historical_archive_bulk_quote_normalization_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.bulk_quote_normalization",
        "data_dir": str(data_dir),
        "plan_path": str(effective_plan_path),
        "registry_path": str(registry_path)
        if registry_path is not None
        else str(data_dir / "registry/trade_xyz_instrument_registry.json"),
        "normalize_requested": normalize,
        "max_files": max_files,
        "skip_existing_raw_quotes": skip_existing_raw_quotes,
        "normalized_file_count": len(normalized_files),
        "rows_written": sum(int(item.get("rows_written") or 0) for item in normalized_files),
        "normalized_row_count": normalized_row_count,
        "normalized_quotes_path": str(normalized_path)
        if normalized_row_count is not None
        else None,
        "duckdb_path": str(duckdb_path) if normalized_row_count is not None else None,
        "skipped": skipped,
        "error_count": len(errors),
        "errors": errors,
        "files": normalized_files,
        "status": "completed_with_errors" if errors else "completed",
        "notes": [
            "Bulk normalization only processes decompressed l2Book files present on disk.",
            "Each output raw quote JSONL is written as a flat data/raw/quotes/trade_xyz/*.jsonl file so existing coverage checks can see it.",
            "Missing asset_ctxs keeps rows not tradable through BLOCK_HISTORICAL_ASSET_CTX_MISSING.",
        ],
    }
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json",
        manifest,
    )
    return manifest
