from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import csv
import hashlib
from pathlib import Path
from typing import Any

import polars as pl

from sis.crypto_perp.backtest_candidate_pack import _select_pairs
from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_PROJECT_FUNDING_RATE,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
)
from sis.crypto_perp.events import build_market_window_event
from sis.crypto_perp.funding_source import (
    HISTORICAL_FUNDING_SOURCE_NOT_AVAILABLE,
    build_funding_source_status,
)
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.source_availability import build_source_availability
from sis.crypto_perp.ticker_source import (
    TICKER_SOURCE_MISSING_BEFORE_CUTOFF,
    build_ticker_source_status,
)
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows


REAL_MARKET_NO_CASH_PRODUCER = "crypto-perp-real-market-no-cash-sample"
PUBLIC_CANDLES_ONLY_GAP = "PUBLIC_MARKET_CANDLES_ONLY"
LOCAL_SIMULATION_GAP = "LOCAL_SIMULATION_ONLY"
NOT_ACTUAL_CASH_GAP = "NOT_ACTUAL_CASH"
HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE = "HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE"
TICKER_COVERED_EVENT_COUNT_BELOW_TARGET = "TICKER_COVERED_EVENT_COUNT_BELOW_TARGET"


@dataclass(frozen=True)
class RealMarketNoCashSampleResult:
    event_count: int
    outcome_count: int
    source_availability_count: int
    ticker_available_count: int
    funding_available_count: int
    rows_path: Path
    guard_path: Path
    manifest_path: Path
    input_csv_path: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _json_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported JSON artifact payload: {type(value)!r}")


def _artifact_ref(path: Path, *, schema_version: str) -> dict[str, str]:
    return {
        "path": path.as_posix(),
        "sha256": _sha256_file(path).removeprefix("sha256:"),
        "schema_version": schema_version,
    }


def _utc_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(microsecond=0)


def _decimal_text(value: object) -> str:
    return str(Decimal(str(value)))


def _source_root_candle_rows(source_root: Path, symbol: str) -> list[dict[str, str]]:
    paths = sorted((source_root / "data" / "candles_5m").glob("date=*/candles.parquet"))
    if not paths:
        raise ValueError(f"source_root has no candles_5m parquet files: {source_root}")
    frames = [pl.read_parquet(path) for path in paths]
    frame = (
        pl.concat(frames, how="vertical_relaxed")
        .with_columns(pl.col("symbol").cast(pl.Utf8).str.to_uppercase())
        .filter(pl.col("symbol") == symbol.upper())
        .sort("ts")
    )
    if frame.is_empty():
        raise ValueError(f"source_root has no candle rows for symbol {symbol}: {source_root}")
    rows: list[dict[str, str]] = []
    for row in frame.iter_rows(named=True):
        ts = _utc_from_ms(int(row["ts"]))
        rows.append(
            {
                "ts": serialize_utc_z(ts),
                "available_at": serialize_utc_z(ts),
                "symbol": str(row["symbol"]),
                "open": _decimal_text(row["open"]),
                "high": _decimal_text(row["high"]),
                "low": _decimal_text(row["low"]),
                "close": _decimal_text(row["close"]),
                "base_vol": _decimal_text(row["base_vol"]),
                "quote_vol": _decimal_text(row["quote_vol"]),
            }
        )
    return rows


def _input_csv_rows(input_csv: Path, symbol: str) -> list[dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "ts",
            "available_at",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "base_vol",
            "quote_vol",
        }
        missing = sorted(required.difference(reader.fieldnames or []))
        if missing:
            raise ValueError("input_csv missing columns: " + ",".join(missing))
        rows = [dict(row) for row in reader if row["symbol"].upper() == symbol.upper()]
    rows.sort(key=lambda row: ensure_utc_aware("ts", row["ts"]))
    if not rows:
        raise ValueError(f"input_csv has no rows for symbol {symbol}: {input_csv}")
    return rows


def _write_input_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ts",
        "available_at",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "base_vol",
        "quote_vol",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _eligible_indices(row_count: int, lookback_bars: int, horizon_bars: int) -> list[int]:
    first = lookback_bars
    last = row_count - horizon_bars - 1
    if last < first:
        raise ValueError(
            "not enough rows for lookback and horizon: "
            f"row_count={row_count} lookback_bars={lookback_bars} horizon_bars={horizon_bars}"
        )
    return list(range(first, last + 1))


