from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import Any

from sis.crypto_perp.backtest_candidate_pack import _select_pairs
from sis.crypto_perp.bars import build_candle_bars, interval_to_milliseconds
from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_PROJECT_FUNDING_RATE,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
)
from sis.crypto_perp.events import CryptoPerpEvent, EventSourceRef, detect_event
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.heartbeat import MarketTickerSnapshot
from sis.crypto_perp.io import write_json_artifact
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.quality import validate_candle_series
from sis.crypto_perp.source_availability import build_source_availability
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows


NO_CASH_BACKTEST_SAMPLE_PRODUCER = "crypto-perp-no-cash-backtest-sample"
FIXTURE_GAP = "DOGFOOD_FIXTURE_NOT_REAL_MARKET_EVIDENCE"


@dataclass(frozen=True)
class NoCashBacktestSampleResult:
    event_count: int
    outcome_count: int
    generated_event_count: int
    source_availability_count: int
    rows_path: Path
    guard_path: Path
    manifest_path: Path


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_ref(kind: str, index: int) -> dict[str, str]:
    return {
        "path": f"dogfood_fixture/{kind}/{index:03d}.json",
        "sha256": _sha256_text(f"{kind}:{index}"),
        "schema_version": f"crypto_perp_{kind}_dogfood_fixture.v1",
    }


def _base_event() -> CryptoPerpEvent:
    base_ms = 1_710_000_000_000
    interval_ms = interval_to_milliseconds("15m")
    rows: list[dict[str, str]] = []
    closes = ["100"] * 591 + ["105"]
    turnovers = ["1000"] * 296 + ["1200"] * 296
    for index, close in enumerate(closes):
        rows.append(
            {
                "ts_open": str(base_ms + index * interval_ms),
                "open": "100",
                "high": str(max(Decimal("100"), Decimal(close)) + Decimal("1")),
                "low": "99",
                "close": close,
                "base_volume": "10",
                "quote_turnover": turnovers[index],
                "candle_type": "market",
                "interval": "15m",
            }
        )
    bars = build_candle_bars(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        candle_rows=rows,
        ts_ingested="2026-06-21T04:00:00Z",
        source_payload_sha256="c" * 64,
        now_ms=base_ms + (len(closes) + 2) * interval_ms,
    )
    ticker = MarketTickerSnapshot(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        ts_event=str(base_ms),
        ts_received=datetime(2026, 6, 21, 4, 0, tzinfo=timezone.utc),
        last_price="105",
        bid1_price="104.9",
        ask1_price="105.1",
        bid1_size="1",
        ask1_size="1",
        spread_bps="1.90476190",
        price_change_24h="0.05",
        volume_24h_base="100",
        turnover_24h_quote="10000",
        index_price="104",
        mark_price="105",
        funding_rate="0.0001",
        open_interest_raw="1234",
        open_interest_unit="base",
        source_payload_sha256="d" * 64,
    )
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=bars,
        ticker=ticker,
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="dogfood-universe-template",
        market_snapshot_id="dogfood-market-template",
        detector_config=EventDetectorConfig(),
    )
    if event is None:
        raise ValueError("dogfood fixture template did not produce an event")
    return event


def _fixture_return(index: int) -> Decimal:
    cycle = [
        Decimal("0.052"),
        Decimal("-0.041"),
        Decimal("0.034"),
        Decimal("-0.028"),
        Decimal("0.018"),
        Decimal("-0.016"),
        Decimal("0.006"),
        Decimal("-0.004"),
        Decimal("0.026"),
        Decimal("-0.023"),
    ]
    return cycle[index % len(cycle)]


def _outcome_return(event_return: Decimal, index: int) -> Decimal:
    if index % 10 in {3, 9}:
        return -event_return
    if abs(event_return) < Decimal("0.01"):
        return Decimal("0.0005") if event_return >= 0 else Decimal("-0.0005")
    return event_return * Decimal("0.80")


