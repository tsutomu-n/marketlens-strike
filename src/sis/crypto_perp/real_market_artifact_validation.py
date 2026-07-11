from __future__ import annotations

import csv
from datetime import timedelta
from decimal import Decimal
import hashlib
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.events import CryptoPerpEvent, build_market_window_event
from sis.crypto_perp.funding_source import build_funding_source_status
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.outcomes import (
    CryptoPerpOutcome,
    OutcomePriceWindow,
    build_outcome,
)
from sis.crypto_perp.real_market_candle_validation import (
    validate_candle_rows,
    validate_signal_lookback_window,
)
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability
from sis.crypto_perp.ticker_source import build_ticker_source_status


PUBLIC_CANDLE_SCHEMA_VERSION = "bitget_public_candles_5m.input_projection.v1"
REAL_MARKET_NO_CASH_PRODUCER = "crypto-perp-real-market-no-cash-sample"


def _is_public_market_event(event: CryptoPerpEvent) -> bool:
    return event.event_family == "market_window_v1"


def _normalized_sha256(value: str) -> str:
    normalized = value.removeprefix("sha256:").lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("SOURCE_REF_SHA256_INVALID")
    return normalized


def _resolve_source_path(path: str, data_dir: Path) -> Path:
    raw = Path(path)
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, data_dir / raw]
    existing = [candidate for candidate in candidates if candidate.is_file()]
    if not existing:
        raise ValueError(f"SOURCE_REF_FILE_MISSING: {path}")
    return existing[0]


def _ref_value(ref: Any, key: str) -> str:
    if isinstance(ref, Mapping):
        return str(ref.get(key, ""))
    return str(getattr(ref, key))


def validate_source_ref_files(refs: list[Any], data_dir: Path) -> None:
    for ref in refs:
        path = _ref_value(ref, "path")
        resolved = _resolve_source_path(path, data_dir)
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual != _normalized_sha256(_ref_value(ref, "sha256")):
            raise ValueError(f"SOURCE_REF_SHA256_MISMATCH: {path}")


def _public_candle_ref(refs: list[Any]) -> Any:
    matches = [ref for ref in refs if ref.schema_version == PUBLIC_CANDLE_SCHEMA_VERSION]
    if len(matches) != 1:
        raise ValueError("PUBLIC_CANDLE_SOURCE_REF_MISSING_OR_AMBIGUOUS")
    return matches[0]