def _evenly_spaced_indices(eligible: list[int], target_event_count: int) -> list[int]:
    if len(eligible) < target_event_count:
        raise ValueError(
            "not enough eligible event windows: "
            f"eligible={len(eligible)} target_event_count={target_event_count}"
        )
    if target_event_count == 1:
        return [eligible[0]]
    return [
        eligible[round(i * (len(eligible) - 1) / (target_event_count - 1))]
        for i in range(target_event_count)
    ]


def _selected_indices(
    row_count: int, target_event_count: int, lookback_bars: int, horizon_bars: int
) -> list[int]:
    return _evenly_spaced_indices(
        _eligible_indices(row_count, lookback_bars, horizon_bars), target_event_count
    )


def _price_window(
    rows: list[dict[str, str]], index: int, horizon_bars: int
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    reference = Decimal(rows[index]["close"])
    horizon = rows[index + 1 : index + horizon_bars + 1]
    close = Decimal(horizon[-1]["close"])
    high = max(Decimal(row["high"]) for row in horizon)
    low = min(Decimal(row["low"]) for row in horizon)
    return reference, close, high, low


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    return Decimal(raw)


def _decimal_json(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def _spread_bps_from_ticker(metadata: dict[str, Any]) -> str | None:
    bid = _decimal_or_none(metadata.get("bid_px"))
    ask = _decimal_or_none(metadata.get("ask_px"))
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / Decimal("2")
    return _decimal_json((ask - bid) / mid * Decimal("10000"))


def _mark_index_basis_bps_from_ticker(metadata: dict[str, Any]) -> str | None:
    mark = _decimal_or_none(metadata.get("mark_px"))
    index = _decimal_or_none(metadata.get("index_px"))
    if mark is None or index is None or index == 0:
        return None
    return _decimal_json((mark - index) / index * Decimal("10000"))


def _event_with_ticker_context(event, metadata: dict[str, Any]):
    updates: dict[str, str] = {}
    spread_bps = _spread_bps_from_ticker(metadata)
    mark_index_basis_bps = _mark_index_basis_bps_from_ticker(metadata)
    funding_rate = _decimal_json(_decimal_or_none(metadata.get("funding_rate")))
    open_interest = _decimal_json(_decimal_or_none(metadata.get("open_interest")))
    if spread_bps is not None:
        updates["spread_bps"] = spread_bps
    if mark_index_basis_bps is not None:
        updates["mark_index_basis_bps"] = mark_index_basis_bps
    if funding_rate is not None:
        updates["funding_rate"] = funding_rate
    if open_interest is not None:
        updates["open_interest_raw"] = open_interest
    if not updates:
        return event
    return event.model_copy(
        update={"features_at_detection": event.features_at_detection.model_copy(update=updates)}
    )


def _event_with_funding_context(event, metadata: dict[str, Any]):
    funding_rate = _decimal_json(_decimal_or_none(metadata.get("funding_rate")))
    if funding_rate is None:
        return event
    return event.model_copy(
        update={
            "features_at_detection": event.features_at_detection.model_copy(
                update={"funding_rate": funding_rate}
            )
        }
    )


def _real_market_ticker_reason(reason: str) -> str:
    if reason == TICKER_SOURCE_MISSING_BEFORE_CUTOFF:
        return HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE
    return reason


def _candidate_event(
    materialized_csv: Path,
    symbol: str,
    cutoff: datetime,
    lookback_minutes: int,
    source_refs: list[dict[str, str]],
):
    return build_market_window_event(
        input_csv=materialized_csv,
        symbol=symbol,
        information_cutoff_at=cutoff,
        lookback_minutes=lookback_minutes,
        source_refs=source_refs,
        producer_command=REAL_MARKET_NO_CASH_PRODUCER,
    )


def _ticker_covered_indices(
    *,
    rows: list[dict[str, str]],
    candidate_indices: list[int],
    materialized_csv: Path,
    symbol: str,
    source_refs: list[dict[str, str]],
    ticker_source_root: Path | None,
    ticker_max_staleness_seconds: int,
    lookback_minutes: int,
) -> tuple[list[int], set[str]]:
    if ticker_source_root is None:
        return [], {HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE}
    covered: list[int] = []
    missing_reasons: set[str] = set()
    for row_index in candidate_indices:
        cutoff = ensure_utc_aware("information_cutoff_at", rows[row_index]["available_at"])
        event = _candidate_event(materialized_csv, symbol, cutoff, lookback_minutes, source_refs)
        status = build_ticker_source_status(
            event=event,
            source_root=ticker_source_root,
            max_staleness_seconds=ticker_max_staleness_seconds,
        )
        if status.row_count > 0:
            covered.append(row_index)
        else:
            missing_reasons.add(_real_market_ticker_reason(status.reason))
    return covered, missing_reasons


def write_real_market_no_cash_sample(
    *,
    out_dir: Path,
    created_at: datetime | str,
    symbol: str = "BTCUSDT",
    source_root: Path | None = None,
    input_csv: Path | None = None,
    ticker_source_root: Path | None = None,
    ticker_max_staleness_seconds: int = 900,
    require_ticker_coverage: bool = False,
    target_event_count: int = 30,
    lookback_minutes: int = 60,
    horizon_minutes: int = 60,
    interval_minutes: int = 5,
    min_events_for_stability: int = 30,
    fold_count: int = 2,
    notional_usd: Decimal = Decimal("100"),
) -> RealMarketNoCashSampleResult:
    if source_root is None and input_csv is None:
        raise ValueError("source_root or input_csv is required")
    if source_root is not None and input_csv is not None:
        raise ValueError("provide only one of source_root or input_csv")
    if ticker_max_staleness_seconds < 0:
        raise ValueError("ticker_max_staleness_seconds must be non-negative")
    if target_event_count < 1:
        raise ValueError("target_event_count must be positive")
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be positive")
    if lookback_minutes < interval_minutes or horizon_minutes < interval_minutes:
        raise ValueError("lookback_minutes and horizon_minutes must be at least interval_minutes")
    if fold_count < 2:
        raise ValueError("fold_count must be at least 2 for an estimable PBO guard")

    created = ensure_utc_aware("created_at", created_at)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = (
        _source_root_candle_rows(source_root, symbol)
        if source_root is not None
        else _input_csv_rows(input_csv or Path(), symbol)
    )
    effective_ticker_source_root = ticker_source_root or source_root
    materialized_csv = out_dir / "input" / f"{symbol.upper()}_{interval_minutes}m_public_market.csv"
    _write_input_csv(materialized_csv, rows)

    lookback_bars = max(1, lookback_minutes // interval_minutes)
    horizon_bars = max(1, horizon_minutes // interval_minutes)
    source_refs = [
        _artifact_ref(
            materialized_csv, schema_version="bitget_public_candles_5m.input_projection.v1"
        )
    ]
    if source_root is not None:
        manifest = source_root.parent / "bitget_public_source_refresh_manifest.json"
        if manifest.exists():
            source_refs.append(
                _artifact_ref(
                    manifest, schema_version="strategy_idea_candidates_bitget_public_source.v1"
                )
            )
    candidate_indices = _eligible_indices(len(rows), lookback_bars, horizon_bars)
    ticker_covered_candidate_count: int | None = None
    ticker_coverage_missing_reasons: set[str] = set()
    if require_ticker_coverage:
        covered_indices, ticker_coverage_missing_reasons = _ticker_covered_indices(
            rows=rows,
            candidate_indices=candidate_indices,
            materialized_csv=materialized_csv,
            symbol=symbol,
            source_refs=source_refs,
            ticker_source_root=effective_ticker_source_root,
            ticker_max_staleness_seconds=ticker_max_staleness_seconds,
            lookback_minutes=lookback_minutes,
        )
        ticker_covered_candidate_count = len(covered_indices)
        if ticker_covered_candidate_count < target_event_count:
            reasons = ",".join(sorted(ticker_coverage_missing_reasons)) or "UNKNOWN"
            raise ValueError(
                f"{TICKER_COVERED_EVENT_COUNT_BELOW_TARGET}: "
                f"covered={ticker_covered_candidate_count} target={target_event_count} "
                f"missing_reasons={reasons}"
            )
        indices = _evenly_spaced_indices(covered_indices, target_event_count)
    else:
        indices = _evenly_spaced_indices(candidate_indices, target_event_count)

    events = []
    outcomes = []
    for sample_index, row_index in enumerate(indices):
        cutoff = ensure_utc_aware("information_cutoff_at", rows[row_index]["available_at"])
        event = build_market_window_event(
            input_csv=materialized_csv,
            symbol=symbol,
            information_cutoff_at=cutoff,
            lookback_minutes=lookback_minutes,
            source_refs=source_refs,
            producer_command=REAL_MARKET_NO_CASH_PRODUCER,
        )
        reference, close, high, low = _price_window(rows, row_index, horizon_bars)
        settled_at = ensure_utc_aware("settled_at", rows[row_index + horizon_bars]["available_at"])
        outcome = build_outcome(
            event_id=event.event_id,
            settled_at=settled_at,
            horizons=[
                OutcomePriceWindow(
                    horizon_minutes=horizon_minutes,
                    matured=True,
                    reference_price=reference,
                    close_price=close,
                    high_price=high,
                    low_price=low,
                    market_return=Decimal("0"),
                )
            ],
            known_gaps=[PUBLIC_CANDLES_ONLY_GAP, LOCAL_SIMULATION_GAP, NOT_ACTUAL_CASH_GAP],
            source_refs=source_refs,
            producer_command=REAL_MARKET_NO_CASH_PRODUCER,
        )
        ticker_status = None
        funding_status = None
        if effective_ticker_source_root is not None:
            ticker_status = build_ticker_source_status(
                event=event,
                source_root=effective_ticker_source_root,
                max_staleness_seconds=ticker_max_staleness_seconds,
            )
            funding_status = build_funding_source_status(
                event=event,
                source_root=effective_ticker_source_root,
            )
            if ticker_status.row_count > 0:
                event = _event_with_ticker_context(event, ticker_status.metadata)
            if funding_status.row_count > 0:
                event = _event_with_funding_context(event, funding_status.metadata)
        event_path = out_dir / "events" / f"event_{sample_index:03d}.json"
        outcome_path = out_dir / "outcomes" / f"outcome_{sample_index:03d}.json"
        write_json_artifact(event_path, _json_payload(event))
        write_json_artifact(outcome_path, _json_payload(outcome))
        events.append((event_path, event, ticker_status, funding_status))
        outcomes.append((outcome_path, outcome))

    source_paths: list[str] = []
    missing_ticker_reasons: set[str] = set()
    missing_funding_reasons: set[str] = set()
    ticker_available_count = 0
    funding_available_count = 0
    for index, (event_path, event, ticker_status, funding_status) in enumerate(events):
        row_counts = {"bars": indices[index] + 1, "outcome": 1}
        source_refs_for_availability = [
            _artifact_ref(event_path, schema_version="crypto_perp_event.v1"),
            _artifact_ref(outcomes[index][0], schema_version="crypto_perp_outcome.v1"),
        ]
        source_metadata: dict[str, dict[str, Any]] = {}
        source_reasons = {
            "books": "BOOKS_SOURCE_MISSING",
            "trades": "TRADES_SOURCE_MISSING",
            "replay": "REPLAY_SOURCE_MISSING",
        }
        if ticker_status is not None:
            ticker_reason = _real_market_ticker_reason(ticker_status.reason)
            row_counts["ticker"] = ticker_status.row_count
            source_refs_for_availability.extend(ticker_status.source_refs)
            source_metadata["ticker"] = ticker_status.metadata
            source_reasons["ticker"] = ticker_reason
            if ticker_status.row_count > 0:
                ticker_available_count += 1
            else:
                missing_ticker_reasons.add(ticker_reason)
        else:
            row_counts["ticker"] = 0
            source_reasons["ticker"] = HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE
            missing_ticker_reasons.add(HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE)

        if funding_status is not None:
            row_counts["funding"] = funding_status.row_count
            source_refs_for_availability.extend(funding_status.source_refs)
            source_metadata["funding"] = funding_status.metadata
            source_reasons["funding"] = funding_status.reason
            if funding_status.row_count > 0:
                funding_available_count += 1
            else:
                missing_funding_reasons.add(funding_status.reason)
        else:
            row_counts["funding"] = 0
            source_reasons["funding"] = HISTORICAL_FUNDING_SOURCE_NOT_AVAILABLE
            missing_funding_reasons.add(HISTORICAL_FUNDING_SOURCE_NOT_AVAILABLE)
        source = build_source_availability(
            event=event,
            created_at=created,
            available_sources={"bars": True, "outcome": True},
            row_counts=row_counts,
            source_reasons=source_reasons,
            source_metadata=source_metadata,
            known_gaps=[PUBLIC_CANDLES_ONLY_GAP, LOCAL_SIMULATION_GAP, NOT_ACTUAL_CASH_GAP],
            source_refs=source_refs_for_availability,
            producer_command=REAL_MARKET_NO_CASH_PRODUCER,
        )
        source_path = out_dir / "source_availability" / f"source_{index:03d}.json"
        write_json_artifact(source_path, _json_payload(source))
        source_paths.append(source_path.as_posix())

    pairs, selection_gaps = _select_pairs(out_dir)
    rows_artifact = build_cost_aware_tournament_rows(
        outcomes=[pair.outcome for pair in pairs],
        created_at=created,
        notional_usd=notional_usd,
        fee_rate=CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
        funding_rate=CRYPTO_PERP_PROJECT_FUNDING_RATE,
        slippage_bps=CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
        known_gaps=[
            *selection_gaps,
            PUBLIC_CANDLES_ONLY_GAP,
            LOCAL_SIMULATION_GAP,
            NOT_ACTUAL_CASH_GAP,
        ],
        producer_command=REAL_MARKET_NO_CASH_PRODUCER,
    )
    rows_path = out_dir / "aggregate" / "tournament_rows_v2.json"
    write_json_artifact(rows_path, _json_payload(rows_artifact))
    guard = build_bias_guard(
        rows=rows_artifact.rows,
        created_at=created,
        min_events_for_pbo=min_events_for_stability,
        fold_count=fold_count,
        known_gaps=[PUBLIC_CANDLES_ONLY_GAP, LOCAL_SIMULATION_GAP, NOT_ACTUAL_CASH_GAP],
        source_refs=[_artifact_ref(rows_path, schema_version="crypto_perp_tournament_rows.v2")],
        producer_command=REAL_MARKET_NO_CASH_PRODUCER,
    )
    guard_path = out_dir / "aggregate" / "bias_guard.json"
    write_json_artifact(guard_path, _json_payload(guard))
    manifest = {
        "schema_version": "crypto_perp_real_market_no_cash_sample.v1",
        "created_at": serialize_utc_z(created),
        "producer": {"tool": "sis", "command": REAL_MARKET_NO_CASH_PRODUCER},
        "symbol": symbol.upper(),
        "target_event_count": target_event_count,
        "event_count": len(pairs),
        "outcome_count": len(pairs),
        "source_availability_count": len(source_paths),
        "selection_policy": (
            "time_evenly_spaced_before_outcome; no outcome-favorable filtering; "
            f"require_ticker_coverage={str(require_ticker_coverage).lower()}"
        ),
        "source_coverage": {
            "ticker_available_count": ticker_available_count,
            "funding_available_count": funding_available_count,
            "require_ticker_coverage": require_ticker_coverage,
            "ticker_covered_candidate_count": ticker_covered_candidate_count,
            "ticker_source_root": effective_ticker_source_root.as_posix()
            if effective_ticker_source_root is not None
            else None,
            "funding_source_root": effective_ticker_source_root.as_posix()
            if effective_ticker_source_root is not None
            else None,
            "ticker_max_staleness_seconds": ticker_max_staleness_seconds,
        },
        "known_gaps": list(
            dict.fromkeys(
                [
                    PUBLIC_CANDLES_ONLY_GAP,
                    *sorted(missing_ticker_reasons),
                    *sorted(missing_funding_reasons),
                    "BOOKS_SOURCE_MISSING",
                    "TRADES_SOURCE_MISSING",
                    "REPLAY_SOURCE_MISSING",
                    LOCAL_SIMULATION_GAP,
                    NOT_ACTUAL_CASH_GAP,
                ]
            )
        ),
        "non_goal_flags": {
            "paper_permission_granted": False,
            "actual_cash_used": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "profit_proven": False,
            "real_market_public_source_used": True,
            "fixture_only": False,
        },
        "artifact_paths": {
            "input_csv": materialized_csv.as_posix(),
            "tournament_rows_v2": rows_path.as_posix(),
            "bias_guard": guard_path.as_posix(),
            "source_availability": source_paths,
        },
    }
    manifest_path = out_dir / "selection_manifest.json"
    write_json_artifact(manifest_path, manifest)
    return RealMarketNoCashSampleResult(
        event_count=len(pairs),
        outcome_count=len(pairs),
        source_availability_count=len(source_paths),
        ticker_available_count=ticker_available_count,
        funding_available_count=funding_available_count,
        rows_path=rows_path,
        guard_path=guard_path,
        manifest_path=manifest_path,
        input_csv_path=materialized_csv,
    )
