from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import math
import os
from pathlib import Path
from typing import Any, Literal

from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import write_json
from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import join_csv
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

RequirementStatus = Literal["pass", "fail", "known_gap"]


def _load_manifest(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing manifest: {path}"
    payload = read_json(path)
    if not isinstance(payload, dict):
        return None, f"manifest is not an object: {path}"
    return payload, None


def _requirement(
    *,
    key: str,
    status: RequirementStatus,
    evidence_path: Path | None,
    details: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "status": status,
        "evidence_path": str(evidence_path) if evidence_path is not None else None,
        "reason": reason,
        "details": details or {},
    }


def _configured_account_fee_user_hash() -> str | None:
    user_address = os.environ.get("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", "").strip()
    if not user_address:
        return None
    return hashlib.sha256(user_address.lower().encode("utf-8")).hexdigest()


def _quote_coverage_requirement(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_quote_coverage_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return _requirement(
            key="quote_coverage",
            status="fail",
            evidence_path=path,
            reason=error,
        )
    passed = bool(payload.get("coverage_passed"))
    return _requirement(
        key="quote_coverage",
        status="pass" if passed else "fail",
        evidence_path=path,
        reason=None if passed else "quote coverage manifest did not pass",
        details={
            "coverage_passed": passed,
            "symbol_count": payload.get("symbol_count"),
            "row_count": payload.get("row_count"),
            "raw_row_count": payload.get("raw_row_count"),
            "traceable_only": payload.get("traceable_only"),
            "excluded_missing_raw_payload_ref_count": payload.get(
                "excluded_missing_raw_payload_ref_count"
            ),
            "excluded_missing_raw_payload_ref_by_symbol": payload.get(
                "excluded_missing_raw_payload_ref_by_symbol", {}
            ),
            "raw_payload_ref_missing_rate_all_rows": payload.get(
                "raw_payload_ref_missing_rate_all_rows"
            ),
            "per_symbol": payload.get("per_symbol", {}),
        },
    )


def _reference_requirement(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_reference_datasets_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return _requirement(
            key="reference_datasets",
            status="fail",
            evidence_path=path,
            reason=error,
        )
    row_counts = payload.get("row_counts") if isinstance(payload.get("row_counts"), dict) else {}
    required_counts = {
        "instrument_registry_snapshots": row_counts.get("instrument_registry_snapshots", 0),
        "fee_snapshots": row_counts.get("fee_snapshots", 0),
        "session_calendar_snapshots": row_counts.get("session_calendar_snapshots", 0),
        "quote_logs_read": row_counts.get("quote_logs_read", 0),
    }
    missing = [
        name for name, count in required_counts.items() if not isinstance(count, int) or count <= 0
    ]
    return _requirement(
        key="reference_datasets",
        status="fail" if missing else "pass",
        evidence_path=path,
        reason=f"missing or empty reference datasets: {', '.join(missing)}" if missing else None,
        details={
            "row_counts": row_counts,
            "artifacts": payload.get("artifacts", {}),
            "funding_skipped": payload.get("funding_skipped", {}),
        },
    )


def _nonzero_counts(payload: Any) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in payload.items():
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            continue
        if count > 0:
            counts[str(key)] = count
    return counts


def _funding_requirement(data_dir: Path) -> dict[str, Any]:
    history_join_path = data_dir / "manifests/funding_history_join_manifest.json"
    history_join, _history_join_error = _load_manifest(history_join_path)
    if history_join is not None:
        usable = bool(history_join.get("usable_as_backtest_funding_event"))
        row_count = int(history_join.get("row_count") or 0)
        skipped = _nonzero_counts(history_join.get("skipped"))
        quote_skipped = _nonzero_counts(history_join.get("quote_skipped"))
        if usable and row_count > 0 and not skipped:
            return _requirement(
                key="funding_events",
                status="pass",
                evidence_path=history_join_path,
                details={
                    "source": "funding_history_join",
                    "artifact_path": history_join.get("artifact_path"),
                    "row_count": row_count,
                    "skipped": skipped,
                    "quote_skipped": quote_skipped,
                    "max_oracle_lag_minutes": history_join.get("max_oracle_lag_minutes"),
                },
            )
        if row_count > 0:
            return _requirement(
                key="funding_events",
                status="known_gap",
                evidence_path=history_join_path,
                reason="funding history join is partial or not marked usable",
                details={
                    "source": "funding_history_join",
                    "artifact_path": history_join.get("artifact_path"),
                    "row_count": row_count,
                    "usable_as_backtest_funding_event": usable,
                    "skipped": skipped,
                    "quote_skipped": quote_skipped,
                    "max_oracle_lag_minutes": history_join.get("max_oracle_lag_minutes"),
                },
            )

    quote_funding_path = data_dir / "manifests/funding_manifest.json"
    quote_funding, quote_funding_error = _load_manifest(quote_funding_path)
    if quote_funding is not None:
        row_count = int(quote_funding.get("row_count") or 0)
        skipped = _nonzero_counts(quote_funding.get("skipped"))
        if row_count > 0 and not skipped:
            return _requirement(
                key="funding_events",
                status="pass",
                evidence_path=quote_funding_path,
                details={
                    "source": "quote_snapshot_hourly_bucket",
                    "artifact_path": quote_funding.get("artifact_path"),
                    "row_count": row_count,
                    "skipped": skipped,
                },
            )
        if row_count > 0:
            return _requirement(
                key="funding_events",
                status="known_gap",
                evidence_path=quote_funding_path,
                reason="quote-derived funding manifest has skipped rows",
                details={
                    "source": "quote_snapshot_hourly_bucket",
                    "artifact_path": quote_funding.get("artifact_path"),
                    "row_count": row_count,
                    "skipped": skipped,
                },
            )
        return _requirement(
            key="funding_events",
            status="fail",
            evidence_path=quote_funding_path,
            reason="funding manifest exists but row_count is zero",
            details={"skipped": quote_funding.get("skipped", {})},
        )
    return _requirement(
        key="funding_events",
        status="fail",
        evidence_path=quote_funding_path,
        reason=quote_funding_error or "missing funding manifest",
        details={
            "preferred_manifest": str(history_join_path),
            "fallback_manifest": str(quote_funding_path),
        },
    )


def _real_market_reference_requirement(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_real_market_reference_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return _requirement(
            key="real_market_reference",
            status="fail",
            evidence_path=path,
            reason=error,
        )
    row_count = int(payload.get("row_count") or 0)
    missing_mapped = (
        payload.get("missing_mapped_symbols")
        if isinstance(payload.get("missing_mapped_symbols"), list)
        else []
    )
    missing_requested = (
        payload.get("missing_requested_symbols")
        if isinstance(payload.get("missing_requested_symbols"), list)
        else []
    )
    passed = (
        payload.get("status") == "pass"
        and row_count > 0
        and not missing_mapped
        and not missing_requested
    )
    return _requirement(
        key="real_market_reference",
        status="pass" if passed else "fail",
        evidence_path=path,
        reason=None
        if passed
        else "real-market reference bars are empty or missing requested/mapped symbols",
        details={
            "status": payload.get("status"),
            "provider": payload.get("provider"),
            "interval": payload.get("interval"),
            "row_count": row_count,
            "requested_symbols": payload.get("requested_symbols", []),
            "returned_symbols": payload.get("returned_symbols", []),
            "missing_mapped_symbols": missing_mapped,
            "missing_requested_symbols": missing_requested,
            "artifacts": payload.get("artifacts", {}),
        },
    )


def _signal_candles_requirement(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/trade_xyz_signal_candles_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return _requirement(
            key="signal_candles",
            status="fail",
            evidence_path=path,
            reason=error,
        )
    row_count = int(payload.get("row_count") or 0)
    request_error_count = int(payload.get("request_error_count") or 0)
    requested_symbols = {
        str(item).strip().upper()
        for item in payload.get("requested_symbols", [])
        if str(item).strip()
    }
    symbols = {
        str(item).strip().upper() for item in payload.get("symbols", []) if str(item).strip()
    }
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry_symbols: set[str] = set()
    if registry_path.exists():
        try:
            registry_symbols = {
                item.canonical_symbol.upper()
                for item in load_trade_xyz_registry(registry_path)
                if item.venue.value == "trade_xyz" and item.active
            }
        except (FileNotFoundError, ValueError):
            registry_symbols = set()
    expected_symbols = registry_symbols or requested_symbols
    requested_intervals = {
        str(item).strip() for item in payload.get("requested_intervals", []) if str(item).strip()
    }
    intervals = {str(item).strip() for item in payload.get("intervals", []) if str(item).strip()}
    expected_intervals = requested_intervals or {"30m", "4h", "1d", "3d"}
    missing_symbols = sorted(expected_symbols - symbols)
    missing_intervals = sorted(expected_intervals - intervals)
    passed = (
        row_count > 0 and request_error_count == 0 and not missing_symbols and not missing_intervals
    )
    return _requirement(
        key="signal_candles",
        status="pass" if passed else "fail",
        evidence_path=path,
        reason=None
        if passed
        else "signal candle collection is empty, partial, or has request errors",
        details={
            "source": payload.get("source"),
            "row_count": row_count,
            "symbol_count": payload.get("symbol_count"),
            "symbols": sorted(symbols),
            "requested_symbols": sorted(requested_symbols),
            "expected_symbols": sorted(expected_symbols),
            "missing_symbols": missing_symbols,
            "intervals": sorted(intervals),
            "requested_intervals": sorted(requested_intervals),
            "expected_intervals": sorted(expected_intervals),
            "missing_intervals": missing_intervals,
            "request_error_count": request_error_count,
            "request_errors": payload.get("request_errors", {}),
            "artifacts": payload.get("artifacts", {}),
        },
    )


def _fee_requirement(data_dir: Path) -> list[dict[str, Any]]:
    path = data_dir / "manifests/fee_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return [
            _requirement(
                key="fee_snapshots",
                status="fail",
                evidence_path=path,
                reason=error,
            )
        ]
    row_count = int(payload.get("fee_snapshot_count") or payload.get("row_count") or 0)
    unresolved = int(payload.get("unresolved_symbol_count") or 0)
    requirements = [
        _requirement(
            key="fee_snapshots",
            status="pass" if row_count > 0 and unresolved == 0 else "fail",
            evidence_path=path,
            reason=None
            if row_count > 0 and unresolved == 0
            else "fee snapshots are empty or contain unresolved symbols",
            details={
                "fee_snapshot_count": row_count,
                "unresolved_symbol_count": unresolved,
                "fee_mode_counts": payload.get("fee_mode_counts", {}),
                "fee_source_counts": payload.get("fee_source_counts", {}),
            },
        )
    ]
    account_fee_path = data_dir / "manifests/trade_xyz_account_fee_manifest.json"
    account_fee_payload, _account_fee_error = _load_manifest(account_fee_path)
    if account_fee_payload is not None:
        status = str(account_fee_payload.get("status") or "")
        configured_user_hash = _configured_account_fee_user_hash()
        manifest_user_hash = account_fee_payload.get("user_address_sha256")
        matches_configured_user = (
            manifest_user_hash == configured_user_hash
            if manifest_user_hash is not None and configured_user_hash is not None
            else None
        )
        parsed = (
            account_fee_payload.get("parsed")
            if isinstance(account_fee_payload.get("parsed"), dict)
            else {}
        )
        has_effective_rates = (
            parsed.get("user_taker_fee_bps") is not None
            and parsed.get("user_maker_fee_bps") is not None
        )
        passed = status == "pass" and has_effective_rates and matches_configured_user is not False
        reason = None
        if status != "pass" or not has_effective_rates:
            reason = "account fee manifest exists but effective maker/taker rates are incomplete"
        elif matches_configured_user is False:
            reason = "account fee manifest user hash does not match configured user address"
        requirements.append(
            _requirement(
                key="account_specific_fee",
                status="pass" if passed else "known_gap",
                evidence_path=account_fee_path,
                reason=reason,
                details={
                    "status": account_fee_payload.get("status"),
                    "source": account_fee_payload.get("source"),
                    "user_address_sha256": account_fee_payload.get("user_address_sha256"),
                    "configured_user_address_sha256": configured_user_hash,
                    "matches_configured_user": matches_configured_user,
                    "available_fields": account_fee_payload.get("available_fields", []),
                    "missing_fields": account_fee_payload.get("missing_fields", []),
                    "not_collected_fields": account_fee_payload.get("not_collected_fields", {}),
                    "parsed": parsed,
                },
            )
        )
        return requirements
    if payload.get("account_specific_fee_status") == "not_collected_no_wallet_or_user_context":
        requirements.append(
            _requirement(
                key="account_specific_fee",
                status="known_gap",
                evidence_path=path,
                reason="not collected because wallet/user context is out of scope",
                details={
                    "missing_fields": payload.get("account_specific_missing_fields", []),
                    "missing_field_counts": payload.get(
                        "account_specific_missing_field_counts", {}
                    ),
                },
            )
        )
    return requirements


def _session_requirement(data_dir: Path) -> list[dict[str, Any]]:
    path = data_dir / "manifests/session_state_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return [
            _requirement(
                key="session_state",
                status="fail",
                evidence_path=path,
                reason=error,
            )
        ]
    row_count = int(payload.get("row_count") or 0)
    missing_counts = (
        payload.get("missing_field_counts")
        if isinstance(payload.get("missing_field_counts"), dict)
        else {}
    )
    session_type_counts = (
        payload.get("session_type_counts")
        if isinstance(payload.get("session_type_counts"), dict)
        else {}
    )
    has_session_classification = bool(session_type_counts) and any(
        int(value or 0) > 0 for value in session_type_counts.values()
    )
    session_status: RequirementStatus = (
        "pass" if row_count > 0 and has_session_classification else "fail"
    )
    session_reason = None
    if row_count <= 0:
        session_reason = "session state artifact is empty"
    elif not has_session_classification:
        session_reason = "session state manifest has no session_type_counts"
    requirements = [
        _requirement(
            key="session_state",
            status=session_status,
            evidence_path=path,
            reason=session_reason,
            details={
                "row_count": row_count,
                "symbol_count": payload.get("symbol_count"),
                "session_type_counts": session_type_counts,
                "calendar_source": payload.get("calendar_source"),
            },
        )
    ]
    known_gap_fields = {
        key: value
        for key, value in missing_counts.items()
        if key in {"internal_session_open", "maintenance_window"} and value
    }
    if known_gap_fields:
        requirements.append(
            _requirement(
                key="internal_session_and_maintenance",
                status="known_gap",
                evidence_path=path,
                reason="Trade[XYZ] internal session and maintenance source is not collected",
                details={"missing_field_counts": known_gap_fields},
            )
        )
    return requirements


def _oracle_requirement(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "manifests/oracle_timestamp_manifest.json"
    payload, error = _load_manifest(path)
    if payload is None:
        return _requirement(
            key="oracle_timestamp_provenance",
            status="fail",
            evidence_path=path,
            reason=error,
        )
    row_count = int(payload.get("row_count") or 0)
    present_count = int(payload.get("oracle_ts_present_count") or 0)
    missing_count = int(payload.get("oracle_ts_missing_count") or 0)
    if row_count <= 0:
        status: RequirementStatus = "fail"
        reason = "oracle timestamp manifest has no rows"
    elif missing_count > 0 or present_count <= 0:
        status = "known_gap"
        reason = "oracle timestamp provenance has missing rows"
    else:
        status = "pass"
        reason = None
    return _requirement(
        key="oracle_timestamp_provenance",
        status=status,
        evidence_path=path,
        reason=reason,
        details={
            "row_count": row_count,
            "oracle_ts_present_count": present_count,
            "oracle_ts_missing_count": missing_count,
            "oracle_ts_missing_rate": missing_count / row_count if row_count > 0 else None,
            "oracle_ts_missing_reasons": payload.get("oracle_ts_missing_reasons", {}),
            "notes": payload.get("notes", []),
        },
    )


def _quote_coverage_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "quote_coverage" or requirement["status"] != "fail":
        return None
    details = requirement.get("details") if isinstance(requirement.get("details"), dict) else {}
    per_symbol = details.get("per_symbol") if isinstance(details.get("per_symbol"), dict) else {}
    failing_symbols = [
        symbol
        for symbol, item in sorted(per_symbol.items())
        if isinstance(item, dict) and item.get("coverage_status") != "pass"
    ]
    reasons: dict[str, list[str]] = {}
    missing_rates: dict[str, dict[str, Any]] = {}
    additional_days_required: dict[str, float] = {}
    estimated_collection_days_required: dict[str, int] = {}
    traceable_only = bool(details.get("traceable_only"))
    excluded_missing_raw_payload_ref_by_symbol = (
        details.get("excluded_missing_raw_payload_ref_by_symbol")
        if isinstance(details.get("excluded_missing_raw_payload_ref_by_symbol"), dict)
        else {}
    )
    for symbol in failing_symbols:
        item = per_symbol.get(symbol, {})
        if not isinstance(item, dict):
            continue
        reasons[symbol] = list(item.get("insufficient_reasons") or [])
        missing_rates[symbol] = dict(item.get("missing_rates") or {})
        min_days = float(item.get("min_days_required") or 0.0)
        span_days = float(item.get("span_days") or 0.0)
        additional = max(0.0, min_days - span_days)
        additional_days_required[symbol] = additional
        estimated_collection_days_required[symbol] = math.ceil(additional)
    command = (
        "uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440 --interval-seconds 60"
    )
    if failing_symbols:
        command += f" --symbols {','.join(failing_symbols)}"
    estimated_max_days = max(estimated_collection_days_required.values(), default=0)
    return {
        "key": "collect_quote_coverage",
        "reason": "quote coverage is insufficient",
        "command": command,
        "follow_up_command": "uv run sis trade-xyz-collection-status --fail-on-not-ready",
        "symbols": failing_symbols,
        "recommended_collection_duration_minutes": 1440,
        "recommended_interval_seconds": 60,
        "estimated_max_collection_days_required": estimated_max_days,
        "additional_days_required_by_symbol": additional_days_required,
        "estimated_collection_days_required_by_symbol": estimated_collection_days_required,
        "insufficient_reasons_by_symbol": reasons,
        "missing_rates_by_symbol": missing_rates,
        "traceable_only": traceable_only,
        "excluded_missing_raw_payload_ref_count": details.get(
            "excluded_missing_raw_payload_ref_count"
        ),
        "excluded_missing_raw_payload_ref_by_symbol": excluded_missing_raw_payload_ref_by_symbol,
        "notes": [
            "Run the one-day data cycle repeatedly until coverage_passed=true",
            "Use collect-trade-xyz-data-cycle rather than quote-only collection so bundle/readiness artifacts are regenerated after quotes",
            "Old raw rows with missing raw_payload_ref should not be patched in place",
            "When traceable_only=true, old untraceable rows are excluded from coverage and recorded in excluded_missing_raw_payload_ref_*",
        ],
    }


def _funding_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "funding_events" or requirement["status"] == "pass":
        return None
    return {
        "key": "collect_funding_history",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-data-bundle --auto-funding-window",
        "notes": [
            "This collects public fundingHistory for the raw quote time range and joins nearest quote oracle_price",
            "Inspect funding_history_join_manifest.json skipped.missing_oracle_quote_within_lag after the run",
        ],
    }


def _real_market_reference_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "real_market_reference" or requirement["status"] != "fail":
        return None
    command = "uv run sis collect-trade-xyz-real-market-reference --period-days 365 --interval 1d"
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
        if config.usable_start_date is not None:
            command = (
                "uv run sis collect-trade-xyz-real-market-reference "
                f"--start {config.usable_start_date} --interval 1d"
            )
    except (FileNotFoundError, ValueError):
        pass
    return {
        "key": "collect_real_market_reference",
        "reason": requirement.get("reason"),
        "command": command,
        "notes": [
            "This collects read-only real-market reference bars from Trade[XYZ] registry real_market_symbol mappings",
            "yfinance output is research/backtest reference data, not live execution data",
        ],
    }


def _signal_candles_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "signal_candles" or requirement["status"] != "fail":
        return None
    command = (
        "uv run sis collect-trade-xyz-signal-candles --intervals 30m,4h,1d,3d --period-days 365"
    )
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
        command = (
            "uv run sis collect-trade-xyz-signal-candles "
            f"--intervals {join_csv(config.signal_candle_intervals)} "
            f"--period-days {config.signal_candle_period_days}"
        )
        if config.usable_start_date is not None:
            command += f" --start {config.usable_start_date}"
    except (FileNotFoundError, ValueError):
        pass
    return {
        "key": "collect_signal_candles",
        "reason": requirement.get("reason"),
        "command": command,
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "notes": [
            "This collects historical candleSnapshot OHLCV for signal inputs",
            "Do not use signal candles as fill snapshots; fill modeling uses quote snapshots",
        ],
    }


def _account_fee_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "account_specific_fee" or requirement["status"] != "known_gap":
        return None
    return {
        "key": "collect_account_fee",
        "reason": requirement.get("reason"),
        "command": "uv run sis collect-trade-xyz-account-fee --user-address 0x...",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "notes": [
            "This uses the read-only Hyperliquid /info userFees request",
            "Use a public Hyperliquid user address; no wallet secret, signing, live order, or exchange write is required",
            "For long-running collection, set SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS before scripts/collect_trade_xyz_data_cycle.sh",
            "builder_fee_bps still requires a specific builder address and is not inferred from userFees",
        ],
    }


def _oracle_timestamp_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "oracle_timestamp_provenance" or requirement["status"] == "pass":
        return None
    return {
        "key": "check_oracle_timestamp_provenance",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-reference-data",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "details": requirement.get("details", {}),
        "notes": [
            "Rebuild oracle timestamp provenance from current raw quote logs",
            "Do not fill oracle_ts_ms from source_ts_ms, recv_ts, or client timestamp",
            "If the source payload does not expose oracle timestamp, keep the missing reason and treat it as a known gap",
        ],
    }


def _session_state_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "session_state" or requirement["status"] == "pass":
        return None
    return {
        "key": "build_session_state",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-session-state",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "details": requirement.get("details", {}),
        "notes": [
            "Build session state observations from raw Trade[XYZ] quote rows",
            "Do not interpret missing internal_session_open or maintenance_window as open/closed",
            "Unsupported symbols remain a known gap until a Trade[XYZ] session spec is added",
        ],
    }


def _build_next_actions(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for requirement in requirements:
        quote_action = _quote_coverage_next_action(requirement)
        if quote_action is not None:
            actions.append(quote_action)
        funding_action = _funding_next_action(requirement)
        if funding_action is not None:
            actions.append(funding_action)
        real_market_action = _real_market_reference_next_action(requirement)
        if real_market_action is not None:
            actions.append(real_market_action)
        signal_candles_action = _signal_candles_next_action(requirement)
        if signal_candles_action is not None:
            actions.append(signal_candles_action)
        session_action = _session_state_next_action(requirement)
        if session_action is not None:
            actions.append(session_action)
        account_fee_action = _account_fee_next_action(requirement)
        if account_fee_action is not None:
            actions.append(account_fee_action)
        oracle_action = _oracle_timestamp_next_action(requirement)
        if oracle_action is not None:
            actions.append(oracle_action)
    return actions


def build_trade_xyz_data_readiness_manifest(
    *,
    data_dir: Path,
    generated_at: datetime | None = None,
    allow_known_gaps: bool = True,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    requirements: list[dict[str, Any]] = [
        _quote_coverage_requirement(data_dir),
        _reference_requirement(data_dir),
        _funding_requirement(data_dir),
        _real_market_reference_requirement(data_dir),
        _signal_candles_requirement(data_dir),
        *_fee_requirement(data_dir),
        *_session_requirement(data_dir),
        _oracle_requirement(data_dir),
    ]
    fail_count = sum(1 for item in requirements if item["status"] == "fail")
    known_gap_count = sum(1 for item in requirements if item["status"] == "known_gap")
    backtest_data_ready = fail_count == 0 and (allow_known_gaps or known_gap_count == 0)
    decision = (
        "READY_WITH_KNOWN_GAPS"
        if backtest_data_ready and known_gap_count
        else "READY"
        if backtest_data_ready
        else "NOT_READY"
    )
    next_actions = _build_next_actions(requirements)
    manifest = {
        "schema_version": "trade_xyz_data_readiness_manifest.v1",
        "generated_at": generated.isoformat(),
        "data_dir": str(data_dir),
        "decision": decision,
        "backtest_data_ready": backtest_data_ready,
        "complete_observed_market_truth": False,
        "allow_known_gaps": allow_known_gaps,
        "fail_count": fail_count,
        "known_gap_count": known_gap_count,
        "requirements": requirements,
        "next_actions": next_actions,
        "notes": [
            "READY_WITH_KNOWN_GAPS means pure backtest data can be used with explicit caveats",
            "complete_observed_market_truth is false until account-specific fees, internal session, and maintenance/halt sources are observed",
            "wallet, signing, live order, and exchange write remain out of scope",
        ],
    }
    write_json(data_dir / "manifests/trade_xyz_data_readiness_manifest.json", manifest)
    return manifest
