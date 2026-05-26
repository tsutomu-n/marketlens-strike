from __future__ import annotations

from sis.execution.live_order_policy import (
    MicroLiveGateInput,
    MicroLivePolicy,
    evaluate_micro_live_gates,
    load_micro_live_policy,
)


def _policy(enabled: bool = True) -> MicroLivePolicy:
    return MicroLivePolicy(
        enabled=enabled,
        venue="trade_xyz",
        max_notional_usd=50.0,
        max_daily_loss_usd=10.0,
        max_open_positions=1,
        max_leverage=2.0,
        allowed_symbols=("SP500", "XYZ100", "NVDA", "AAPL", "MSFT"),
        prohibited_order_types=("market",),
        schedule_cancel_deadline_seconds_after_now=300,
        close_require_reduce_only=True,
    )


def _gate_input(**overrides: object) -> MicroLiveGateInput:
    base = MicroLiveGateInput(
        enable_live_flag=True,
        kill_switch_clear=True,
        schedule_cancel_success=True,
        daily_loss_remaining_usd=50.0,
        requested_notional_usd=25.0,
        requested_leverage=1.5,
        order_type="limit",
        canonical_symbol="SP500",
        underlying_session_regular=True,
        tracking_trade_allowed=True,
        source_confidence=0.80,
        venue_quality_score=0.80,
        event_window_blocked=False,
    )
    return MicroLiveGateInput(**{**base.__dict__, **overrides})


def test_micro_live_policy_blocks_disabled_and_missing_confirm_flag() -> None:
    reasons = evaluate_micro_live_gates(
        _policy(enabled=False),
        _gate_input(enable_live_flag=False),
    )

    assert "BLOCK_MICRO_LIVE_DISABLED" in reasons
    assert "BLOCK_CONFIRM_FLAG_REQUIRED" in reasons


def test_load_micro_live_policy_reads_config_file() -> None:
    policy = load_micro_live_policy()

    assert policy.enabled is False
    assert policy.venue == "trade_xyz"
    assert policy.max_notional_usd == 50.0
    assert policy.max_leverage == 2.0
    assert "SP500" in policy.allowed_symbols
    assert "market" in policy.prohibited_order_types
    assert policy.schedule_cancel_deadline_seconds_after_now == 300
    assert policy.close_require_reduce_only is True


def test_micro_live_policy_blocks_market_notional_leverage_and_low_quality() -> None:
    reasons = evaluate_micro_live_gates(
        _policy(),
        _gate_input(
            order_type="market",
            requested_notional_usd=55.0,
            requested_leverage=3.0,
            source_confidence=0.60,
            venue_quality_score=0.65,
            schedule_cancel_success=False,
        ),
    )

    assert "BLOCK_ORDER_TYPE_PROHIBITED" in reasons
    assert "BLOCK_NOTIONAL_TOO_HIGH" in reasons
    assert "BLOCK_LEVERAGE_TOO_HIGH" in reasons
    assert "BLOCK_LOW_SOURCE_CONFIDENCE" in reasons
    assert "BLOCK_LOW_VENUE_QUALITY" in reasons
    assert "BLOCK_SCHEDULE_CANCEL_REQUIRED" in reasons


def test_micro_live_policy_allows_valid_gate_input() -> None:
    reasons = evaluate_micro_live_gates(_policy(), _gate_input())
    assert reasons == []


def test_micro_live_policy_blocks_non_regular_session_and_event_window() -> None:
    reasons = evaluate_micro_live_gates(
        _policy(),
        _gate_input(
            underlying_session_regular=False,
            event_window_blocked=True,
        ),
    )
    assert "BLOCK_UNDERLYING_NOT_REGULAR_SESSION" in reasons
    assert "BLOCK_EVENT_WINDOW" in reasons


def test_micro_live_policy_blocks_max_open_positions() -> None:
    reasons = evaluate_micro_live_gates(
        _policy(),
        _gate_input(open_positions_count=1),
    )
    assert "BLOCK_MAX_OPEN_POSITIONS" in reasons
