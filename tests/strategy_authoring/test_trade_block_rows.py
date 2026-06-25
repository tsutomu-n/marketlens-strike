from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.trade_block_rows import (
    _blocked_trade_signal_row,
)

from .helpers import _feature_rows, _write_data, _write_spec, load_authoring_spec


def test_blocked_trade_signal_row_uses_trade_row_then_neutralizes_trade_fields(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    binding = spec.experiment.symbol_bindings[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = _blocked_trade_signal_row(
        spec=spec,
        row=_feature_rows()[0],
        binding=binding,
        side="long",
        generated_at=generated_at,
        raw_score=0.75,
        rank=0.75,
        block_reason="risk_throttle_daily_loss",
    )

    assert row["side"] == "none"
    assert row["generated_at"] == generated_at
    assert row["execution_symbol"] == binding.execution_symbol
    assert row["real_market_symbol"] == binding.real_market_symbol
    assert row["raw_score"] == 0.75
    assert row["rank_score"] == 0.75
    assert row["confidence"] == 0.0
    assert row["entry_order_type"] == "market"
    assert row["stop_loss_bps"] is None
    assert row["take_profit_bps"] is None
    assert row["position_weight"] == 0.0
    assert row["reason_codes"] == [spec.rules.hold_reason_code]
    assert row["block_reasons"] == ["risk_throttle_daily_loss"]
