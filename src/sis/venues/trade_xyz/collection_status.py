from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Any, cast

from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.collection_status_inventory import raw_quote_inventory
from sis.venues.trade_xyz import collection_status_progress
from sis.venues.trade_xyz.collection_status_report import render_collection_status_report
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.collection_status_artifacts import (
    account_fee_artifact_status as _account_fee_artifact_status,
)
from sis.venues.trade_xyz.collection_status_artifacts import (
    account_fee_prerequisites as _account_fee_prerequisites,
)
from sis.venues.trade_xyz.collection_status_artifacts import (
    historical_archive_artifact_status as _historical_archive_artifact_status,
)
from sis.venues.trade_xyz.collection_status_artifacts import (
    historical_archive_backfill_action as _historical_archive_backfill_action,
)
from sis.venues.trade_xyz.collection_status_artifacts import (
    runtime_prerequisites as _runtime_prerequisites,
)
from sis.venues.trade_xyz.collection_status_artifacts import (
    ws_artifact_status as _ws_artifact_status,
)
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest

_coverage_progress = collection_status_progress.coverage_progress
_parse_generated_at = collection_status_progress.parse_generated_at
_progress_since_previous = collection_status_progress.progress_since_previous
_cycle_command = collection_status_progress.cycle_command
_raw_quote_inventory = raw_quote_inventory
_render_collection_status_report = render_collection_status_report


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    return cast(dict[str, Any], payload) if isinstance(payload, dict) else None


def _readiness_requirement_summary(readiness: dict[str, Any] | None) -> dict[str, Any]:
    if readiness is None:
        return {
            "pass": [],
            "fail": [],
            "known_gap": [],
            "unknown": [],
        }
    requirements_value = readiness.get("requirements")
    requirements = (
        cast(list[object], requirements_value) if isinstance(requirements_value, list) else []
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
        item = cast(dict[str, Any], item)
        key = str(item.get("key") or "")
        if not key:
            continue
        status = str(item.get("status") or "unknown")
        if status not in summary:
            status = "unknown"
        summary[status].append(key)
    return {key: sorted(values) for key, values in summary.items()}


def _readiness_requirement_details(readiness: dict[str, Any] | None) -> dict[str, Any]:
    requirements_value = readiness.get("requirements") if readiness is not None else None
    requirements = (
        cast(list[object], requirements_value) if isinstance(requirements_value, list) else []
    )
    details: dict[str, Any] = {}
    for item in requirements:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        key = str(item.get("key") or "")
        if not key:
            continue
        item_details_value = item.get("details")
        item_details = (
            cast(dict[str, Any], item_details_value) if isinstance(item_details_value, dict) else {}
        )
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
    report = _render_collection_status_report(
        status=status,
        progress=progress,
        readiness_requirements=readiness_requirements,
        readiness_details=readiness_details,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    status["report_path"] = str(report_path)
    write_json(data_dir / "ops/trade_xyz_collection_status.json", status)
    return status
