from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Any, Callable

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import append_jsonl
from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.normalizer import payload_hash
from sis.venues.trade_xyz.normalizer import quote_from_l2_book
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

HYPERLIQUID_ARCHIVE_BUCKET = "s3://hyperliquid-archive"
HISTORICAL_L2_ARCHIVE_SOURCE = "hyperliquid_archive.market_data.l2Book"
HISTORICAL_ASSET_CTXS_ARCHIVE_SOURCE = "hyperliquid_archive.asset_ctxs"
HISTORICAL_QUOTE_SOURCE = "hyperliquid_archive.l2Book+asset_ctxs"


@dataclass(frozen=True)
class HistoricalL2ArchiveRequest:
    coin: str
    date: date
    hour: int
    data_type: str = "l2Book"

    def __post_init__(self) -> None:
        if not self.coin:
            raise ValueError("coin is required")
        if self.hour < 0 or self.hour > 23:
            raise ValueError("hour must be between 0 and 23")
        if self.data_type != "l2Book":
            raise ValueError("only l2Book historical archive collection is supported")

    @property
    def date_part(self) -> str:
        return self.date.strftime("%Y%m%d")

    @property
    def s3_uri(self) -> str:
        return (
            f"{HYPERLIQUID_ARCHIVE_BUCKET}/market_data/"
            f"{self.date_part}/{self.hour}/{self.data_type}/{self.coin}.lz4"
        )

    @property
    def output_relative_path(self) -> Path:
        return (
            Path("raw/historical_archive/hyperliquid/market_data")
            / self.date_part
            / str(self.hour)
            / self.data_type
            / self.coin
        )


def _run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit {completed.returncode}: {' '.join(command)}")


CommandRunner = Callable[[list[str]], None]
PreflightRunner = Callable[[list[str]], tuple[int, str, str]]


def _date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end date must be >= start date")
    values: list[date] = []
    current = start
    while current <= end:
        values.append(current)
        current += timedelta(days=1)
    return values


def aws_download_command_status() -> dict[str, Any]:
    configured = os.environ.get("SIS_AWS_COMMAND")
    if configured:
        prefix = shlex.split(configured)
        return {
            "available": bool(prefix),
            "source": "SIS_AWS_COMMAND",
            "path": prefix[0] if prefix else None,
            "command_prefix": prefix,
            "requires_network_for_tool_install": False,
        }
    aws_path = shutil.which("aws")
    if aws_path is not None:
        return {
            "available": True,
            "source": "system_aws",
            "path": aws_path,
            "command_prefix": [aws_path],
            "requires_network_for_tool_install": False,
        }
    uv_path = shutil.which("uv")
    if uv_path is not None:
        return {
            "available": True,
            "source": "uv_awscli_fallback",
            "path": uv_path,
            "command_prefix": [uv_path, "run", "--with", "awscli", "aws"],
            "requires_network_for_tool_install": True,
        }
    return {
        "available": False,
        "source": "missing",
        "path": None,
        "command_prefix": ["aws"],
        "requires_network_for_tool_install": False,
    }


def _download_command(s3_uri: str, destination: Path) -> list[str]:
    return [
        *aws_download_command_status()["command_prefix"],
        "s3",
        "cp",
        s3_uri,
        str(destination),
        "--request-payer",
        "requester",
    ]


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


def _historical_archive_preflight_status(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json"
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "status": None,
            "return_code": None,
            "aws_command_source": None,
        }
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {
            "path": str(path),
            "exists": True,
            "status": "invalid",
            "return_code": None,
            "aws_command_source": None,
        }
    return {
        "path": str(path),
        "exists": True,
        "status": payload.get("status"),
        "return_code": payload.get("return_code"),
        "aws_command_source": payload.get("aws_command_source"),
    }