def _csv_rows(path: Path, symbol: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {"ts", "available_at", "symbol", "open", "high", "low", "close", "quote_vol"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError("PUBLIC_CANDLE_SOURCE_COLUMNS_MISSING: " + ",".join(missing))
        rows = [dict(row) for row in reader if row["symbol"] == symbol]
    if len(rows) < 2:
        raise ValueError("PUBLIC_CANDLE_SOURCE_ROWS_INSUFFICIENT")
    rows.sort(key=lambda row: ensure_utc_aware("ts", row["ts"]))
    return rows


def _interval_minutes(rows: list[dict[str, str]], signal_index: int) -> int:
    if signal_index < 1:
        raise ValueError("PUBLIC_CANDLE_LOOKBACK_ROWS_INSUFFICIENT")
    current = ensure_utc_aware("ts", rows[signal_index]["ts"])
    previous = ensure_utc_aware("ts", rows[signal_index - 1]["ts"])
    seconds = int((current - previous).total_seconds())
    if seconds <= 0 or seconds % 60:
        raise ValueError("PUBLIC_CANDLE_INTERVAL_INVALID")
    return seconds // 60


def _signal_index(rows: list[dict[str, str]], event: CryptoPerpEvent) -> int:
    eligible = [
        index
        for index, row in enumerate(rows)
        if ensure_utc_aware("available_at", row["available_at"]) <= event.information_cutoff_at
    ]
    if not eligible:
        raise ValueError(f"PUBLIC_CANDLE_SIGNAL_ROW_MISSING: {event.event_id}")
    index = eligible[-1]
    available_at = ensure_utc_aware("available_at", rows[index]["available_at"])
    if available_at != event.information_cutoff_at:
        raise ValueError(f"PUBLIC_CANDLE_SIGNAL_CUTOFF_MISMATCH: {event.event_id}")
    return index


def _validate_event_from_candles(
    event: CryptoPerpEvent,
    source_path: Path,
    source_ref_path: str,
    rows: list[dict[str, str]],
    signal_index: int,
    interval_minutes: int,
) -> None:
    lookback_minutes = event.capture_request.duration_minutes
    if lookback_minutes % interval_minutes:
        raise ValueError(f"EVENT_LOOKBACK_INTERVAL_MISMATCH: {event.event_id}")
    validate_signal_lookback_window(
        rows, signal_index, lookback_minutes // interval_minutes, interval_minutes
    )
    expected = build_market_window_event(
        input_csv=source_path,
        symbol=event.native_symbol,
        information_cutoff_at=event.information_cutoff_at,
        lookback_minutes=lookback_minutes,
    )
    expected_event_id = stable_hash(
        [
            "crypto-perp-market-window-event",
            event.native_symbol,
            serialize_utc_z(event.information_cutoff_at),
            stable_hash(
                [Path(source_ref_path).as_posix(), source_path.read_text(encoding="utf-8")]
            ),
        ]
    )
    if event.event_id != expected_event_id:
        raise ValueError(f"EVENT_SOURCE_IDENTITY_MISMATCH: {event.event_id}")
    expected_artifact_id = stable_hash(
        ["crypto-perp-market-window-event-artifact", expected_event_id]
    )
    if event.artifact_id != expected_artifact_id:
        raise ValueError(f"EVENT_ARTIFACT_IDENTITY_MISMATCH: {event.event_id}")
    candle_feature_fields = (
        "return_15m",
        "return_60m",
        "return_74h",
        "recent_turnover",
        "previous_turnover",
        "turnover_impulse",
        "robust_return_z",
        "turnover_percentile",
    )
    for field in candle_feature_fields:
        if getattr(event.features_at_detection, field) != getattr(
            expected.features_at_detection, field
        ):
            raise ValueError(f"EVENT_CANDLE_FEATURE_MISMATCH: {event.event_id}:{field}")
    expected_config_hash = stable_hash(["market-window-csv", lookback_minutes, interval_minutes])
    if event.detector_config_hash != expected_config_hash:
        raise ValueError(f"EVENT_DETECTOR_CONFIG_MISMATCH: {event.event_id}")


def _validate_outcome_from_candles(
    event: CryptoPerpEvent,
    outcome: CryptoPerpOutcome,
    rows: list[dict[str, str]],
    signal_index: int,
    interval_minutes: int,
) -> tuple[str, str, int]:
    matured = [horizon for horizon in outcome.horizons if horizon.matured]
    if len(matured) != 1:
        raise ValueError(f"MATURED_HORIZON_COUNT_NOT_ONE: {event.event_id}")
    horizon = matured[0]
    if horizon.horizon_minutes % interval_minutes:
        raise ValueError(f"OUTCOME_HORIZON_INTERVAL_MISMATCH: {event.event_id}")
    horizon_bars = horizon.horizon_minutes // interval_minutes
    entry_index = signal_index + 1
    while entry_index < len(rows):
        entry_candidate = ensure_utc_aware("entry_candidate", rows[entry_index]["ts"])
        if entry_candidate > event.information_cutoff_at:
            break
        entry_index += 1
    execution_rows = rows[entry_index : entry_index + horizon_bars]
    if len(execution_rows) != horizon_bars:
        raise ValueError(f"OUTCOME_EXECUTION_ROWS_INSUFFICIENT: {event.event_id}")
    interval = timedelta(minutes=interval_minutes)
    entry_at = ensure_utc_aware("entry_at", execution_rows[0]["ts"])
    if entry_at != event.information_cutoff_at + interval:
        raise ValueError(f"OUTCOME_ENTRY_TIME_MISMATCH: {event.event_id}")
    for offset, row in enumerate(execution_rows):
        if ensure_utc_aware("execution_row_at", row["ts"]) != entry_at + interval * offset:
            raise ValueError(f"OUTCOME_EXECUTION_WINDOW_NOT_CONTIGUOUS: {event.event_id}")
    settled_at = entry_at + interval * horizon_bars
    if outcome.settled_at != settled_at:
        raise ValueError(f"OUTCOME_SETTLED_AT_MISMATCH: {event.event_id}")
    expected = build_outcome(
        event_id=event.event_id,
        settled_at=settled_at,
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=horizon.horizon_minutes,
                matured=True,
                reference_price=Decimal(execution_rows[0]["open"]),
                close_price=Decimal(execution_rows[-1]["close"]),
                high_price=max(Decimal(row["high"]) for row in execution_rows),
                low_price=min(Decimal(row["low"]) for row in execution_rows),
                market_return=Decimal("0"),
            )
        ],
    )
    if horizon != expected.horizons[0]:
        raise ValueError(f"OUTCOME_CANDLE_VALUE_MISMATCH: {event.event_id}")
    if outcome.outcome_id != expected.outcome_id:
        raise ValueError(f"OUTCOME_SOURCE_IDENTITY_MISMATCH: {event.event_id}")
    if outcome.artifact_id != expected.artifact_id:
        raise ValueError(f"OUTCOME_ARTIFACT_IDENTITY_MISMATCH: {event.event_id}")
    return serialize_utc_z(entry_at), serialize_utc_z(settled_at), horizon.horizon_minutes


