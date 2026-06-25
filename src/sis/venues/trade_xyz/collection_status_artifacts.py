from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import shlex
import shutil
from typing import Any, cast

from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.historical_archive import aws_download_command_status


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    return cast(dict[str, Any], payload) if isinstance(payload, dict) else None


def runtime_prerequisites() -> dict[str, Any]:
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


def account_fee_prerequisites() -> dict[str, Any]:
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


def account_fee_artifact_status(
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


def historical_archive_artifact_status(data_dir: Path) -> dict[str, Any]:
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


def ws_artifact_status(data_dir: Path) -> dict[str, Any]:
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


def historical_archive_backfill_action(
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
