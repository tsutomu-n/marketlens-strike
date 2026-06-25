from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.build_entry_signal_rows import (
    _entry_signal_rows,
)

from .helpers import _feature_rows, _write_spec, load_authoring_spec


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_entry_signal_rows_emit_blocked_base_trade_before_multi_leg(tmp_path) -> None:
    spec = _spec(tmp_path)
    binding = spec.experiment.symbol_bindings[0]
    row = _feature_rows()[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    rows = _entry_signal_rows(
        spec=spec,
        row=row,
        binding=binding,
        bindings={binding.real_market_symbol: binding},
        side="long",
        generated_at=generated_at,
        raw_score=0.8,
        rank=0.8,
        block_reason="risk_gate",
    )

    assert len(rows) == 1
    assert rows[0]["side"] == "none"
    assert rows[0]["block_reasons"] == ["risk_gate"]
    assert rows[0]["max_fill_fraction"] == 0.0
    assert rows[0]["multi_leg_group_id"] is None


def test_entry_signal_rows_emit_single_trade_when_not_blocked(tmp_path) -> None:
    spec = _spec(tmp_path)
    binding = spec.experiment.symbol_bindings[0]
    row = _feature_rows()[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    rows = _entry_signal_rows(
        spec=spec,
        row=row,
        binding=binding,
        bindings={binding.real_market_symbol: binding},
        side="long",
        generated_at=generated_at,
        raw_score=0.8,
        rank=0.8,
        block_reason=None,
    )

    assert len(rows) == 1
    assert rows[0]["generated_at"] == generated_at
    assert rows[0]["real_market_symbol"] == "QQQ"
    assert rows[0]["side"] == "long"
    assert rows[0]["block_reasons"] == []
    assert rows[0]["multi_leg_group_id"] is None
