from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Any

from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest
from sis.venues.trade_xyz.historical_archive import aws_download_command_status
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    return payload if isinstance(payload, dict) else None


def _raw_quote_inventory(raw_quotes_root: Path, *, generated_at: datetime) -> dict[str, Any]:
    quote_dir = raw_quotes_root / "trade_xyz"
    files = sorted(quote_dir.glob("*.jsonl"))
    total_rows = 0
    traceable_rows = 0
    untraceable_rows = 0
    malformed_rows = 0
    missing_symbol_rows = 0
    symbol_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    latest_path: Path | None = None
    latest_mtime: float | None = None
    per_file: list[dict[str, Any]] = []
    for path in files:
        row_count = 0
        traceable_count = 0
        file_malformed_rows = 0
        file_missing_symbol_rows = 0
        file_symbol_counts: dict[str, int] = {}
        file_source_counts: dict[str, int] = {}
        with path.open("r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        for line in lines:
            row_count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed_rows += 1
                file_malformed_rows += 1
                continue
            if not isinstance(row, dict):
                malformed_rows += 1
                file_malformed_rows += 1
                continue
            if row.get("raw_payload_ref") is None:
                untraceable_rows += 1
            else:
                traceable_count += 1
            symbol = (
                row.get("canonical_symbol")
                or row.get("symbol")
                or row.get("asset_symbol")
                or row.get("coin")
            )
            if isinstance(symbol, str) and symbol.strip():
                symbol_key = symbol.strip().upper()
            else:
                symbol_key = "<missing>"
                missing_symbol_rows += 1
                file_missing_symbol_rows += 1
            source = row.get("source")
            source_key = (
                source.strip() if isinstance(source, str) and source.strip() else "<missing>"
            )
            symbol_counts[symbol_key] = symbol_counts.get(symbol_key, 0) + 1
            file_symbol_counts[symbol_key] = file_symbol_counts.get(symbol_key, 0) + 1
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            file_source_counts[source_key] = file_source_counts.get(source_key, 0) + 1
        total_rows += row_count
        traceable_rows += traceable_count
        stat = path.stat()
        if latest_mtime is None or stat.st_mtime > latest_mtime:
            latest_mtime = stat.st_mtime
            latest_path = path
        per_file.append(
            {
                "path": str(path),
                "row_count": row_count,
                "traceable_row_count": traceable_count,
                "untraceable_row_count": row_count - traceable_count,
                "malformed_row_count": file_malformed_rows,
                "missing_symbol_row_count": file_missing_symbol_rows,
                "symbol_counts": dict(sorted(file_symbol_counts.items())),
                "source_counts": dict(sorted(file_source_counts.items())),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    latest_file_modified_at = (
        datetime.fromtimestamp(latest_mtime, tz=UTC) if latest_mtime is not None else None
    )
    latest_file_age_seconds = (
        max(0.0, (generated_at - latest_file_modified_at).total_seconds())
        if latest_file_modified_at is not None
        else None
    )
    untraceable_rows = total_rows - traceable_rows
    return {
        "raw_quotes_root": str(raw_quotes_root),
        "file_count": len(files),
        "row_count": total_rows,
        "traceable_row_count": traceable_rows,
        "untraceable_row_count": untraceable_rows,
        "malformed_row_count": malformed_rows,
        "missing_symbol_row_count": missing_symbol_rows,
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "latest_file": str(latest_path) if latest_path is not None else None,
        "latest_file_modified_at": latest_file_modified_at.isoformat()
        if latest_file_modified_at is not None
        else None,
        "latest_file_age_seconds": latest_file_age_seconds,
        "files": per_file,
    }


def _format_counts(counts: dict[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in sorted(counts.items()))


def _coverage_progress(coverage: dict[str, Any] | None) -> dict[str, Any]:
    if coverage is None:
        return {
            "coverage_passed": False,
            "reason": "missing trade_xyz_quote_coverage_manifest.json",
            "symbols": {},
            "estimated_max_collection_days_required": None,
            "min_span_days": None,
            "max_span_days": None,
            "max_remaining_days_exact": None,
            "completion_ratio_by_span": None,
            "slowest_symbols": [],
        }
    per_symbol = coverage.get("per_symbol") if isinstance(coverage.get("per_symbol"), dict) else {}
    symbols: dict[str, Any] = {}
    max_days = 0
    min_span_days: float | None = None
    max_span_days = 0.0
    max_remaining_days_exact = 0.0
    slowest_symbols: list[str] = []
    for symbol, item in sorted(per_symbol.items()):
        if not isinstance(item, dict):
            continue
        min_days = float(item.get("min_days_required") or 0.0)
        span_days = float(item.get("span_days") or 0.0)
        remaining = max(0.0, min_days - span_days)
        remaining_ceiling = int(remaining) if remaining.is_integer() else int(remaining) + 1
        max_days = max(max_days, remaining_ceiling)
        max_span_days = max(max_span_days, span_days)
        min_span_days = span_days if min_span_days is None else min(min_span_days, span_days)
        if remaining > max_remaining_days_exact:
            max_remaining_days_exact = remaining
            slowest_symbols = [symbol]
        elif remaining == max_remaining_days_exact:
            slowest_symbols.append(symbol)
        symbols[symbol] = {
            "coverage_status": item.get("coverage_status"),
            "row_count": item.get("row_count"),
            "raw_row_count": item.get("raw_row_count"),
            "span_days": span_days,
            "min_days_required": min_days,
            "max_gap_seconds": item.get("max_gap_seconds"),
            "estimated_collection_days_required": remaining_ceiling,
            "insufficient_reasons": item.get("insufficient_reasons", []),
            "missing_rates": item.get("missing_rates", {}),
            "excluded_missing_raw_payload_ref_count": item.get(
                "excluded_missing_raw_payload_ref_count"
            ),
        }
    return {
        "coverage_passed": bool(coverage.get("coverage_passed")),
        "traceable_only": coverage.get("traceable_only"),
        "row_count": coverage.get("row_count"),
        "raw_row_count": coverage.get("raw_row_count"),
        "excluded_missing_raw_payload_ref_count": coverage.get(
            "excluded_missing_raw_payload_ref_count"
        ),
        "raw_payload_ref_missing_rate_all_rows": coverage.get(
            "raw_payload_ref_missing_rate_all_rows"
        ),
        "estimated_max_collection_days_required": max_days,
        "min_span_days": min_span_days,
        "max_span_days": max_span_days,
        "max_remaining_days_exact": max_remaining_days_exact,
        "completion_ratio_by_span": (
            max_span_days / max(max_span_days + max_remaining_days_exact, 1e-12)
        ),
        "slowest_symbols": slowest_symbols,
        "symbols": symbols,
    }


def _parse_generated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _progress_since_previous(
    previous_status: dict[str, Any] | None,
    *,
    generated_at: datetime,
    raw_inventory: dict[str, Any],
    coverage: dict[str, Any],
    collector_process: dict[str, Any],
    latest_file_stale: bool,
    interval_seconds: int,
) -> dict[str, Any]:
    if previous_status is None:
        return {
            "previous_status_exists": False,
            "seconds_since_previous_status": None,
            "row_count_delta": None,
            "traceable_row_count_delta": None,
            "status": "unknown_no_previous_status",
            "warnings": [],
        }
    previous_generated_at = _parse_generated_at(previous_status.get("generated_at"))
    previous_inventory = (
        previous_status.get("raw_quote_inventory")
        if isinstance(previous_status.get("raw_quote_inventory"), dict)
        else {}
    )
    previous_rows = int(previous_inventory.get("row_count") or 0)
    previous_traceable = int(previous_inventory.get("traceable_row_count") or 0)
    current_rows = int(raw_inventory.get("row_count") or 0)
    current_traceable = int(raw_inventory.get("traceable_row_count") or 0)
    seconds_since_previous = (
        max(0.0, (generated_at - previous_generated_at).total_seconds())
        if previous_generated_at is not None
        else None
    )
    row_delta = current_rows - previous_rows
    traceable_delta = current_traceable - previous_traceable
    warnings: list[str] = []
    if latest_file_stale:
        warnings.append("latest_file_stale")
    if not collector_process.get("running") and not coverage.get("coverage_passed"):
        warnings.append("collector_not_running_while_coverage_incomplete")
    if (
        collector_process.get("running")
        and seconds_since_previous is not None
        and seconds_since_previous >= interval_seconds * 2
        and traceable_delta <= 0
    ):
        warnings.append("no_traceable_row_growth_since_previous_status")
    return {
        "previous_status_exists": True,
        "seconds_since_previous_status": seconds_since_previous,
        "row_count_delta": row_delta,
        "traceable_row_count_delta": traceable_delta,
        "status": "warning" if warnings else "collecting_ok",
        "warnings": warnings,
    }


def _cycle_command(symbols: list[str], *, duration_minutes: int, interval_seconds: int) -> str:
    command = (
        "uv run sis collect-trade-xyz-data-cycle "
        f"--collection-config {DEFAULT_COLLECTION_CONFIG_PATH} "
        f"--duration-minutes {duration_minutes} --interval-seconds {interval_seconds}"
    )
    if symbols:
        command += f" --symbols {','.join(symbols)}"
    return command


def _runtime_prerequisites() -> dict[str, Any]:
    aws_status = aws_download_command_status()
    aws_preflight_command = shlex.join(
        [*aws_status["command_prefix"], "sts", "get-caller-identity"]
    )
    lz4_path = shutil.which("lz4")
    return {
        "aws_cli": {
            "available": aws_status["available"],
            "source": aws_status["source"],
            "path": aws_status["path"],
            "command_prefix": aws_status["command_prefix"],
            "preflight_command": aws_preflight_command,
            "requires_network_for_tool_install": aws_status["requires_network_for_tool_install"],
            "required_for": [
                "execute-trade-xyz-historical-archive-bulk --execute",
                "collect-trade-xyz-historical-l2-archive --execute",
                "collect-trade-xyz-historical-asset-ctxs-archive --execute",
            ],
        },
        "lz4": {
            "available": lz4_path is not None,
            "path": lz4_path,
            "required_for": [
                "historical archive decompression",
                "normalize-trade-xyz-historical-archive-quotes from downloaded archive objects",
            ],
        },
    }


def _account_fee_prerequisites() -> dict[str, Any]:
    value = os.environ.get("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", "").strip()
    return {
        "env_var": "SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS",
        "configured": bool(value),
        "user_address_sha256": hashlib.sha256(value.lower().encode("utf-8")).hexdigest()
        if value
        else None,
        "required_for": ["account_specific_fee"],
        "notes": [
            "Public Hyperliquid user address only; no wallet secret, signing, or exchange write.",
            "When configured, scripts/collect_trade_xyz_data_cycle.sh passes it to collect-trade-xyz-data-cycle.",
        ],
    }


def _account_fee_artifact_status(
    data_dir: Path, *, account_fee_prerequisites: dict[str, Any]
) -> dict[str, Any]:
    manifest_path = data_dir / "manifests/trade_xyz_account_fee_manifest.json"
    manifest = _load_object(manifest_path)
    parsed = manifest.get("parsed") if manifest is not None else None
    parsed = parsed if isinstance(parsed, dict) else {}
    manifest_user_hash = manifest.get("user_address_sha256") if manifest is not None else None
    configured_user_hash = account_fee_prerequisites.get("user_address_sha256")
    return {
        "path": str(manifest_path),
        "exists": manifest is not None,
        "status": manifest.get("status") if manifest is not None else None,
        "generated_at": manifest.get("generated_at") if manifest is not None else None,
        "source": manifest.get("source") if manifest is not None else None,
        "raw_artifact_path": manifest.get("raw_artifact_path") if manifest is not None else None,
        "user_address_sha256": manifest_user_hash,
        "configured_user_address_sha256": configured_user_hash,
        "matches_configured_user": (
            manifest_user_hash == configured_user_hash
            if manifest_user_hash is not None and configured_user_hash is not None
            else None
        ),
        "user_taker_fee_bps": parsed.get("user_taker_fee_bps"),
        "user_maker_fee_bps": parsed.get("user_maker_fee_bps"),
        "user_cross_rate": parsed.get("user_cross_rate"),
        "user_add_rate": parsed.get("user_add_rate"),
        "missing_fields": manifest.get("missing_fields", []) if manifest is not None else [],
        "payload_field_keys": manifest.get("payload_field_keys", [])
        if manifest is not None
        else [],
    }


def _historical_archive_artifact_status(data_dir: Path) -> dict[str, Any]:
    plan_path = data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json"
    execution_path = (
        data_dir / "manifests/trade_xyz_historical_archive_bulk_execution_manifest.json"
    )
    normalization_path = (
        data_dir / "manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json"
    )
    plan = _load_object(plan_path)
    execution = _load_object(execution_path)
    normalization = _load_object(normalization_path)
    return {
        "bulk_plan": {
            "path": str(plan_path),
            "exists": plan is not None,
            "generated_at": plan.get("generated_at") if plan is not None else None,
            "source": plan.get("source") if plan is not None else None,
            "start_date": plan.get("start_date") if plan is not None else None,
            "end_date": plan.get("end_date") if plan is not None else None,
            "coin_count": len(plan.get("coins", [])) if plan is not None else None,
            "date_count": plan.get("date_count") if plan is not None else None,
            "hour_count": len(plan.get("hours", [])) if plan is not None else None,
            "estimated_l2_object_count": plan.get("estimated_l2_object_count")
            if plan is not None
            else None,
            "estimated_asset_ctx_object_count": plan.get("estimated_asset_ctx_object_count")
            if plan is not None
            else None,
            "estimated_total_object_count": plan.get("estimated_total_object_count")
            if plan is not None
            else None,
            "requester_pays_ack_required": plan.get("requester_pays_ack_required")
            if plan is not None
            else None,
        },
        "bulk_execution": {
            "path": str(execution_path),
            "exists": execution is not None,
            "generated_at": execution.get("generated_at") if execution is not None else None,
            "status": execution.get("status") if execution is not None else None,
            "dry_run": execution.get("dry_run") if execution is not None else None,
            "max_objects": execution.get("max_objects") if execution is not None else None,
            "candidate_object_count": execution.get("candidate_object_count")
            if execution is not None
            else None,
            "selected_object_count": execution.get("selected_object_count")
            if execution is not None
            else None,
            "downloaded_object_count": execution.get("downloaded_object_count")
            if execution is not None
            else None,
            "decompressed_object_count": execution.get("decompressed_object_count")
            if execution is not None
            else None,
            "skipped_existing_count": execution.get("skipped_existing_count")
            if execution is not None
            else None,
            "command_error_count": execution.get("command_error_count")
            if execution is not None
            else None,
            "requester_pays_acknowledged": execution.get("requester_pays_acknowledged")
            if execution is not None
            else None,
            "aws_command_source": execution.get("aws_command_source")
            if execution is not None
            else None,
        },
        "bulk_normalization": {
            "path": str(normalization_path),
            "exists": normalization is not None,
            "generated_at": normalization.get("generated_at")
            if normalization is not None
            else None,
            "status": normalization.get("status") if normalization is not None else None,
            "normalized_file_count": normalization.get("normalized_file_count")
            if normalization is not None
            else None,
            "rows_written": normalization.get("rows_written")
            if normalization is not None
            else None,
            "normalized_row_count": normalization.get("normalized_row_count")
            if normalization is not None
            else None,
            "skipped_existing_count": normalization.get("skipped_existing_count")
            if normalization is not None
            else None,
            "missing_l2_count": normalization.get("missing_l2_count")
            if normalization is not None
            else None,
            "missing_asset_ctxs_count": normalization.get("missing_asset_ctxs_count")
            if normalization is not None
            else None,
        },
    }


def _ws_artifact_status(data_dir: Path) -> dict[str, Any]:
    capture_path = data_dir / "manifests/trade_xyz_ws_capture_manifest.json"
    quality_path = data_dir / "manifests/trade_xyz_ws_quality_manifest.json"
    parity_path = data_dir / "manifests/trade_xyz_rest_parity_manifest.json"
    capture = _load_object(capture_path)
    quality = _load_object(quality_path)
    parity = _load_object(parity_path)
    return {
        "capture": {
            "path": str(capture_path),
            "exists": capture is not None,
            "status": capture.get("status") if capture is not None else None,
            "row_count": capture.get("row_count") if capture is not None else None,
            "error_count": capture.get("error_count") if capture is not None else None,
            "reconnect_count": capture.get("reconnect_count") if capture is not None else None,
        },
        "quality": {
            "path": str(quality_path),
            "exists": quality is not None,
            "status": quality.get("status") if quality is not None else None,
            "row_count": quality.get("row_count") if quality is not None else None,
            "block_reasons": quality.get("block_reasons", []) if quality is not None else [],
        },
        "rest_parity": {
            "path": str(parity_path),
            "exists": parity is not None,
            "status": parity.get("status") if parity is not None else None,
            "request_error_count": parity.get("request_error_count")
            if parity is not None
            else None,
            "missing_rest_symbols": parity.get("missing_rest_symbols", [])
            if parity is not None
            else [],
        },
    }


def _historical_archive_backfill_action(
    *,
    data_dir: Path,
    failing_symbols: list[str],
    generated_at: datetime,
    coverage: dict[str, Any],
    prerequisites: dict[str, Any],
    archive_preflight: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not failing_symbols:
        return None
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
    except (FileNotFoundError, ValueError):
        config = None
    end_date = (generated_at - timedelta(days=1)).date()
    start_date = (
        datetime.fromisoformat(config.archive_start_date).date()
        if config is not None and config.archive_start_date is not None
        else end_date - timedelta(days=29)
    )
    if start_date > end_date:
        end_date = start_date
    coins = [
        f"xyz:{symbol}" if not symbol.startswith("xyz:") else symbol for symbol in failing_symbols
    ]
    plan_command = (
        "uv run sis plan-trade-xyz-historical-archive-bulk "
        f"--coins {','.join(coins)} "
        f"--start-date {start_date.isoformat()} --end-date {end_date.isoformat()}"
    )
    dry_run_command = "uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10"
    execute_command = (
        "uv run sis execute-trade-xyz-historical-archive-bulk "
        "--execute --acknowledge-requester-pays --max-objects 10"
    )
    normalize_template = "uv run sis normalize-trade-xyz-historical-archive-bulk"
    aws_available = bool(prerequisites.get("aws_cli", {}).get("available"))
    lz4_available = bool(prerequisites.get("lz4", {}).get("available"))
    blocked_by: list[str] = []
    if not aws_available:
        blocked_by.append("missing_aws_command")
    if not lz4_available:
        blocked_by.append("missing_lz4")
    if archive_preflight is not None and archive_preflight.get("status") == "fail":
        blocked_by.append("aws_preflight_failed")
    return {
        "key": "historical_archive_backfill",
        "reason": "quote coverage is not ready; archive backfill can reduce waiting time",
        "status": "blocked_by_prerequisites" if blocked_by else "available",
        "blocked_by": blocked_by,
        "plan_command": plan_command,
        "preflight_command": prerequisites.get("aws_cli", {}).get("preflight_command"),
        "preflight_status": archive_preflight.get("status")
        if archive_preflight is not None
        else None,
        "preflight_return_code": archive_preflight.get("return_code")
        if archive_preflight is not None
        else None,
        "command": dry_run_command,
        "dry_run_command": dry_run_command,
        "execute_command": execute_command,
        "follow_up_command": normalize_template,
        "final_check_command": "uv run sis trade-xyz-collection-status --strict --fail-on-not-ready",
        "symbols": failing_symbols,
        "coins": coins,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "coverage_min_span_days": coverage.get("min_span_days"),
        "coverage_max_remaining_days_exact": coverage.get("max_remaining_days_exact"),
        "requester_pays_ack_required": True,
        "notes": [
            "Archive execution is requester-pays and requires --execute --acknowledge-requester-pays.",
            "Downloaded archive objects do not change quote coverage until normalized into raw quote JSONL.",
            "Use small --max-objects batches first, then rerun collection status after normalization.",
        ],
    }


def _readiness_requirement_summary(readiness: dict[str, Any] | None) -> dict[str, Any]:
    if readiness is None:
        return {
            "pass": [],
            "fail": [],
            "known_gap": [],
            "unknown": [],
        }
    requirements = (
        readiness.get("requirements") if isinstance(readiness.get("requirements"), list) else []
    )
    summary: dict[str, list[str]] = {
        "pass": [],
        "fail": [],
        "known_gap": [],
        "unknown": [],
    }
    for item in requirements:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        if not key:
            continue
        status = str(item.get("status") or "unknown")
        if status not in summary:
            status = "unknown"
        summary[status].append(key)
    return {key: sorted(values) for key, values in summary.items()}


def _readiness_requirement_details(readiness: dict[str, Any] | None) -> dict[str, Any]:
    requirements = (
        readiness.get("requirements")
        if readiness is not None and isinstance(readiness.get("requirements"), list)
        else []
    )
    details: dict[str, Any] = {}
    for item in requirements:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        if not key:
            continue
        item_details = item.get("details") if isinstance(item.get("details"), dict) else {}
        details[key] = {
            "status": item.get("status"),
            "reason": item.get("reason"),
            "evidence_path": item.get("evidence_path"),
            "row_count": item_details.get("row_count"),
            "missing_symbols": item_details.get("missing_symbols", []),
            "missing_intervals": item_details.get("missing_intervals", []),
            "request_error_count": item_details.get("request_error_count"),
            "oracle_ts_missing_rate": item_details.get("oracle_ts_missing_rate"),
            "oracle_ts_present_count": item_details.get("oracle_ts_present_count"),
            "oracle_ts_missing_count": item_details.get("oracle_ts_missing_count"),
            "oracle_freshness_proxy": item_details.get("oracle_freshness_proxy", {}),
            "skipped": item_details.get("skipped", {}),
            "quote_skipped": item_details.get("quote_skipped", {}),
            "max_oracle_lag_minutes": item_details.get("max_oracle_lag_minutes"),
            "missing_requested_symbols": item_details.get("missing_requested_symbols", []),
            "missing_mapped_symbols": item_details.get("missing_mapped_symbols", []),
        }
    return details


def _process_status(
    *,
    pattern: str,
    process_rows: list[str] | None = None,
) -> dict[str, Any]:
    rows = process_rows
    if rows is None:
        try:
            completed = subprocess.run(
                ["ps", "-eo", "pid=,args="],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return {
                "running": False,
                "process_count": 0,
                "processes": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        needles = pattern.split("|")
        rows = [
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
            and any(needle in line for needle in needles)
            and "collection_status" not in line
            and "trade-xyz-collection-status" not in line
            and " rg " not in line
        ]
    return {
        "running": bool(rows),
        "process_count": len(rows),
        "processes": rows,
        "error": None,
    }


def _collector_process_status(process_rows: list[str] | None = None) -> dict[str, Any]:
    return _process_status(
        pattern="collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle",
        process_rows=process_rows,
    )


def _supervisor_process_status(process_rows: list[str] | None = None) -> dict[str, Any]:
    return _process_status(
        pattern="collect_trade_xyz_data_until_ready",
        process_rows=process_rows,
    )


def _lock_status(lock_dir: Path) -> dict[str, Any]:
    pid_path = lock_dir / "pid"
    if not lock_dir.exists():
        return {
            "path": str(lock_dir),
            "exists": False,
            "pid": None,
            "pid_running": None,
            "stale": False,
            "error": None,
        }
    if not lock_dir.is_dir():
        return {
            "path": str(lock_dir),
            "exists": True,
            "pid": None,
            "pid_running": None,
            "stale": True,
            "error": "lock_path_is_not_directory",
        }
    if not pid_path.exists():
        return {
            "path": str(lock_dir),
            "exists": True,
            "pid": None,
            "pid_running": None,
            "stale": True,
            "error": "missing_pid_file",
        }
    raw_pid = pid_path.read_text(encoding="utf-8").strip()
    if not raw_pid.isdigit():
        return {
            "path": str(lock_dir),
            "exists": True,
            "pid": raw_pid,
            "pid_running": False,
            "stale": True,
            "error": "invalid_pid_file",
        }
    pid = int(raw_pid)
    completed = subprocess.run(["kill", "-0", str(pid)], check=False)
    pid_running = completed.returncode == 0
    return {
        "path": str(lock_dir),
        "exists": True,
        "pid": pid,
        "pid_running": pid_running,
        "stale": not pid_running,
        "error": None if pid_running else "pid_not_running",
    }


def build_trade_xyz_collection_status(
    *,
    data_dir: Path,
    raw_quotes_root: Path | None = None,
    symbols: list[str] | None = None,
    min_days: float = 30.0,
    max_gap_minutes: float = 10.0,
    traceable_only: bool = True,
    refresh_coverage: bool = True,
    refresh_readiness: bool = True,
    allow_known_gaps: bool = True,
    duration_minutes: int = 1440,
    interval_seconds: int = 60,
    stale_after_minutes: float = 180.0,
    cycle_lock_dir: Path | None = None,
    supervisor_lock_dir: Path | None = None,
    generated_at: datetime | None = None,
    collector_process_rows: list[str] | None = None,
    supervisor_process_rows: list[str] | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    effective_raw_quotes_root = raw_quotes_root or data_dir / "raw/quotes"
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
    except (FileNotFoundError, ValueError):
        config = None
    if config is not None:
        if symbols is None:
            symbols = list(config.symbols)
        duration_minutes = duration_minutes or config.duration_minutes
        interval_seconds = interval_seconds or config.interval_seconds
        min_days = min_days if min_days is not None else config.min_days
        max_gap_minutes = max_gap_minutes if max_gap_minutes is not None else config.max_gap_minutes
        traceable_only = config.traceable_only if traceable_only is True else traceable_only
    coverage_path = data_dir / "manifests/trade_xyz_quote_coverage_manifest.json"
    readiness_path = data_dir / "manifests/trade_xyz_data_readiness_manifest.json"
    bundle_path = data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json"
    archive_preflight_path = (
        data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json"
    )
    summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    status_path = data_dir / "ops/trade_xyz_collection_status.json"
    previous_status = _load_object(status_path)

    coverage_refresh: dict[str, Any] = {"enabled": refresh_coverage, "status": "skipped"}
    if refresh_coverage:
        try:
            refreshed = build_trade_xyz_quote_coverage_manifest(
                data_dir=data_dir,
                raw_quotes_root=effective_raw_quotes_root,
                symbols=symbols,
                min_days=min_days,
                max_gap_minutes=max_gap_minutes,
                traceable_only=traceable_only,
                generated_at=generated,
            )
            coverage_refresh = {
                "enabled": True,
                "status": "completed",
                "coverage_passed": refreshed["coverage_passed"],
                "row_count": refreshed["row_count"],
                "raw_row_count": refreshed["raw_row_count"],
                "symbol_count": refreshed["symbol_count"],
                "traceable_only": refreshed["traceable_only"],
            }
        except (FileNotFoundError, ValueError) as exc:
            coverage_refresh = {
                "enabled": True,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }

    readiness_refresh: dict[str, Any] = {"enabled": refresh_readiness, "status": "skipped"}
    if refresh_readiness:
        try:
            refreshed_readiness = build_trade_xyz_data_readiness_manifest(
                data_dir=data_dir,
                generated_at=generated,
                allow_known_gaps=allow_known_gaps,
            )
            readiness_refresh = {
                "enabled": True,
                "status": "completed",
                "decision": refreshed_readiness["decision"],
                "backtest_data_ready": refreshed_readiness["backtest_data_ready"],
                "fail_count": refreshed_readiness["fail_count"],
                "known_gap_count": refreshed_readiness["known_gap_count"],
            }
        except (FileNotFoundError, ValueError) as exc:
            readiness_refresh = {
                "enabled": True,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }

    coverage = _load_object(coverage_path)
    readiness = _load_object(readiness_path)
    bundle = _load_object(bundle_path)
    archive_preflight = _load_object(archive_preflight_path)
    quote_summary = _load_object(summary_path)
    progress = _coverage_progress(coverage)
    symbols = list(progress["symbols"].keys())
    failing_symbols = [
        symbol
        for symbol, item in progress["symbols"].items()
        if isinstance(item, dict) and item.get("coverage_status") != "pass"
    ]
    decision = (
        "READY"
        if readiness is not None and readiness.get("backtest_data_ready") is True
        else "COLLECT_MORE_QUOTES"
        if failing_symbols
        else "MISSING_READINESS_MANIFEST"
        if readiness is None
        else "NOT_READY"
    )
    raw_inventory = _raw_quote_inventory(effective_raw_quotes_root, generated_at=generated)
    latest_age_seconds = raw_inventory.get("latest_file_age_seconds")
    latest_file_stale = latest_age_seconds is None or latest_age_seconds > stale_after_minutes * 60
    collector_process = _collector_process_status(collector_process_rows)
    supervisor_process = _supervisor_process_status(supervisor_process_rows)
    prerequisites = _runtime_prerequisites()
    account_fee_prerequisites = _account_fee_prerequisites()
    account_fee_artifact = _account_fee_artifact_status(
        data_dir, account_fee_prerequisites=account_fee_prerequisites
    )
    historical_archive_artifacts = _historical_archive_artifact_status(data_dir)
    ws_artifacts = _ws_artifact_status(data_dir)
    locks = {
        "cycle": _lock_status(cycle_lock_dir or data_dir.parent / ".tmp/trade_xyz_data_cycle.lock"),
        "supervisor": _lock_status(
            supervisor_lock_dir or data_dir.parent / ".tmp/trade_xyz_data_until_ready.lock"
        ),
    }
    progress_since_previous = _progress_since_previous(
        previous_status,
        generated_at=generated,
        raw_inventory=raw_inventory,
        coverage=progress,
        collector_process=collector_process,
        latest_file_stale=latest_file_stale,
        interval_seconds=interval_seconds,
    )
    readiness_next_actions = (
        readiness.get("next_actions", [])
        if readiness is not None and isinstance(readiness.get("next_actions"), list)
        else []
    )
    readiness_requirements = _readiness_requirement_summary(readiness)
    readiness_details = _readiness_requirement_details(readiness)
    next_actions: list[dict[str, Any]] = []
    if decision != "READY":
        next_actions.append(
            {
                "key": "collect_trade_xyz_data_cycle",
                "reason": "quote coverage is not ready" if failing_symbols else "refresh readiness",
                "command": _cycle_command(
                    failing_symbols or symbols,
                    duration_minutes=duration_minutes,
                    interval_seconds=interval_seconds,
                ),
                "estimated_max_collection_days_required": progress.get(
                    "estimated_max_collection_days_required"
                ),
                "symbols": failing_symbols or symbols,
            }
        )
    historical_archive_action = _historical_archive_backfill_action(
        data_dir=data_dir,
        failing_symbols=failing_symbols,
        generated_at=generated,
        coverage=progress,
        prerequisites=prerequisites,
        archive_preflight=archive_preflight,
    )
    if historical_archive_action is not None:
        next_actions.append(historical_archive_action)
    if decision != "READY" and not collector_process["running"]:
        next_actions.append(
            {
                "key": "start_trade_xyz_data_cycle",
                "reason": "quote coverage is not ready and no collector process was detected",
                "command": "scripts/collect_trade_xyz_data_cycle.sh",
                "notes": [
                    "This starts the read-only collection wrapper in the foreground",
                    "Use a supervisor, terminal multiplexer, cron, or systemd to keep it running across sessions",
                ],
            }
        )
    existing_action_keys = {str(item.get("key")) for item in next_actions}
    for action in readiness_next_actions:
        if not isinstance(action, dict):
            continue
        action_key = str(action.get("key") or "")
        if action_key in {"", "collect_quote_coverage"} or action_key in existing_action_keys:
            continue
        if action_key == "collect_account_fee":
            action = {
                **action,
                "env_var": account_fee_prerequisites["env_var"],
                "env_configured": account_fee_prerequisites["configured"],
                "user_address_sha256": account_fee_prerequisites["user_address_sha256"],
                "manifest_exists": account_fee_artifact["exists"],
                "manifest_status": account_fee_artifact["status"],
                "manifest_user_matches_env": account_fee_artifact["matches_configured_user"],
            }
        next_actions.append(action)
        existing_action_keys.add(action_key)
    status: dict[str, Any] = {
        "schema_version": "trade_xyz_collection_status.v1",
        "generated_at": generated.isoformat(),
        "data_dir": str(data_dir),
        "decision": decision,
        "backtest_data_ready": bool(readiness.get("backtest_data_ready"))
        if readiness is not None
        else False,
        "readiness_decision": readiness.get("decision") if readiness is not None else None,
        "fail_count": readiness.get("fail_count") if readiness is not None else None,
        "known_gap_count": readiness.get("known_gap_count") if readiness is not None else None,
        "stale_after_minutes": stale_after_minutes,
        "latest_file_stale": latest_file_stale,
        "collector_process": collector_process,
        "supervisor_process": supervisor_process,
        "locks": locks,
        "progress_since_previous_status": progress_since_previous,
        "raw_quote_inventory": raw_inventory,
        "runtime_prerequisites": prerequisites,
        "account_fee_prerequisites": account_fee_prerequisites,
        "account_fee_artifact": account_fee_artifact,
        "coverage_refresh": coverage_refresh,
        "readiness_refresh": readiness_refresh,
        "readiness_requirements": readiness_requirements,
        "readiness_requirement_details": readiness_details,
        "coverage": progress,
        "latest_quote_collection_summary": {
            "path": str(summary_path),
            "exists": quote_summary is not None,
            "row_count": quote_summary.get("row_count") if quote_summary is not None else None,
            "started_at": quote_summary.get("started_at") if quote_summary is not None else None,
            "ended_at": quote_summary.get("ended_at") if quote_summary is not None else None,
            "api_error_count": quote_summary.get("api_error_count")
            if quote_summary is not None
            else None,
            "collected_symbols": quote_summary.get("collected_symbols", [])
            if quote_summary is not None
            else [],
        },
        "bundle": {
            "path": str(bundle_path),
            "exists": bundle is not None,
            "status": bundle.get("status") if bundle is not None else None,
            "readiness_decision": bundle.get("readiness_decision") if bundle is not None else None,
            "backtest_data_ready": bundle.get("backtest_data_ready")
            if bundle is not None
            else None,
            "failed_step_count": bundle.get("failed_step_count") if bundle is not None else None,
        },
        "historical_archive_preflight": {
            "path": str(archive_preflight_path),
            "exists": archive_preflight is not None,
            "status": archive_preflight.get("status") if archive_preflight is not None else None,
            "return_code": archive_preflight.get("return_code")
            if archive_preflight is not None
            else None,
            "aws_command_source": archive_preflight.get("aws_command_source")
            if archive_preflight is not None
            else None,
        },
        "historical_archive_artifacts": historical_archive_artifacts,
        "ws_artifacts": ws_artifacts,
        "next_actions": next_actions,
        "notes": [
            "This is read-only data collection status; it performs no wallet, signing, or exchange write.",
            "Use collect-trade-xyz-data-cycle for daily collection so bundle/readiness artifacts are regenerated after quote collection.",
        ],
    }
    write_json(data_dir / "ops/trade_xyz_collection_status.json", status)

    report_path = data_dir / "reports/trade_xyz_collection_status.md"
    lines = [
        "# Trade[XYZ] Collection Status",
        "",
        f"- decision: {status['decision']}",
        f"- backtest_data_ready: {status['backtest_data_ready']}",
        f"- readiness_decision: {status['readiness_decision']}",
        f"- fail_count: {status['fail_count']}",
        f"- known_gap_count: {status['known_gap_count']}",
        f"- failing_requirements: {','.join(readiness_requirements['fail'])}",
        f"- known_gap_requirements: {','.join(readiness_requirements['known_gap'])}",
        f"- funding_events_status: {readiness_details.get('funding_events', {}).get('status')}",
        f"- funding_events_skipped: {readiness_details.get('funding_events', {}).get('skipped')}",
        "- oracle_timestamp_provenance_status: "
        f"{readiness_details.get('oracle_timestamp_provenance', {}).get('status')}",
        "- oracle_ts_missing_rate: "
        f"{readiness_details.get('oracle_timestamp_provenance', {}).get('oracle_ts_missing_rate')}",
        "- oracle_freshness_proxy_observed_rate: "
        f"{(readiness_details.get('oracle_timestamp_provenance', {}).get('oracle_freshness_proxy') or {}).get('observed_rate')}",
        f"- signal_candles_status: {readiness_details.get('signal_candles', {}).get('status')}",
        "- signal_candles_missing_symbols: "
        f"{','.join(readiness_details.get('signal_candles', {}).get('missing_symbols') or [])}",
        "- signal_candles_missing_intervals: "
        f"{','.join(readiness_details.get('signal_candles', {}).get('missing_intervals') or [])}",
        "- signal_candles_request_error_count: "
        f"{readiness_details.get('signal_candles', {}).get('request_error_count')}",
        f"- coverage_passed: {progress['coverage_passed']}",
        f"- latest_file_stale: {status['latest_file_stale']}",
        f"- collector_running: {status['collector_process']['running']}",
        f"- collector_process_count: {status['collector_process']['process_count']}",
        f"- supervisor_running: {status['supervisor_process']['running']}",
        f"- supervisor_process_count: {status['supervisor_process']['process_count']}",
        f"- cycle_lock_stale: {status['locks']['cycle']['stale']}",
        f"- supervisor_lock_stale: {status['locks']['supervisor']['stale']}",
        f"- aws_cli_available: {status['runtime_prerequisites']['aws_cli']['available']}",
        f"- aws_command_source: {status['runtime_prerequisites']['aws_cli']['source']}",
        f"- historical_archive_preflight_status: {status['historical_archive_preflight']['status']}",
        f"- historical_archive_preflight_return_code: {status['historical_archive_preflight']['return_code']}",
        "- historical_archive_bulk_plan_exists: "
        f"{status['historical_archive_artifacts']['bulk_plan']['exists']}",
        "- historical_archive_bulk_plan_estimated_total_object_count: "
        f"{status['historical_archive_artifacts']['bulk_plan']['estimated_total_object_count']}",
        "- historical_archive_bulk_execution_status: "
        f"{status['historical_archive_artifacts']['bulk_execution']['status']}",
        "- historical_archive_bulk_execution_dry_run: "
        f"{status['historical_archive_artifacts']['bulk_execution']['dry_run']}",
        "- historical_archive_bulk_execution_selected_object_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['selected_object_count']}",
        "- historical_archive_bulk_execution_downloaded_object_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['downloaded_object_count']}",
        "- historical_archive_bulk_execution_command_error_count: "
        f"{status['historical_archive_artifacts']['bulk_execution']['command_error_count']}",
        "- historical_archive_bulk_normalization_status: "
        f"{status['historical_archive_artifacts']['bulk_normalization']['status']}",
        "- historical_archive_bulk_normalization_normalized_file_count: "
        f"{status['historical_archive_artifacts']['bulk_normalization']['normalized_file_count']}",
        f"- ws_capture_manifest_exists: {status['ws_artifacts']['capture']['exists']}",
        f"- ws_capture_row_count: {status['ws_artifacts']['capture']['row_count']}",
        f"- ws_capture_error_count: {status['ws_artifacts']['capture']['error_count']}",
        f"- ws_capture_reconnect_count: {status['ws_artifacts']['capture']['reconnect_count']}",
        f"- ws_quality_manifest_exists: {status['ws_artifacts']['quality']['exists']}",
        f"- ws_quality_status: {status['ws_artifacts']['quality']['status']}",
        f"- ws_quality_row_count: {status['ws_artifacts']['quality']['row_count']}",
        f"- ws_rest_parity_manifest_exists: {status['ws_artifacts']['rest_parity']['exists']}",
        f"- ws_rest_parity_status: {status['ws_artifacts']['rest_parity']['status']}",
        "- ws_rest_parity_missing_rest_symbols: "
        f"{','.join(status['ws_artifacts']['rest_parity']['missing_rest_symbols'])}",
        f"- lz4_available: {status['runtime_prerequisites']['lz4']['available']}",
        f"- account_fee_user_address_configured: {status['account_fee_prerequisites']['configured']}",
        f"- account_fee_manifest_exists: {status['account_fee_artifact']['exists']}",
        f"- account_fee_manifest_status: {status['account_fee_artifact']['status']}",
        f"- account_fee_manifest_user_matches_env: {status['account_fee_artifact']['matches_configured_user']}",
        f"- account_fee_user_taker_fee_bps: {status['account_fee_artifact']['user_taker_fee_bps']}",
        f"- account_fee_user_maker_fee_bps: {status['account_fee_artifact']['user_maker_fee_bps']}",
        f"- progress_status: {status['progress_since_previous_status']['status']}",
        "- traceable_row_count_delta: "
        f"{status['progress_since_previous_status']['traceable_row_count_delta']}",
        f"- latest_file_age_seconds: {status['raw_quote_inventory']['latest_file_age_seconds']}",
        f"- traceable_rows: {status['raw_quote_inventory']['traceable_row_count']}",
        f"- untraceable_rows: {status['raw_quote_inventory']['untraceable_row_count']}",
        f"- malformed_rows: {status['raw_quote_inventory']['malformed_row_count']}",
        f"- missing_symbol_rows: {status['raw_quote_inventory']['missing_symbol_row_count']}",
        f"- raw_symbol_counts: {_format_counts(status['raw_quote_inventory']['symbol_counts'])}",
        f"- raw_source_counts: {_format_counts(status['raw_quote_inventory']['source_counts'])}",
        f"- coverage_min_span_days: {progress['min_span_days']}",
        f"- coverage_max_remaining_days_exact: {progress['max_remaining_days_exact']}",
        f"- coverage_completion_ratio_by_span: {progress['completion_ratio_by_span']}",
        f"- coverage_slowest_symbols: {','.join(progress['slowest_symbols'])}",
        "",
        "## Next Actions",
        "",
    ]
    if status["next_actions"]:
        for action in status["next_actions"]:
            lines.append(f"- key: {action['key']}")
            if action.get("status") is not None:
                lines.append(f"  - status: {action['status']}")
            if action.get("blocked_by"):
                lines.append(f"  - blocked_by: {','.join(action['blocked_by'])}")
            for command_key in (
                "plan_command",
                "preflight_command",
                "preflight_status",
                "preflight_return_code",
                "dry_run_command",
                "execute_command",
                "command",
                "follow_up_command",
                "final_check_command",
            ):
                command_value = action.get(command_key)
                if command_value:
                    lines.append(f"  - {command_key}: `{command_value}`")
            if action.get("env_var"):
                lines.append(f"  - env_var: {action['env_var']}")
                lines.append(f"  - env_configured: {action.get('env_configured')}")
            if action.get("user_address_sha256"):
                lines.append(f"  - user_address_sha256: {action['user_address_sha256']}")
    else:
        lines.append("- none")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    status["report_path"] = str(report_path)
    write_json(data_dir / "ops/trade_xyz_collection_status.json", status)
    return status
