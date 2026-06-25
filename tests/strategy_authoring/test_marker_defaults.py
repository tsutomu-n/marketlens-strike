from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.marker_defaults import (
    _marker_trade_control_defaults,
)
from sis.research.strategy_lab.authoring.contracts.base import DEFAULT_EXIT_PRIORITY


def test_marker_trade_control_defaults_use_no_trade_execution_values() -> None:
    defaults = _marker_trade_control_defaults()

    assert defaults["stop_loss_bps"] is None
    assert defaults["exit_priority"] == DEFAULT_EXIT_PRIORITY
    assert defaults["bracket_type"] == "none"
    assert defaults["entry_order_type"] == "market"
    assert defaults["entry_time_in_force"] == "gtc"
    assert defaults["entry_reduce_only"] is False
    assert defaults["slippage_bps"] == 0.0
    assert defaults["max_fill_fraction"] == 0.0
    assert defaults["depth_participation_rate"] == 0.0
    assert defaults["position_weight"] == 0.0
    assert defaults["notional_usd"] is None


def test_marker_trade_control_defaults_leave_marker_reason_fields_to_callers() -> None:
    defaults = _marker_trade_control_defaults()

    assert "reason_codes" not in defaults
    assert "block_reasons" not in defaults


def test_marker_trade_control_defaults_return_fresh_dicts() -> None:
    first = _marker_trade_control_defaults()
    second = _marker_trade_control_defaults()
    first["entry_order_type"] = "limit"

    assert second["entry_order_type"] == "market"
    assert first is not second
