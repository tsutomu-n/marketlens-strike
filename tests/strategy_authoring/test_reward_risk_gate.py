from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.reward_risk_gate import (
    _apply_reward_risk_gate,
)

from .helpers import _write_spec, load_authoring_spec


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_reward_risk_gate_passes_rows_without_minimum_or_trade_side(tmp_path) -> None:
    spec = _spec(tmp_path)
    no_minimum = {"side": "long", "stop_loss_bps": 150.0, "take_profit_bps": 300.0}
    neutral = {"side": "none", "min_reward_risk_ratio": 2.5}

    assert _apply_reward_risk_gate(no_minimum, spec) is no_minimum
    assert _apply_reward_risk_gate(neutral, spec) is neutral


def test_reward_risk_gate_blocks_low_ratio_and_preserves_ratio_fields(tmp_path) -> None:
    row = {
        "ts_signal": "2026-01-01T00:00:00+00:00",
        "execution_symbol": "XYZ100",
        "signal_id": "sig-1",
        "side": "long",
        "confidence": 0.7,
        "stop_loss_bps": 150.0,
        "take_profit_bps": 300.0,
        "min_reward_risk_ratio": 2.5,
        "block_reasons": [],
    }

    blocked = _apply_reward_risk_gate(row, _spec(tmp_path))

    assert blocked["side"] == "none"
    assert blocked["confidence"] == 0.0
    assert blocked["min_reward_risk_ratio"] == 2.5
    assert blocked["reward_risk_ratio"] == 2.0
    assert blocked["block_reasons"] == ["reward_risk_ratio_too_low"]


def test_reward_risk_gate_blocks_missing_ratio(tmp_path) -> None:
    row = {
        "ts_signal": "2026-01-01T00:00:00+00:00",
        "execution_symbol": "XYZ100",
        "signal_id": "sig-1",
        "side": "short",
        "confidence": 0.7,
        "take_profit_bps": 300.0,
        "min_reward_risk_ratio": 1.5,
        "block_reasons": ["existing"],
    }

    blocked = _apply_reward_risk_gate(row, _spec(tmp_path))

    assert blocked["side"] == "none"
    assert blocked["min_reward_risk_ratio"] == 1.5
    assert blocked["reward_risk_ratio"] is None
    assert blocked["block_reasons"] == ["existing", "reward_risk_ratio_missing"]
