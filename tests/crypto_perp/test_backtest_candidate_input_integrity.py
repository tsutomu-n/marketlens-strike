from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

import pytest

from sis.crypto_perp.backtest_candidate_pack import (
    build_crypto_perp_backtest_candidate_pack,
)
from sis.crypto_perp.clock import serialize_utc_z
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.real_market_no_cash_sample import write_real_market_no_cash_sample
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows
from .test_real_market_no_cash_sample import (
    _write_funding_rows,
    _write_public_candle_csv,
    _write_ticker_source_root,
)
from .test_backtest_candidate_pack import (
    _event,
    _outcome,
    _write_json,
    _write_ready_inputs,
)


def _build(data_dir: Path, out_dir: Path):
    return build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=out_dir,
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )


def test_tampered_derived_rows_are_ignored_and_recomputed(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    rows = build_cost_aware_tournament_rows(
        outcomes=[_outcome(_event().event_id)],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
    ).model_dump(mode="json")
    rows["rows"][0]["cost_adjusted_cash_estimate_usd"] = "999999"
    _write_json(data_dir / "tournament_rows_v2.json", rows)

    result = _build(data_dir, tmp_path / "pack")
    persisted = json.loads(result.paths["tournament_rows_v2.json"].read_text(encoding="utf-8"))

    assert all(row["cost_adjusted_cash_estimate_usd"] != "999999" for row in persisted["rows"])
    assert result.decision.summary["tournament_rows_origin"]["origin"] == ("recomputed_minimal")


def test_multiple_matured_outcomes_for_one_event_fail_closed(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    duplicate = json.loads((data_dir / "outcome.json").read_text(encoding="utf-8"))
    _write_json(data_dir / "outcome_duplicate.json", duplicate)

    with pytest.raises(ValueError, match="MULTIPLE_MATURED_OUTCOMES_FOR_EVENT"):
        _build(data_dir, tmp_path / "pack")


def test_duplicate_event_identity_fails_closed(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    duplicate = json.loads((data_dir / "event.json").read_text(encoding="utf-8"))
    _write_json(data_dir / "event_duplicate.json", duplicate)

    with pytest.raises(ValueError, match="MULTIPLE_EVENTS_WITH_SAME_ID"):
        _build(data_dir, tmp_path / "pack")


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"fee_rate": Decimal("0.0000001")}, "fee_rate must not be below"),
        ({"funding_rate": Decimal("0")}, "funding_rate must not be below"),
        ({"slippage_bps": Decimal("0.0001")}, "slippage_bps must not be below"),
    ],
)
def test_candidate_pack_rejects_costs_below_project_floor(
    tmp_path: Path, kwargs: dict, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        build_crypto_perp_backtest_candidate_pack(
            data_dir=tmp_path,
            out_dir=tmp_path / "pack",
            created_at="2026-06-21T08:00:00Z",
            notional_usd=Decimal("100"),
            **kwargs,
        )


def _write_public_sample(tmp_path: Path, *, with_market_sources: bool = False) -> Path:
    input_csv = _write_public_candle_csv(tmp_path / "source.csv", row_count=60)
    data_dir = tmp_path / "sample"
    source_root = None
    if with_market_sources:
        source_root = _write_ticker_source_root(tmp_path / "market-source", row_count=60)
        _write_funding_rows(source_root, row_count=60)
    write_real_market_no_cash_sample(
        out_dir=data_dir,
        created_at="2026-06-27T06:00:00Z",
        input_csv=input_csv,
        ticker_source_root=source_root,
        symbol="BTCUSDT",
        target_event_count=1,
        lookback_minutes=60,
        horizon_minutes=60,
        interval_minutes=5,
        min_events_for_stability=1,
        fold_count=2,
    )
    return data_dir


def test_outcome_return_edit_with_stale_identity_fails_closed(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    path = data_dir / "outcome.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["horizons"][0]["long_return_before_cost"] = "99"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="OUTCOME_IDENTITY_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_public_event_feature_edit_fails_against_raw_candles(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path)
    path = data_dir / "events/event_000.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["features_at_detection"]["return_60m"] = "0.99"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="EVENT_CANDLE_FEATURE_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_public_outcome_resealed_with_forged_prices_fails_against_raw_candles(
    tmp_path: Path,
) -> None:
    data_dir = _write_public_sample(tmp_path)
    path = data_dir / "outcomes/outcome_000.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    reference = Decimal(original["horizons"][0]["reference_price"])
    forged = build_outcome(
        event_id=original["event_id"],
        settled_at=original["settled_at"],
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=reference,
                close_price=reference * Decimal("2"),
                high_price=reference * Decimal("2"),
                low_price=reference,
            )
        ],
        source_refs=original["source_refs"],
        known_gaps=original["known_gaps"],
    )
    _write_json(path, forged)

    with pytest.raises(ValueError, match="OUTCOME_CANDLE_VALUE_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_public_source_ref_sha_mismatch_fails_closed(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path)
    source_path = data_dir / "input/BTCUSDT_5m_public_market.csv"
    source_path.write_text(source_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SOURCE_REF_SHA256_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_public_selection_manifest_event_set_mismatch_fails_closed(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path)
    path = data_dir / "selection_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["event_set"] = ["forged-event"]
    _write_json(path, payload)

    with pytest.raises(ValueError, match="SELECTION_MANIFEST_EVENT_SET_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_multiple_matured_horizons_inside_outcome_fail_closed(tmp_path: Path) -> None:
    event = _event()
    data_dir = tmp_path / "data"
    _write_json(data_dir / "event.json", event)
    outcome = build_outcome(
        event_id=event.event_id,
        settled_at="2026-06-21T12:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("101"),
                high_price=Decimal("102"),
                low_price=Decimal("99"),
            ),
            OutcomePriceWindow(
                horizon_minutes=360,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("110"),
                high_price=Decimal("111"),
                low_price=Decimal("98"),
            ),
        ],
    )
    _write_json(data_dir / "outcome.json", outcome)

    with pytest.raises(ValueError, match="MATURED_HORIZON_COUNT_NOT_ONE"):
        _build(data_dir, tmp_path / "pack")


def test_matured_horizon_must_match_candidate_holding_period(tmp_path: Path) -> None:
    event = _event()
    data_dir = tmp_path / "data"
    _write_json(data_dir / "event.json", event)
    outcome = build_outcome(
        event_id=event.event_id,
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=30,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("101"),
                high_price=Decimal("102"),
                low_price=Decimal("99"),
            )
        ],
    )
    _write_json(data_dir / "outcome.json", outcome)

    with pytest.raises(ValueError, match="MATURED_HORIZON_HOLDING_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_current_public_sample_integrity_contract_passes(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path)

    result = _build(data_dir, tmp_path / "pack")

    assert result.decision.event_count == 1


def test_duplicate_source_availability_for_event_fails_closed(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    duplicate = json.loads((data_dir / "source_availability.json").read_text(encoding="utf-8"))
    _write_json(data_dir / "source_availability_duplicate.json", duplicate)

    with pytest.raises(ValueError, match="MULTIPLE_CRYPTO_PERP_SOURCE_AVAILABILITY_V1_FOR_EVENT"):
        _build(data_dir, tmp_path / "pack")


def test_resealed_ticker_metadata_forgery_fails_against_raw_parquet(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path, with_market_sources=True)
    source_path = data_dir / "source_availability/source_000.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    for status in payload["source_statuses"]:
        if status["source_id"] == "ticker":
            status["metadata"]["bid_px"] = "1"
    source = CryptoPerpSourceAvailability.model_validate(payload)
    payload["artifact_id"] = stable_hash(
        [
            "crypto-perp-source-availability",
            source.event_id,
            serialize_utc_z(source.created_at),
            [status.model_dump(mode="json") for status in source.source_statuses],
            source.known_gaps,
        ]
    )
    _write_json(source_path, payload)

    with pytest.raises(ValueError, match="TICKER_SOURCE_STATUS_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_market_window_cannot_escape_raw_validation_by_relabeling_provenance(
    tmp_path: Path,
) -> None:
    data_dir = _write_public_sample(tmp_path)
    event_path = data_dir / "events/event_000.json"
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    payload["producer"]["command"] = "forged-producer"
    for ref in payload["source_refs"]:
        if ref["schema_version"] == "bitget_public_candles_5m.input_projection.v1":
            ref["schema_version"] = "forged-source-schema"
    _write_json(event_path, payload)

    with pytest.raises(ValueError, match="PUBLIC_CANDLE_SOURCE_REF_MISSING_OR_AMBIGUOUS"):
        _build(data_dir, tmp_path / "pack")


def test_resealed_ticker_available_flag_must_match_raw_source(tmp_path: Path) -> None:
    data_dir = _write_public_sample(tmp_path, with_market_sources=True)
    source_path = data_dir / "source_availability/source_000.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    for status in payload["source_statuses"]:
        if status["source_id"] == "ticker":
            assert status["row_count"] == 1
            status["available"] = False
    payload["can_compute_cost_adjusted_estimate"] = False
    payload["summary"]["can_compute_cost_adjusted_estimate"] = False
    payload["summary"]["available_source_count"] -= 1
    source = CryptoPerpSourceAvailability.model_validate(payload)
    payload["artifact_id"] = stable_hash(
        [
            "crypto-perp-source-availability",
            source.event_id,
            serialize_utc_z(source.created_at),
            [status.model_dump(mode="json") for status in source.source_statuses],
            source.known_gaps,
        ]
    )
    _write_json(source_path, payload)

    with pytest.raises(ValueError, match="TICKER_SOURCE_STATUS_MISMATCH"):
        _build(data_dir, tmp_path / "pack")


def test_non_market_event_without_reconstructable_source_cannot_promote(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")

    result = _build(data_dir, tmp_path / "pack")

    assert "EVENT_SOURCE_PROVENANCE_NOT_VERIFIABLE" in result.decision.reason_codes