def validate_public_market_pair(
    *, event: CryptoPerpEvent, outcome: CryptoPerpOutcome, data_dir: Path
) -> tuple[str, str, int] | None:
    if not _is_public_market_event(event):
        return None
    event_ref = _public_candle_ref(event.source_refs)
    outcome_ref = _public_candle_ref(outcome.source_refs)
    if event_ref.path != outcome_ref.path or _normalized_sha256(
        event_ref.sha256
    ) != _normalized_sha256(outcome_ref.sha256):
        raise ValueError(f"EVENT_OUTCOME_SOURCE_REF_MISMATCH: {event.event_id}")
    validate_source_ref_files([*event.source_refs, *outcome.source_refs], data_dir)
    source_path = _resolve_source_path(event_ref.path, data_dir)
    rows = _csv_rows(source_path, event.native_symbol)
    signal_index = _signal_index(rows, event)
    interval_minutes = _interval_minutes(rows, signal_index)
    validate_candle_rows(rows, interval_minutes)
    _validate_event_from_candles(
        event, source_path, event_ref.path, rows, signal_index, interval_minutes
    )
    return _validate_outcome_from_candles(event, outcome, rows, signal_index, interval_minutes)


def validate_selection_manifest(
    *, data_dir: Path, pairs: list[Any], execution_windows: dict[str, tuple[str, str, int]]
) -> None:
    public_pairs = [pair for pair in pairs if _is_public_market_event(pair.event)]
    if not public_pairs:
        return
    path = data_dir / "selection_manifest.json"
    if not path.is_file():
        raise ValueError("SELECTION_MANIFEST_MISSING")
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "crypto_perp_real_market_no_cash_sample.v1":
        raise ValueError("SELECTION_MANIFEST_SCHEMA_INVALID")
    expected_events = sorted(pair.event.event_id for pair in pairs)
    expected_outcomes = sorted(pair.outcome.artifact_id for pair in pairs)
    if payload.get("event_set") != expected_events:
        raise ValueError("SELECTION_MANIFEST_EVENT_SET_MISMATCH")
    if payload.get("outcome_set") != expected_outcomes:
        raise ValueError("SELECTION_MANIFEST_OUTCOME_SET_MISMATCH")
    if payload.get("event_count") != len(pairs) or payload.get("outcome_count") != len(pairs):
        raise ValueError("SELECTION_MANIFEST_COUNT_MISMATCH")
    raw_windows = payload.get("execution_windows")
    if not isinstance(raw_windows, list) or len(raw_windows) != len(pairs):
        raise ValueError("SELECTION_MANIFEST_EXECUTION_WINDOW_COUNT_MISMATCH")
    actual: dict[str, tuple[str, str, str, int]] = {}
    for item in raw_windows:
        if not isinstance(item, dict):
            raise ValueError("SELECTION_MANIFEST_EXECUTION_WINDOW_INVALID")
        event_id = str(item.get("event_id", ""))
        if not event_id or event_id in actual:
            raise ValueError("SELECTION_MANIFEST_EXECUTION_WINDOW_EVENT_INVALID")
        actual[event_id] = (
            str(item.get("outcome_id", "")),
            str(item.get("entry_at", "")),
            str(item.get("settled_at", "")),
            int(item.get("horizon_minutes", 0)),
        )
    expected = {
        pair.event.event_id: (
            pair.outcome.outcome_id,
            execution_windows[pair.event.event_id][0],
            execution_windows[pair.event.event_id][1],
            execution_windows[pair.event.event_id][2],
        )
        for pair in pairs
    }
    if actual != expected:
        raise ValueError("SELECTION_MANIFEST_EXECUTION_WINDOW_MISMATCH")


