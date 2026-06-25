from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.marker_rows import (
    _hold_signal_row,
    _marker_signal_base,
)

from .helpers import _feature_rows, _write_data, _write_spec, load_authoring_spec


def test_marker_signal_base_uses_marker_side_and_core_metadata(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    binding = spec.experiment.symbol_bindings[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = _marker_signal_base(
        spec=spec,
        row=_feature_rows()[0],
        binding=binding,
        generated_at=generated_at,
        side="close",
    )

    assert row["schema_version"] == "strategy_signal.v1"
    assert (
        row["signal_id"]
        != _marker_signal_base(
            spec=spec,
            row=_feature_rows()[0],
            binding=binding,
            generated_at=generated_at,
            side="none",
        )["signal_id"]
    )
    assert row["generated_at"] == generated_at
    assert row["strategy_id"] == spec.experiment.strategy_id
    assert row["execution_symbol"] == binding.execution_symbol
    assert row["real_market_symbol"] == binding.real_market_symbol
    assert row["side"] == "close"
    assert row["confidence"] == 0.0
    assert row["source_confidence"] == 0.8
    assert row["venue_quality_score"] == 0.9
    assert row["tracking_ref"] is None
    assert "stop_loss_bps" not in row
    assert "reason_codes" not in row


def test_hold_signal_row_uses_hold_reason_and_no_trade_defaults(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    binding = spec.experiment.symbol_bindings[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = _hold_signal_row(
        spec=spec,
        row=_feature_rows()[0],
        binding=binding,
        generated_at=generated_at,
        block_reason="manual_hold",
    )

    assert row["schema_version"] == "strategy_signal.v1"
    assert row["generated_at"] == generated_at
    assert row["execution_symbol"] == binding.execution_symbol
    assert row["real_market_symbol"] == binding.real_market_symbol
    assert row["side"] == "none"
    assert row["confidence"] == 0.0
    assert row["entry_order_type"] == "market"
    assert row["max_fill_fraction"] == 0.0
    assert row["depth_column"] is None
    assert row["position_weight"] == 0.0
    assert row["reason_codes"] == [spec.rules.hold_reason_code]
    assert row["block_reasons"] == ["manual_hold"]
    assert isinstance(row["signal_id"], str)
    assert isinstance(row["parameter_hash"], str)


def test_hold_signal_row_defaults_missing_block_reason_to_hold_rule(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    row = _hold_signal_row(
        spec=spec,
        row=_feature_rows()[0],
        binding=spec.experiment.symbol_bindings[0],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        block_reason=None,
    )

    assert row["block_reasons"] == ["hold_rule"]
