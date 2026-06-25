from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.marker_action_row import (
    _marker_action_signal_row,
)

from .helpers import _feature_rows, _write_data, _write_spec, load_authoring_spec


def test_marker_action_signal_row_composes_action_fields(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = _marker_action_signal_row(
        spec=spec,
        row=_feature_rows()[0],
        binding=spec.experiment.symbol_bindings[0],
        generated_at=generated_at,
        side="reduce",
        position_fields={"reduce_fraction": 0.4},
        reason_code="manual_reduce",
    )

    assert row["schema_version"] == "strategy_signal.v1"
    assert row["generated_at"] == generated_at
    assert row["execution_symbol"] == spec.experiment.symbol_bindings[0].execution_symbol
    assert row["side"] == "reduce"
    assert row["reduce_fraction"] == 0.4
    assert row["entry_order_type"] == "market"
    assert row["max_fill_fraction"] == 0.0
    assert row["reason_codes"] == ["manual_reduce"]
    assert row["block_reasons"] == []