def _build_fixture_pair(
    *,
    template: CryptoPerpEvent,
    index: int,
    cutoff: datetime,
) -> tuple[CryptoPerpEvent, Any]:
    event_return = _fixture_return(index)
    family = (
        "market_window_v1"
        if abs(event_return) < Decimal("0.01")
        else ("fast_pump_1h_v1" if index % 2 else "slow_pump_74h_v1")
    )
    source_refs = [
        _source_ref("bars", index),
        _source_ref("ticker", index),
        _source_ref("funding", index),
    ]
    event_id = stable_hash(["no-cash-backtest-dogfood-event", index, serialize_utc_z(cutoff)])
    feature_update = {
        "return_15m": str(event_return / Decimal("4")),
        "return_60m": str(event_return),
        "return_74h": str(event_return),
        "turnover_impulse": str(Decimal("0.15") + Decimal(index % 7) / Decimal("100")),
        "robust_return_z": str(Decimal("3.0") + Decimal(index % 5) / Decimal("10")),
        "turnover_percentile": str(Decimal("0.90") + Decimal(index % 8) / Decimal("1000")),
        "spread_bps": "1.90476190",
        "funding_rate": "0.0001",
    }
    event = template.model_copy(
        update={
            "artifact_id": stable_hash(["no-cash-backtest-dogfood-event-artifact", event_id]),
            "created_at": cutoff,
            "producer": CryptoPerpProducer(command=NO_CASH_BACKTEST_SAMPLE_PRODUCER),
            "source_refs": [EventSourceRef.model_validate(ref) for ref in source_refs],
            "event_id": event_id,
            "event_family": family,
            "first_detected_at": cutoff,
            "information_cutoff_at": cutoff,
            "universe_snapshot_id": f"dogfood-universe-{index:03d}",
            "market_snapshot_id": f"dogfood-market-{index:03d}",
            "features_at_detection": template.features_at_detection.model_copy(
                update=feature_update
            ),
            "market_context": template.market_context.model_copy(
                update={
                    "btc_return": str(event_return / Decimal("4")),
                    "eth_return": str(event_return / Decimal("5")),
                    "cross_section_median_return": str(event_return / Decimal("6")),
                    "market_adjusted_return": str(event_return * Decimal("0.75")),
                }
            ),
        }
    )
    reference = Decimal("100") + Decimal(index % 11)
    raw_outcome = _outcome_return(event_return, index)
    close = reference * (Decimal("1") + raw_outcome)
    high = max(reference, close) * Decimal("1.010")
    low = min(reference, close) * Decimal("0.990")
    outcome = build_outcome(
        event_id=event.event_id,
        settled_at=cutoff + timedelta(minutes=90 + index),
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=reference,
                close_price=close,
                high_price=high,
                low_price=low,
                market_return=event_return / Decimal("5"),
                observed_high_low_order="HIGH_FIRST" if index % 2 == 0 else "LOW_FIRST",
            )
        ],
        known_gaps=[FIXTURE_GAP, "LOCAL_SIMULATION_ONLY", "NOT_ACTUAL_CASH"],
        source_refs=[_source_ref("outcome", index)],
        producer_command=NO_CASH_BACKTEST_SAMPLE_PRODUCER,
    )
    return event, outcome


def _json_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported JSON artifact payload: {type(value)!r}")


def _artifact_ref(path: Path, *, artifact_id: str, schema_version: str) -> dict[str, str]:
    return {
        "path": path.as_posix(),
        "sha256": f"sha256:{_sha256_text(artifact_id)}",
        "schema_version": schema_version,
    }


