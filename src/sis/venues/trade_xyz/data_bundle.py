from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sis.research.providers import PriceProvider
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import collect_quote_logs
from sis.venues.trade_xyz.account_fee import collect_trade_xyz_account_fee_snapshot
from sis.venues.trade_xyz.candles import collect_trade_xyz_signal_candles
from sis.venues.trade_xyz.candles import signal_candles_manifest_is_fresh
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.coverage import build_trade_xyz_quote_coverage_manifest
from sis.venues.trade_xyz.funding_history import (
    build_trade_xyz_backtest_funding_events_from_history,
    collect_trade_xyz_funding_history,
)
from sis.venues.trade_xyz.real_market_reference import collect_trade_xyz_real_market_reference
from sis.venues.trade_xyz.readiness import build_trade_xyz_data_readiness_manifest
from sis.venues.trade_xyz.reference_data import build_trade_xyz_reference_datasets
from sis.venues.trade_xyz.session_state import build_trade_xyz_session_state_observations


def _record_step(
    steps: list[dict[str, Any]],
    *,
    name: str,
    status: str,
    manifest_path: Path | None = None,
    details: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    steps.append(
        {
            "name": name,
            "status": status,
            "manifest_path": str(manifest_path) if manifest_path is not None else None,
            "details": details or {},
            "error": f"{type(error).__name__}: {error}" if error is not None else None,
        }
    )


def _quote_ts_ms(value: Any) -> int:
    if value.source_ts_ms is not None:
        return int(value.source_ts_ms)
    if value.recv_ts_ms is not None:
        return int(value.recv_ts_ms)
    item = (
        value.ts_client
        if value.ts_client.tzinfo is not None
        else value.ts_client.replace(tzinfo=UTC)
    )
    return int(item.timestamp() * 1000)


def _infer_funding_window_from_quotes(
    raw_quotes_root: Path,
    *,
    symbols: list[str] | None = None,
) -> tuple[int, int, dict[str, Any]]:
    requested = {item.upper() for item in symbols} if symbols else None
    logs = [
        log
        for log in collect_quote_logs(raw_quotes_root)
        if log.venue.value == "trade_xyz"
        and (requested is None or log.canonical_symbol.upper() in requested)
    ]
    if not logs:
        raise FileNotFoundError(f"No Trade[XYZ] quote JSONL rows found under {raw_quotes_root}")
    timestamps = [_quote_ts_ms(log) for log in logs]
    start_ms = min(timestamps)
    end_ms = max(timestamps) + 3_600_000
    return (
        start_ms,
        end_ms,
        {
            "source": "raw_quote_time_range_plus_1h",
            "quote_log_count": len(logs),
            "symbol_count": len({log.canonical_symbol.upper() for log in logs}),
            "first_quote_time_ms": start_ms,
            "last_quote_time_ms": max(timestamps),
            "inferred_start_time_ms": start_ms,
            "inferred_end_time_ms": end_ms,
        },
    )


def build_trade_xyz_data_collection_bundle(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    raw_quotes_root: Path | None = None,
    symbols: list[str] | None = None,
    min_days: float = 30.0,
    max_gap_minutes: float = 10.0,
    traceable_only: bool = True,
    max_oracle_lag_minutes: float = 90.0,
    funding_start_time_ms: int | None = None,
    funding_end_time_ms: int | None = None,
    auto_funding_window: bool = False,
    funding_client: TradeXyzClient | None = None,
    account_fee_user_address: str | None = None,
    account_fee_client: TradeXyzClient | None = None,
    collect_signal_candles: bool = True,
    signal_candle_intervals: list[str] | None = None,
    signal_candle_period_days: int = 365,
    signal_candle_max_age_hours: float = 24.0,
    signal_candle_client: TradeXyzClient | None = None,
    collect_real_market_reference_data: bool = True,
    real_market_provider: PriceProvider | None = None,
    allow_known_gaps: bool = True,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(UTC)
    effective_raw_quotes_root = raw_quotes_root or data_dir / "raw/quotes"
    steps: list[dict[str, Any]] = []

    try:
        manifest = build_trade_xyz_quote_coverage_manifest(
            data_dir=data_dir,
            raw_quotes_root=effective_raw_quotes_root,
            symbols=symbols,
            min_days=min_days,
            max_gap_minutes=max_gap_minutes,
            traceable_only=traceable_only,
            generated_at=generated,
        )
        _record_step(
            steps,
            name="quote_coverage",
            status="completed",
            manifest_path=data_dir / "manifests/trade_xyz_quote_coverage_manifest.json",
            details={
                "coverage_passed": manifest["coverage_passed"],
                "row_count": manifest["row_count"],
                "raw_row_count": manifest["raw_row_count"],
                "symbol_count": manifest["symbol_count"],
                "traceable_only": manifest["traceable_only"],
                "excluded_missing_raw_payload_ref_count": manifest[
                    "excluded_missing_raw_payload_ref_count"
                ],
            },
        )
    except (FileNotFoundError, ValueError) as exc:
        _record_step(steps, name="quote_coverage", status="failed", error=exc)

    try:
        manifest = build_trade_xyz_reference_datasets(
            data_dir=data_dir,
            registry_path=registry_path,
            raw_quotes_root=effective_raw_quotes_root,
            snapshot_ts=generated,
        )
        _record_step(
            steps,
            name="reference_datasets",
            status="completed",
            manifest_path=data_dir / "manifests/trade_xyz_reference_datasets_manifest.json",
            details={"row_counts": manifest["row_counts"]},
        )
    except (FileNotFoundError, ValueError) as exc:
        _record_step(steps, name="reference_datasets", status="failed", error=exc)

    try:
        manifest = build_trade_xyz_session_state_observations(
            data_dir=data_dir,
            registry_path=registry_path,
            raw_quotes_root=effective_raw_quotes_root,
            generated_at=generated,
        )
        _record_step(
            steps,
            name="session_state",
            status="completed",
            manifest_path=data_dir / "manifests/session_state_manifest.json",
            details={
                "row_count": manifest["row_count"],
                "symbol_count": manifest["symbol_count"],
                "missing_field_counts": manifest["missing_field_counts"],
            },
        )
    except (FileNotFoundError, ValueError) as exc:
        _record_step(steps, name="session_state", status="failed", error=exc)

    effective_funding_start_time_ms = funding_start_time_ms
    effective_funding_end_time_ms = funding_end_time_ms
    funding_window_source = "explicit" if funding_start_time_ms is not None else None
    if auto_funding_window and effective_funding_start_time_ms is None:
        try:
            (
                effective_funding_start_time_ms,
                effective_funding_end_time_ms,
                window_details,
            ) = _infer_funding_window_from_quotes(effective_raw_quotes_root, symbols=symbols)
            funding_window_source = "auto"
            _record_step(
                steps,
                name="funding_window",
                status="completed",
                details=window_details,
            )
        except (FileNotFoundError, ValueError) as exc:
            _record_step(steps, name="funding_window", status="failed", error=exc)
    elif auto_funding_window:
        _record_step(
            steps,
            name="funding_window",
            status="skipped",
            details={"reason": "explicit funding_start_time_ms provided"},
        )

    if effective_funding_start_time_ms is not None:
        try:
            manifest = collect_trade_xyz_funding_history(
                data_dir=data_dir,
                registry_path=registry_path,
                symbols=symbols,
                start_time_ms=effective_funding_start_time_ms,
                end_time_ms=effective_funding_end_time_ms,
                client=funding_client,
                generated_at=generated,
            )
            _record_step(
                steps,
                name="funding_history",
                status="completed",
                manifest_path=data_dir / "manifests/funding_history_manifest.json",
                details={
                    "row_count": manifest["row_count"],
                    "start_time_ms": manifest["start_time_ms"],
                    "end_time_ms": manifest["end_time_ms"],
                    "funding_window_source": funding_window_source,
                    "request_errors": manifest["request_errors"],
                },
            )
        except (FileNotFoundError, ValueError) as exc:
            _record_step(steps, name="funding_history", status="failed", error=exc)
    else:
        _record_step(
            steps,
            name="funding_history",
            status="skipped",
            details={"reason": "funding_start_time_ms not provided"},
        )

    funding_history_path = data_dir / "normalized/funding_history_events.parquet"
    if funding_history_path.exists():
        try:
            manifest = build_trade_xyz_backtest_funding_events_from_history(
                data_dir=data_dir,
                funding_history_path=funding_history_path,
                raw_quotes_root=effective_raw_quotes_root,
                max_oracle_lag_minutes=max_oracle_lag_minutes,
                generated_at=generated,
            )
            _record_step(
                steps,
                name="funding_events_from_history",
                status="completed",
                manifest_path=data_dir / "manifests/funding_history_join_manifest.json",
                details={
                    "row_count": manifest["row_count"],
                    "usable_as_backtest_funding_event": manifest[
                        "usable_as_backtest_funding_event"
                    ],
                    "skipped": manifest["skipped"],
                },
            )
        except (FileNotFoundError, ValueError) as exc:
            _record_step(steps, name="funding_events_from_history", status="failed", error=exc)
    else:
        _record_step(
            steps,
            name="funding_events_from_history",
            status="skipped",
            details={
                "reason": "funding_history_events.parquet not found; quote-derived funding_events may still be available from reference_datasets"
            },
        )

    if collect_real_market_reference_data:
        try:
            manifest = collect_trade_xyz_real_market_reference(
                data_dir=data_dir,
                registry_path=registry_path,
                symbols=symbols,
                provider=real_market_provider,
                generated_at=generated,
            )
            _record_step(
                steps,
                name="real_market_reference",
                status="completed",
                manifest_path=data_dir / "manifests/trade_xyz_real_market_reference_manifest.json",
                details={
                    "status": manifest["status"],
                    "row_count": manifest["row_count"],
                    "missing_mapped_symbols": manifest["missing_mapped_symbols"],
                    "provider": manifest["provider"],
                    "interval": manifest["interval"],
                },
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            _record_step(steps, name="real_market_reference", status="failed", error=exc)
    else:
        _record_step(
            steps,
            name="real_market_reference",
            status="skipped",
            details={"reason": "collect_real_market_reference_data=false"},
        )

    if collect_signal_candles:
        fresh, freshness = signal_candles_manifest_is_fresh(
            data_dir=data_dir,
            symbols=symbols,
            intervals=signal_candle_intervals or ["30m", "4h", "1d", "3d"],
            max_age_hours=signal_candle_max_age_hours,
            now=generated,
        )
        if fresh:
            _record_step(
                steps,
                name="signal_candles",
                status="skipped",
                manifest_path=data_dir / "manifests/trade_xyz_signal_candles_manifest.json",
                details={"reason": "fresh_existing_signal_candles", **freshness},
            )
        else:
            try:
                effective_signal_candle_client = signal_candle_client or funding_client
                if effective_signal_candle_client is None:
                    with TradeXyzClient() as client:
                        manifest = collect_trade_xyz_signal_candles(
                            data_dir=data_dir,
                            registry_path=registry_path,
                            symbols=symbols,
                            intervals=signal_candle_intervals,
                            period_days=signal_candle_period_days,
                            client=client,
                            generated_at=generated,
                        )
                else:
                    manifest = collect_trade_xyz_signal_candles(
                        data_dir=data_dir,
                        registry_path=registry_path,
                        symbols=symbols,
                        intervals=signal_candle_intervals,
                        period_days=signal_candle_period_days,
                        client=effective_signal_candle_client,
                        generated_at=generated,
                    )
                _record_step(
                    steps,
                    name="signal_candles",
                    status="completed",
                    manifest_path=data_dir / "manifests/trade_xyz_signal_candles_manifest.json",
                    details={
                        "row_count": manifest["row_count"],
                        "symbol_count": manifest["symbol_count"],
                        "intervals": manifest["intervals"],
                        "request_error_count": manifest["request_error_count"],
                        "freshness": freshness,
                    },
                )
            except (FileNotFoundError, ValueError) as exc:
                _record_step(steps, name="signal_candles", status="failed", error=exc)
    else:
        _record_step(
            steps,
            name="signal_candles",
            status="skipped",
            details={"reason": "collect_signal_candles=false"},
        )

    if account_fee_user_address:
        try:
            effective_account_fee_client = account_fee_client or funding_client
            if effective_account_fee_client is None:
                with TradeXyzClient() as client:
                    manifest = collect_trade_xyz_account_fee_snapshot(
                        data_dir=data_dir,
                        user_address=account_fee_user_address,
                        client=client,
                        snapshot_ts=generated,
                    )
            else:
                manifest = collect_trade_xyz_account_fee_snapshot(
                    data_dir=data_dir,
                    user_address=account_fee_user_address,
                    client=effective_account_fee_client,
                    snapshot_ts=generated,
                )
            _record_step(
                steps,
                name="account_fee",
                status="completed",
                manifest_path=data_dir / "manifests/trade_xyz_account_fee_manifest.json",
                details={
                    "status": manifest["status"],
                    "user_address_sha256": manifest["user_address_sha256"],
                    "available_fields": manifest["available_fields"],
                    "missing_fields": manifest["missing_fields"],
                    "parsed": manifest["parsed"],
                },
            )
        except ValueError as exc:
            _record_step(steps, name="account_fee", status="failed", error=exc)
    else:
        _record_step(
            steps,
            name="account_fee",
            status="skipped",
            details={"reason": "account_fee_user_address not provided"},
        )

    readiness = build_trade_xyz_data_readiness_manifest(
        data_dir=data_dir,
        generated_at=generated,
        allow_known_gaps=allow_known_gaps,
    )
    _record_step(
        steps,
        name="data_readiness",
        status="completed",
        manifest_path=data_dir / "manifests/trade_xyz_data_readiness_manifest.json",
        details={
            "decision": readiness["decision"],
            "backtest_data_ready": readiness["backtest_data_ready"],
            "fail_count": readiness["fail_count"],
            "known_gap_count": readiness["known_gap_count"],
        },
    )

    failed_steps = [item for item in steps if item["status"] == "failed"]
    bundle = {
        "schema_version": "trade_xyz_data_collection_bundle_manifest.v1",
        "generated_at": generated.isoformat(),
        "data_dir": str(data_dir),
        "registry_path": str(registry_path) if registry_path is not None else None,
        "raw_quotes_root": str(effective_raw_quotes_root),
        "requested_symbols": [item.upper() for item in symbols] if symbols else None,
        "min_days": min_days,
        "max_gap_minutes": max_gap_minutes,
        "traceable_only": traceable_only,
        "max_oracle_lag_minutes": max_oracle_lag_minutes,
        "funding_start_time_ms": effective_funding_start_time_ms,
        "funding_end_time_ms": effective_funding_end_time_ms,
        "auto_funding_window": auto_funding_window,
        "funding_window_source": funding_window_source,
        "account_fee_user_address_provided": bool(account_fee_user_address),
        "collect_signal_candles": collect_signal_candles,
        "signal_candle_intervals": signal_candle_intervals or ["30m", "4h", "1d", "3d"],
        "signal_candle_period_days": signal_candle_period_days,
        "signal_candle_max_age_hours": signal_candle_max_age_hours,
        "collect_real_market_reference_data": collect_real_market_reference_data,
        "allow_known_gaps": allow_known_gaps,
        "status": "completed_with_errors" if failed_steps else "completed",
        "failed_step_count": len(failed_steps),
        "readiness_decision": readiness["decision"],
        "backtest_data_ready": readiness["backtest_data_ready"],
        "steps": steps,
    }
    write_json(data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json", bundle)
    return bundle