def _historical_archive_preflight_error(status: dict[str, Any]) -> str | None:
    if status.get("status") == "pass":
        return None
    if not status.get("exists"):
        return (
            "historical archive AWS preflight has not been run; run "
            "`uv run sis check-trade-xyz-historical-archive-preflight` before --execute"
        )
    return (
        "historical archive AWS preflight has not passed; configure AWS credentials or "
        'SIS_AWS_COMMAND="aws --profile <profile>", then rerun '
        "`uv run sis check-trade-xyz-historical-archive-preflight`"
    )


def _decompress_lz4(source: Path, destination: Path) -> None:
    lz4 = shutil.which("lz4")
    if lz4 is None:
        raise RuntimeError(
            "lz4 executable not found; install lz4 before decompressing archive data"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_command([lz4, "-d", "-f", str(source), str(destination)])


def _normalize_symbol(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("xyz:").upper()


def _source_ts_ms_from_payload(payload: dict[str, Any]) -> int | None:
    for key in ("time", "ts", "timestamp"):
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _extract_l2_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(row.get("levels"), list):
        return row
    for key in ("data", "book", "l2Book", "payload"):
        value = row.get(key)
        if isinstance(value, dict) and isinstance(value.get("levels"), list):
            return value
    return None


def _load_l2_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _coerce_asset_ctx_value(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _load_asset_ctxs(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        if sample.lstrip().startswith(("{", "[")):
            payload = json.load(handle)
            items = payload if isinstance(payload, list) else payload.get("ctxs", [])
            result: dict[str, dict[str, Any]] = {}
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict):
                    continue
                symbol = _normalize_symbol(
                    str(
                        item.get("coin")
                        or item.get("name")
                        or item.get("symbol")
                        or item.get("canonical_symbol")
                        or ""
                    )
                )
                if symbol:
                    result[symbol] = item
            return result
        reader = csv.DictReader(handle)
        result: dict[str, dict[str, Any]] = {}
        for row in reader:
            symbol = _normalize_symbol(
                row.get("coin")
                or row.get("name")
                or row.get("symbol")
                or row.get("canonical_symbol")
                or ""
            )
            if not symbol:
                continue
            if row.get("ctx"):
                parsed_ctx = _coerce_asset_ctx_value(str(row["ctx"]))
                if isinstance(parsed_ctx, dict):
                    result[symbol] = parsed_ctx
                    continue
            result[symbol] = {
                key: _coerce_asset_ctx_value(value)
                for key, value in row.items()
                if value is not None and value != ""
            }
        return result


def _resolve_instrument(
    instruments: list[InstrumentSpec],
    *,
    canonical_symbol: str | None,
    coin: str | None,
) -> InstrumentSpec:
    by_symbol = {item.canonical_symbol.upper(): item for item in instruments}
    by_coin = {str(item.coin).upper(): item for item in instruments if item.coin}
    if canonical_symbol and canonical_symbol.upper() in by_symbol:
        return by_symbol[canonical_symbol.upper()]
    if coin and coin.upper() in by_coin:
        return by_coin[coin.upper()]
    if coin and (normalized := _normalize_symbol(coin)) and normalized in by_symbol:
        return by_symbol[normalized]
    raise ValueError("historical archive symbol was not found in Trade[XYZ] registry")


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
    relative_output = request.output_relative_path
    lz4_path = data_dir / relative_output.with_suffix(".lz4")
    decompressed_path = data_dir / relative_output.with_suffix(".jsonl")
    manifest_path = data_dir / "manifests/trade_xyz_historical_l2_archive_manifest.json"
    aws_status = aws_download_command_status()

    download_command = _download_command(request.s3_uri, lz4_path)
    manifest: dict[str, Any] = {
        "schema_version": "trade_xyz_historical_l2_archive_manifest.v1",
        "generated_at": generated.isoformat(),
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
        "aws_requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
        "raw_lz4_path": str(lz4_path),
        "decompressed_path": str(decompressed_path) if decompress else None,
        "download_command": download_command,
        "status": "planned",
        "notes": [
            "Hyperliquid historical l2Book archive is requester-pays S3 data.",
            "Archive uploads are approximately monthly and may be missing or stale.",
            "Raw archive data is not normalized into quote snapshots by this command.",
        ],
    }

    if dry_run:
        write_json(manifest_path, manifest)
        return manifest
    if not acknowledge_requester_pays:
        manifest["status"] = "blocked_requires_requester_pays_ack"
        write_json(manifest_path, manifest)
        raise ValueError(
            "historical L2 archive is requester-pays; pass --acknowledge-requester-pays to download"
        )
    if not aws_status["available"]:
        manifest["status"] = "blocked_missing_aws_command"
        write_json(manifest_path, manifest)
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    preflight_status = _historical_archive_preflight_status(data_dir)
    manifest["preflight"] = preflight_status
    if preflight_error := _historical_archive_preflight_error(preflight_status):
        manifest["status"] = "blocked_preflight_failed"
        write_json(manifest_path, manifest)
        raise RuntimeError(preflight_error)

    lz4_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command(download_command)
    manifest["status"] = "downloaded"
    manifest["raw_lz4_bytes"] = lz4_path.stat().st_size if lz4_path.exists() else None
    if decompress:
        _decompress_lz4(lz4_path, decompressed_path)
        manifest["status"] = "downloaded_and_decompressed"
        manifest["decompressed_bytes"] = (
            decompressed_path.stat().st_size if decompressed_path.exists() else None
        )
    write_json(manifest_path, manifest)
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
    date_part = archive_date.strftime("%Y%m%d")
    s3_uri = f"{HYPERLIQUID_ARCHIVE_BUCKET}/asset_ctxs/{date_part}.csv.lz4"
    relative_output = Path("raw/historical_archive/hyperliquid/asset_ctxs") / f"{date_part}.csv"
    lz4_path = data_dir / relative_output.with_suffix(".csv.lz4")
    decompressed_path = data_dir / relative_output
    manifest_path = data_dir / "manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json"
    aws_status = aws_download_command_status()

    download_command = _download_command(s3_uri, lz4_path)
    manifest: dict[str, Any] = {
        "schema_version": "trade_xyz_historical_asset_ctxs_archive_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": HISTORICAL_ASSET_CTXS_ARCHIVE_SOURCE,
        "s3_uri": s3_uri,
        "date": archive_date.isoformat(),
        "requester_pays_acknowledged": acknowledge_requester_pays,
        "dry_run": dry_run,
        "decompress_requested": decompress,
        "aws_available": aws_status["available"],
        "aws_command_source": aws_status["source"],
        "aws_command_prefix": aws_status["command_prefix"],
        "aws_requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
        "raw_lz4_path": str(lz4_path),
        "decompressed_path": str(decompressed_path) if decompress else None,
        "download_command": download_command,
        "status": "planned",
        "notes": [
            "Hyperliquid historical asset_ctxs archive is requester-pays S3 data.",
            "Archive uploads are approximately monthly and may be missing or stale.",
            "Asset contexts help recover mark/oracle/funding context for historical L2 data.",
        ],
    }
    if dry_run:
        write_json(manifest_path, manifest)
        return manifest
    if not acknowledge_requester_pays:
        manifest["status"] = "blocked_requires_requester_pays_ack"
        write_json(manifest_path, manifest)
        raise ValueError(
            "historical asset_ctxs archive is requester-pays; pass "
            "--acknowledge-requester-pays to download"
        )
    if not aws_status["available"]:
        manifest["status"] = "blocked_missing_aws_command"
        write_json(manifest_path, manifest)
        raise RuntimeError(
            "aws command not found; install aws CLI, install uv, or set SIS_AWS_COMMAND"
        )
    preflight_status = _historical_archive_preflight_status(data_dir)
    manifest["preflight"] = preflight_status
    if preflight_error := _historical_archive_preflight_error(preflight_status):
        manifest["status"] = "blocked_preflight_failed"
        write_json(manifest_path, manifest)
        raise RuntimeError(preflight_error)

    lz4_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command(download_command)
    manifest["status"] = "downloaded"
    manifest["raw_lz4_bytes"] = lz4_path.stat().st_size if lz4_path.exists() else None
    if decompress:
        _decompress_lz4(lz4_path, decompressed_path)
        manifest["status"] = "downloaded_and_decompressed"
        manifest["decompressed_bytes"] = (
            decompressed_path.stat().st_size if decompressed_path.exists() else None
        )
    write_json(manifest_path, manifest)
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
    dates = _date_range(start_date, end_date)
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
                    "download_command": _download_command(s3_uri, destination),
                }
            )
        for hour in effective_hours:
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
                        "download_command": _download_command(request.s3_uri, destination),
                    }
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

    candidates: list[dict[str, Any]] = []
    if include_asset_ctxs:
        for item in plan.get("asset_ctx_objects", []):
            if isinstance(item, dict):
                candidates.append({"kind": "asset_ctxs", **item})
    if include_l2:
        for item in plan.get("l2_objects", []):
            if isinstance(item, dict):
                candidates.append({"kind": "l2", **item})
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

    preflight_status = _historical_archive_preflight_status(data_dir)
    preflight_error = (
        None
        if dry_run or command_runner is not None
        else _historical_archive_preflight_error(preflight_status)
    )
    if preflight_error is not None:
        generated = generated_at or datetime.now(UTC)
        manifest = {
            "schema_version": "trade_xyz_historical_archive_bulk_execution_manifest.v1",
            "generated_at": generated.isoformat(),
            "source": "hyperliquid_archive.bulk_execution",
            "plan_path": str(effective_plan_path),
            "dry_run": dry_run,
            "requester_pays_acknowledged": acknowledge_requester_pays,
            "aws_available": aws_status["available"],
            "aws_command_source": aws_status["source"],
            "aws_command_prefix": aws_status["command_prefix"],
            "aws_requires_network_for_tool_install": aws_status[
                "requires_network_for_tool_install"
            ],
            "include_l2": include_l2,
            "include_asset_ctxs": include_asset_ctxs,
            "skip_existing": skip_existing,
            "decompress_requested": decompress,
            "max_objects": max_objects,
            "candidate_object_count": len(candidates),
            "selected_object_count": len(selected),
            "skipped_existing_count": skipped_existing,
            "downloaded_object_count": 0,
            "decompressed_object_count": 0,
            "command_error_count": 0,
            "command_errors": [],
            "selected_objects": selected,
            "preflight": preflight_status,
            "status": "blocked_preflight_failed",
            "notes": [
                "Bulk execution was blocked before download because AWS preflight did not pass.",
                "Run check-trade-xyz-historical-archive-preflight after configuring AWS credentials.",
            ],
        }
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
    manifest = {
        "schema_version": "trade_xyz_historical_archive_bulk_execution_manifest.v1",
        "generated_at": generated.isoformat(),
        "source": "hyperliquid_archive.bulk_execution",
        "plan_path": str(effective_plan_path),
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
        "status": "planned"
        if dry_run
        else "completed_with_errors"
        if command_errors
        else "completed",
        "notes": [
            "Bulk execution reads a prebuilt requester-pays plan and never infers extra S3 objects.",
            "Use max_objects to download in small batches before running the full plan.",
            "Downloaded archive data still requires quote normalization before readiness coverage changes.",
        ],
    }
    write_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json",
        manifest,
    )
    return manifest


