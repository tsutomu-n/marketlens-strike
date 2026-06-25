from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.marker_signal_base import (
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
        row={**_feature_rows()[0], "source_confidence": 0.8, "venue_quality_score": 0.7},
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
    assert row["raw_score"] is None
    assert row["rank_score"] is None
    assert row["percentile_rank"] is None
    assert row["tail_bucket"] == "none"
    assert row["confidence"] == 0.0
    assert row["source_confidence"] == 0.8
    assert row["venue_quality_score"] == 0.7
    assert row["feature_snapshot_ref"] is None
    assert row["quote_ref"] is None
    assert row["tracking_ref"] is None
