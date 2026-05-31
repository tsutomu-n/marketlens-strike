from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.trade_xyz.cost_model import (
    FeeResolution,
    calculate_market_like_fee,
    calculate_v0_funding_amount,
    resolve_fee_bps,
)


def test_resolve_fee_bps_prefers_row_fee_values() -> None:
    fee = resolve_fee_bps(
        {"taker_fee_bps": 7.0, "maker_fee_bps": 2.0, "fee_mode": "standard"},
        fee_model_path="configs/fee_model.trade_xyz.yaml",
        fee_scenario="row_resolved",
    )

    assert fee == FeeResolution(taker_fee_bps=7.0, maker_fee_bps=2.0, source="row")


def test_resolve_fee_bps_falls_back_to_config_by_fee_mode() -> None:
    fee = resolve_fee_bps(
        {"fee_mode": "growth"},
        fee_model_path="configs/fee_model.trade_xyz.yaml",
        fee_scenario="row_resolved",
    )

    assert fee.resolved
    assert fee.taker_fee_bps == 0.9
    assert fee.maker_fee_bps == 0.3
    assert fee.source == "configs/fee_model.trade_xyz.yaml:growth"


def test_resolve_fee_bps_unresolved_unknown_fee_mode() -> None:
    fee = resolve_fee_bps(
        {"fee_mode": "unknown"},
        fee_model_path="configs/fee_model.trade_xyz.yaml",
        fee_scenario="row_resolved",
    )

    assert not fee.resolved
    assert fee.source == "unresolved"


def test_market_like_fee_always_uses_taker_rate() -> None:
    assert calculate_market_like_fee(fill_notional_usd=1_000, taker_fee_bps=9.0) == 0.9


def test_nullable_zero_funding_policy_does_not_apply_runtime_row_funding() -> None:
    amount, warning = calculate_v0_funding_amount(
        policy="nullable_zero_v0",
        position_qty=2,
        oracle_price=100,
        funding_rate=0.01,
        is_funding_event=False,
        event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert amount == 0
    assert warning == "funding_rate_present_without_interval_assertion"


def test_fixture_hourly_funding_policy_requires_event_and_uses_oracle_price() -> None:
    amount, warning = calculate_v0_funding_amount(
        policy="fixture_hourly_v0",
        position_qty=2,
        oracle_price=100,
        funding_rate=0.01,
        is_funding_event=True,
        event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert amount == -2.0
    assert warning is None


def test_fixture_hourly_funding_policy_ignores_non_event_rows() -> None:
    amount, warning = calculate_v0_funding_amount(
        policy="fixture_hourly_v0",
        position_qty=2,
        oracle_price=100,
        funding_rate=0.01,
        is_funding_event=False,
        event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert amount == 0
    assert warning is None