def _source_root(path_value: object, data_dir: Path, field: str) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError(f"SELECTION_MANIFEST_{field.upper()}_MISSING")
    raw = Path(path_value)
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, data_dir / raw]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise ValueError(f"SELECTION_MANIFEST_{field.upper()}_NOT_FOUND")


def _status_by_id(source: CryptoPerpSourceAvailability) -> dict[str, Any]:
    statuses: dict[str, Any] = {str(status.source_id): status for status in source.source_statuses}
    expected_ids = {
        "event",
        "bars",
        "ticker",
        "funding",
        "trades",
        "books",
        "outcome",
        "replay",
        "cash_ledger",
        "live_measurement",
    }
    if len(statuses) != len(source.source_statuses) or set(statuses) != expected_ids:
        raise ValueError(f"SOURCE_AVAILABILITY_STATUS_SET_INVALID: {source.event_id}")
    return statuses


def _validate_source_availability_identity(
    event: CryptoPerpEvent, source: CryptoPerpSourceAvailability
) -> dict[str, Any]:
    if source.event_id != event.event_id:
        raise ValueError("SOURCE_AVAILABILITY_EVENT_ID_MISMATCH")
    if source.information_cutoff_at != event.information_cutoff_at:
        raise ValueError("SOURCE_AVAILABILITY_CUTOFF_MISMATCH")
    expected_artifact_id = stable_hash(
        [
            "crypto-perp-source-availability",
            source.event_id,
            serialize_utc_z(source.created_at),
            [status.model_dump(mode="json") for status in source.source_statuses],
            source.known_gaps,
        ]
    )
    if source.artifact_id != expected_artifact_id:
        raise ValueError(f"SOURCE_AVAILABILITY_IDENTITY_MISMATCH: {source.event_id}")
    statuses = _status_by_id(source)
    expected_depth = bool(statuses["books"].available)
    expected_trade_imbalance = bool(statuses["trades"].available)
    expected_cost = all(
        statuses[source_id].available for source_id in ("event", "bars", "ticker", "funding")
    )
    expected_cash = bool(
        statuses["cash_ledger"].available or statuses["live_measurement"].available
    )
    if (
        source.can_compute_depth != expected_depth
        or source.can_compute_ofi != expected_depth
        or source.can_compute_trade_sign_imbalance != expected_trade_imbalance
        or source.can_compute_cost_adjusted_estimate != expected_cost
        or source.can_compute_actual_cash != expected_cash
    ):
        raise ValueError(f"SOURCE_AVAILABILITY_DERIVED_FLAGS_MISMATCH: {source.event_id}")
    expected_summary = {
        "event_id": source.event_id,
        "available_source_count": sum(status.available for status in source.source_statuses),
        "known_gap_count": len(source.known_gaps),
        "can_compute_cost_adjusted_estimate": expected_cost,
        "can_compute_actual_cash": expected_cash,
        "can_compute_depth": expected_depth,
    }
    if source.summary != expected_summary:
        raise ValueError(f"SOURCE_AVAILABILITY_SUMMARY_MISMATCH: {source.event_id}")
    return statuses


def _ref_identity(ref: Mapping[str, str], data_dir: Path) -> tuple[str, str, str]:
    path = _resolve_source_path(str(ref.get("path", "")), data_dir).resolve().as_posix()
    return (
        path,
        _normalized_sha256(str(ref.get("sha256", ""))),
        str(ref.get("schema_version", "")),
    )


def _expected_refs_present(
    actual_refs: list[dict[str, str]],
    expected_refs: list[dict[str, str]],
    data_dir: Path,
) -> bool:
    actual = {_ref_identity(ref, data_dir) for ref in actual_refs}
    return all(_ref_identity(ref, data_dir) in actual for ref in expected_refs)


def _normalized_source_metadata(metadata: Mapping[str, Any], data_dir: Path) -> dict[str, Any]:
    normalized = dict(metadata)
    for key in ("manifest_path", "selected_parquet_path"):
        value = normalized.get(key)
        if isinstance(value, str) and value:
            normalized[key] = _resolve_source_path(value, data_dir).resolve().as_posix()
    return normalized


def _decimal_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except Exception:
        return False