def _archive_quote_output_path(data_dir: Path, item: dict[str, Any]) -> Path:
    date_part = str(item.get("date") or "unknown").replace("-", "")
    hour = str(item.get("hour") if item.get("hour") is not None else "unknown")
    coin = str(item.get("coin") or "unknown").replace("/", "_").replace(":", "_")
    return data_dir / "raw/quotes/trade_xyz" / f"historical_archive_{date_part}_{hour}_{coin}.jsonl"


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
        if not isinstance(row, dict):
            skipped["invalid_json_object"] += 1
            continue
        payload = _extract_l2_payload(row)
        if payload is None:
            skipped["missing_levels"] += 1
            continue
        source_ts_ms = _source_ts_ms_from_payload(payload) or _source_ts_ms_from_payload(row)
        if source_ts_ms is None:
            skipped["missing_source_ts_ms"] += 1
            continue
        if "time" not in payload:
            payload = {**payload, "time": source_ts_ms}
        quote_ts = datetime.fromtimestamp(source_ts_ms / 1000, tz=UTC)
        row_asset_ctx = asset_ctx
        if row_asset_ctx is None:
            missing_asset_ctx_count += 1
        quote = quote_from_l2_book(
            canonical_symbol=instrument.canonical_symbol,
            coin=effective_coin,
            asset_id=instrument.asset_id,
            real_market_symbol=instrument.real_market_symbol,
            payload=payload,
            asset_ctx=row_asset_ctx,
            fee_mode=instrument.fee_mode,
            taker_fee_bps=instrument.taker_fee_bps,
            maker_fee_bps=instrument.maker_fee_bps,
            source=HISTORICAL_QUOTE_SOURCE,
            now=quote_ts,
        )
        combined_payload = {
            "l2Book": payload,
            "assetCtx": row_asset_ctx,
            "archive_row": row,
        }
        block_reasons = list(quote.block_reasons)
        if row_asset_ctx is None:
            block_reasons.append("BLOCK_HISTORICAL_ASSET_CTX_MISSING")
        block_reasons = list(dict.fromkeys(block_reasons))
        quote = quote.model_copy(
            update={
                "source_ts_ms": source_ts_ms,
                "raw_payload_sha256": payload_hash(combined_payload),
                "raw_payload": combined_payload,
                "raw_payload_ref": f"{effective_output_path}#row={rows_written}",
                "is_tradable": quote.is_tradable and row_asset_ctx is not None,
                "block_reasons": block_reasons,
            }
        )
        append_jsonl(effective_output_path, quote.model_dump(mode="json"))
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

    asset_ctx_by_date: dict[str, Path] = {}
    for item in plan.get("asset_ctx_objects", []):
        if not isinstance(item, dict):
            continue
        archive_date = str(item.get("date") or "")
        decompressed_path = item.get("decompressed_path")
        if archive_date and isinstance(decompressed_path, str):
            path = Path(decompressed_path)
            if path.exists():
                asset_ctx_by_date[archive_date] = path

    generated = generated_at or datetime.now(UTC)
    normalized_files: list[dict[str, Any]] = []
    skipped: dict[str, int] = {
        "missing_l2_jsonl": 0,
        "missing_asset_ctxs": 0,
        "raw_quote_output_exists": 0,
    }
    errors: list[dict[str, Any]] = []
    for item in plan.get("l2_objects", []):
        if not isinstance(item, dict):
            continue
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
        output_path = _archive_quote_output_path(data_dir, item)
        if skip_existing_raw_quotes and output_path.exists():
            skipped["raw_quote_output_exists"] += 1
            continue
        try:
            child = normalize_historical_archive_to_trade_xyz_quotes(
                data_dir=data_dir,
                l2_jsonl_path=l2_path,
                registry_path=registry_path,
                asset_ctxs_path=asset_ctxs_path,
                coin=str(item.get("coin") or "") or None,
                output_path=output_path,
                normalize=False,
                generated_at=generated,
            )
        except (FileNotFoundError, ValueError) as exc:
            errors.append(
                {
                    "l2_jsonl_path": str(l2_path),
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
