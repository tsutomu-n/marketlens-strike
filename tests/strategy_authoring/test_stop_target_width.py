from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.stop_target_width import (
    _apply_stop_target_width_gate,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError

from .helpers import load_authoring_spec, template_yaml


def _spec(tmp_path):
    spec_path = tmp_path / "stop-target-width.yaml"
    spec_path.write_text(template_yaml(), encoding="utf-8")
    return load_authoring_spec(spec_path)


def test_stop_target_width_gate_passes_non_trade_rows_through(tmp_path) -> None:
    spec = _spec(tmp_path)
    row = {"side": "none", "stop_loss_bps": None, "min_stop_loss_bps": 100.0}

    assert _apply_stop_target_width_gate(row, spec) is row


def test_stop_target_width_gate_blocks_stop_before_take_profit(tmp_path) -> None:
    spec = _spec(tmp_path)
    row = {
        "side": "long",
        "ts_signal": "2026-01-01T00:00:00+00:00",
        "execution_symbol": "XYZ100",
        "stop_loss_bps": 90.0,
        "min_stop_loss_bps": 100.0,
        "take_profit_bps": 500.0,
        "max_take_profit_bps": 400.0,
        "block_reasons": ["preexisting"],
    }

    blocked = _apply_stop_target_width_gate(row, spec)

    assert blocked["side"] == "none"
    assert blocked["block_reasons"] == ["preexisting", "stop_loss_bps_too_low"]


def test_stop_target_width_gate_validates_min_max_order(tmp_path) -> None:
    spec = _spec(tmp_path)

    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.exit.max_stop_loss_bps must be >= min_stop_loss_bps",
    ):
        _apply_stop_target_width_gate(
            {
                "side": "long",
                "min_stop_loss_bps": 200.0,
                "max_stop_loss_bps": 100.0,
            },
            spec,
        )

    with pytest.raises(
        StrategyAuthoringValidationError,
        match="rules.exit.max_take_profit_bps must be >= min_take_profit_bps",
    ):
        _apply_stop_target_width_gate(
            {
                "side": "long",
                "min_take_profit_bps": 300.0,
                "max_take_profit_bps": 200.0,
            },
            spec,
        )