def write_no_cash_backtest_sample(
    *,
    data_dir: Path,
    out_dir: Path,
    created_at: datetime | str,
    target_event_count: int = 30,
    min_events_for_stability: int = 30,
    fold_count: int = 2,
    notional_usd: Decimal = Decimal("100"),
) -> NoCashBacktestSampleResult:
    if target_event_count < 1:
        raise ValueError("target_event_count must be positive")
    if fold_count < 2:
        raise ValueError("fold_count must be at least 2 for an estimable dogfood PBO guard")
    created = ensure_utc_aware("created_at", created_at)
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs, _ = _select_pairs(data_dir)
    missing_count = max(0, target_event_count - len(pairs))
    template = _base_event()
    base_cutoff = datetime(2026, 6, 21, 0, 0, tzinfo=timezone.utc)
    generated = 0
    start_index = 0
    existing_ids = {pair.event.event_id for pair in pairs}
    while generated < missing_count:
        index = start_index
        start_index += 1
        cutoff = base_cutoff + timedelta(hours=index * 3)
        event, outcome = _build_fixture_pair(template=template, index=index, cutoff=cutoff)
        if event.event_id in existing_ids:
            continue
        existing_ids.add(event.event_id)
        write_json_artifact(out_dir / "events" / f"event_{index:03d}.json", _json_payload(event))
        write_json_artifact(
            out_dir / "outcomes" / f"outcome_{index:03d}.json", _json_payload(outcome)
        )
        generated += 1

    pairs, selection_gaps = _select_pairs(data_dir)
    source_paths: list[str] = []
    for index, pair in enumerate(pairs):
        cutoff_ms = int(pair.event.information_cutoff_at.timestamp() * 1000)
        source = build_source_availability(
            event=pair.event,
            created_at=created,
            available_sources={"bars": True, "ticker": True, "funding": True, "outcome": True},
            row_counts={"bars": 592, "ticker": 1, "funding": 1, "outcome": 1},
            source_metadata={
                "bars": {"coverage_end_ms": cutoff_ms, "source_class": "dogfood_fixture"},
                "ticker": {"coverage_end_ms": cutoff_ms, "source_class": "dogfood_fixture"},
                "funding": {"coverage_end_ms": cutoff_ms, "source_class": "dogfood_fixture"},
            },
            source_reasons={
                "books": "BOOKS_SOURCE_MISSING",
                "trades": "TRADES_SOURCE_MISSING",
                "replay": "REPLAY_SOURCE_MISSING",
            },
            known_gaps=[FIXTURE_GAP, "LOCAL_SIMULATION_ONLY", "NOT_ACTUAL_CASH"],
            source_refs=[
                _artifact_ref(
                    pair.outcome_path,
                    artifact_id=pair.outcome.artifact_id,
                    schema_version=pair.outcome.schema_version,
                )
            ],
            producer_command=NO_CASH_BACKTEST_SAMPLE_PRODUCER,
        )
        source_path = out_dir / "source_availability" / f"source_{index:03d}.json"
        write_json_artifact(source_path, _json_payload(source))
        source_paths.append(source_path.as_posix())

    rows = build_cost_aware_tournament_rows(
        outcomes=[pair.outcome for pair in pairs],
        created_at=created,
        notional_usd=notional_usd,
        fee_rate=CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
        funding_rate=CRYPTO_PERP_PROJECT_FUNDING_RATE,
        slippage_bps=CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
        known_gaps=[*selection_gaps, FIXTURE_GAP, "LOCAL_SIMULATION_ONLY", "NOT_ACTUAL_CASH"],
        producer_command=NO_CASH_BACKTEST_SAMPLE_PRODUCER,
    )
    rows_path = out_dir / "aggregate" / "tournament_rows_v2.json"
    write_json_artifact(rows_path, _json_payload(rows))
    guard = build_bias_guard(
        rows=rows.rows,
        created_at=created,
        min_events_for_pbo=min_events_for_stability,
        fold_count=fold_count,
        known_gaps=[FIXTURE_GAP, "LOCAL_SIMULATION_ONLY", "NOT_ACTUAL_CASH"],
        source_refs=[
            _artifact_ref(
                rows_path, artifact_id=rows.artifact_id, schema_version=rows.schema_version
            )
        ],
        producer_command=NO_CASH_BACKTEST_SAMPLE_PRODUCER,
    )
    guard_path = out_dir / "aggregate" / "bias_guard.json"
    write_json_artifact(guard_path, _json_payload(guard))
    manifest = {
        "schema_version": "crypto_perp_no_cash_backtest_sample.v1",
        "created_at": serialize_utc_z(created),
        "producer": {"tool": "sis", "command": NO_CASH_BACKTEST_SAMPLE_PRODUCER},
        "target_event_count": target_event_count,
        "event_count": len(pairs),
        "outcome_count": len(pairs),
        "generated_event_count": generated,
        "source_availability_count": len(source_paths),
        "known_gaps": [FIXTURE_GAP, "LOCAL_SIMULATION_ONLY", "NOT_ACTUAL_CASH"],
        "non_goal_flags": {
            "paper_permission_granted": False,
            "actual_cash_used": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "profit_proven": False,
        },
        "artifact_paths": {
            "tournament_rows_v2": rows_path.as_posix(),
            "bias_guard": guard_path.as_posix(),
            "source_availability": source_paths,
        },
    }
    manifest_path = out_dir / "selection_manifest.json"
    write_json_artifact(manifest_path, manifest)
    return NoCashBacktestSampleResult(
        event_count=len(pairs),
        outcome_count=len(pairs),
        generated_event_count=generated,
        source_availability_count=len(source_paths),
        rows_path=rows_path,
        guard_path=guard_path,
        manifest_path=manifest_path,
    )