def _validate_event_market_features(
    event: CryptoPerpEvent,
    ticker_metadata: Mapping[str, Any] | None,
    funding_metadata: Mapping[str, Any] | None,
) -> None:
    if ticker_metadata is None:
        spread = Decimal("0")
        basis = Decimal("0")
        ticker_funding: object = Decimal("0")
        open_interest: object = Decimal("0")
    else:
        bid = Decimal(str(ticker_metadata.get("bid_px", "0")))
        ask = Decimal(str(ticker_metadata.get("ask_px", "0")))
        mark = Decimal(str(ticker_metadata.get("mark_px", "0")))
        index = Decimal(str(ticker_metadata.get("index_px", "0")))
        if bid <= 0 or ask <= 0 or ask < bid or index <= 0:
            raise ValueError(f"TICKER_METADATA_PRICE_INVALID: {event.event_id}")
        spread = (ask - bid) / ((ask + bid) / Decimal("2")) * Decimal("10000")
        basis = (mark - index) / index * Decimal("10000")
        ticker_funding = ticker_metadata.get("funding_rate", Decimal("0"))
        open_interest = ticker_metadata.get("open_interest", Decimal("0"))
    funding = (
        funding_metadata.get("funding_rate", ticker_funding)
        if funding_metadata is not None
        else ticker_funding
    )
    expected = {
        "spread_bps": spread,
        "mark_index_basis_bps": basis,
        "funding_rate": funding,
        "open_interest_raw": open_interest,
    }
    for field, value in expected.items():
        if value is None or not _decimal_equal(getattr(event.features_at_detection, field), value):
            raise ValueError(f"EVENT_MARKET_FEATURE_MISMATCH: {event.event_id}:{field}")


def validate_public_source_availability(
    *,
    event: CryptoPerpEvent,
    source: CryptoPerpSourceAvailability,
    data_dir: Path,
) -> None:
    statuses = _validate_source_availability_identity(event, source)
    if (
        event.producer.command == "crypto-perp-no-cash-backtest-sample"
        and not _is_public_market_event(event)
    ):
        return
    validate_source_ref_files(source.source_refs, data_dir)
    if not _is_public_market_event(event):
        return
    manifest_path = data_dir / "selection_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("SELECTION_MANIFEST_MISSING")
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coverage = manifest.get("source_coverage")
    if not isinstance(coverage, Mapping):
        raise ValueError("SELECTION_MANIFEST_SOURCE_COVERAGE_INVALID")
    actual_ticker = statuses["ticker"]
    actual_funding = statuses["funding"]
    expected_ticker = None
    expected_funding = None
    if actual_ticker.available or (actual_ticker.row_count or 0) > 0:
        ticker_root = _source_root(
            coverage.get("ticker_source_root"), data_dir, "ticker_source_root"
        )
        max_staleness = coverage.get("ticker_max_staleness_seconds")
        if (
            not isinstance(max_staleness, int)
            or isinstance(max_staleness, bool)
            or max_staleness < 0
        ):
            raise ValueError("SELECTION_MANIFEST_TICKER_MAX_STALENESS_INVALID")
        expected_ticker = build_ticker_source_status(
            event=event,
            source_root=ticker_root,
            max_staleness_seconds=max_staleness,
        )
        if (
            actual_ticker.available != (expected_ticker.row_count > 0)
            or actual_ticker.row_count != expected_ticker.row_count
            or actual_ticker.reason != expected_ticker.reason
            or _normalized_source_metadata(actual_ticker.metadata, data_dir)
            != _normalized_source_metadata(expected_ticker.metadata, data_dir)
            or not _expected_refs_present(
                actual_ticker.source_refs, expected_ticker.source_refs, data_dir
            )
        ):
            raise ValueError(f"TICKER_SOURCE_STATUS_MISMATCH: {event.event_id}")
    if actual_funding.available or (actual_funding.row_count or 0) > 0:
        funding_root = _source_root(
            coverage.get("funding_source_root"), data_dir, "funding_source_root"
        )
        expected_funding = build_funding_source_status(event=event, source_root=funding_root)
        if (
            actual_funding.available != (expected_funding.row_count > 0)
            or actual_funding.row_count != expected_funding.row_count
            or actual_funding.reason != expected_funding.reason
            or _normalized_source_metadata(actual_funding.metadata, data_dir)
            != _normalized_source_metadata(expected_funding.metadata, data_dir)
            or not _expected_refs_present(
                actual_funding.source_refs, expected_funding.source_refs, data_dir
            )
        ):
            raise ValueError(f"FUNDING_SOURCE_STATUS_MISMATCH: {event.event_id}")
    _validate_event_market_features(
        event,
        expected_ticker.metadata
        if expected_ticker is not None and expected_ticker.row_count
        else None,
        expected_funding.metadata
        if expected_funding is not None and expected_funding.row_count
        else None,
    )
