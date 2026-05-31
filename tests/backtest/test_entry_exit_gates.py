from __future__ import annotations

from sis.backtest.engine.config import GateConfig
from sis.backtest.trade_xyz.cost_model import FeeResolution
from sis.backtest.trade_xyz.gates import evaluate_entry_gate, evaluate_exit_gate


def test_entry_gate_blocks_untradable_block_reasons_and_unresolved_fee() -> None:
    result = evaluate_entry_gate(
        {
            "symbol": "SP500",
            "is_tradable": False,
            "block_reasons": ["BLOCK_NO_BID"],
            "market_status": "open",
        },
        gates=GateConfig(),
        fee=FeeResolution.unresolved(),
    )

    assert not result.allowed
    assert result.reasons == ["is_tradable_false", "block_reasons_non_empty", "fee_unresolved"]


def test_entry_gate_blocks_configured_spread_depth_bound_and_oi_limits() -> None:
    result = evaluate_entry_gate(
        {
            "symbol": "SP500",
            "is_tradable": True,
            "block_reasons": [],
            "market_status": "open",
            "spread_bps": 11.0,
            "min_side_depth_10bps_usd": 500.0,
            "bound_distance": 0.4,
            "oi_cap_usage": 0.95,
        },
        gates=GateConfig(
            max_spread_bps=10,
            min_depth_10bps_usd=1_000,
            max_bound_distance=0.3,
            max_oi_cap_usage=0.9,
        ),
        fee=FeeResolution(taker_fee_bps=9, maker_fee_bps=3, source="row"),
    )

    assert not result.allowed
    assert result.reasons == [
        "spread_bps_above_max",
        "min_depth_10bps_usd_below_min",
        "bound_distance_above_max",
        "oi_cap_usage_above_max",
    ]


def test_exit_gate_allows_close_only_and_fixture_unknown_market_status() -> None:
    fee = FeeResolution(taker_fee_bps=9, maker_fee_bps=3, source="row")

    assert evaluate_exit_gate(
        {"market_status": "close_only"}, position_is_open=True, exit_signal_exists=True, fee=fee
    ).allowed
    assert evaluate_exit_gate(
        {"market_status": "unknown_if_fixture"},
        position_is_open=True,
        exit_signal_exists=True,
        fee=fee,
    ).allowed


def test_exit_gate_blocks_missing_position_signal_price_or_fee() -> None:
    result = evaluate_exit_gate(
        {"market_status": "open"},
        position_is_open=False,
        exit_signal_exists=False,
        fee=FeeResolution.unresolved(),
        exit_price_resolved=False,
    )

    assert not result.allowed
    assert result.reasons == [
        "position_not_open",
        "exit_signal_missing",
        "exit_price_unresolved",
        "fee_unresolved",
    ]
