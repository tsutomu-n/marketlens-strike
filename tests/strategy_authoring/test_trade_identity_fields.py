from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.signal_ids import _signal_id
from sis.research.strategy_lab.authoring.compiler.trade_identity_fields import (
    _trade_identity_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest

from .helpers import _feature_rows, _write_spec, load_authoring_spec


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_trade_identity_fields_preserve_base_signal_metadata(tmp_path) -> None:
    spec = _spec(tmp_path)
    binding = spec.experiment.symbol_bindings[0]
    row = _feature_rows()[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    fields = _trade_identity_fields(
        spec=spec,
        row=row,
        binding=binding,
        side="long",
        generated_at=generated_at,
    )

    assert fields == {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side="long"),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "multi_leg_group_id": None,
        "multi_leg_leg_index": None,
        "multi_leg_leg_count": None,
        "multi_leg_anchor_real_market_symbol": None,
        "side": "long",
    }


def test_trade_identity_fields_preserve_multi_leg_metadata(tmp_path) -> None:
    spec = _spec(tmp_path)
    binding = spec.experiment.symbol_bindings[0]
    row = _feature_rows()[0]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    fields = _trade_identity_fields(
        spec=spec,
        row=row,
        binding=binding,
        side="short",
        generated_at=generated_at,
        multi_leg_group_id="group-1",
        multi_leg_leg_index=2,
        multi_leg_leg_count=3,
        multi_leg_anchor_real_market_symbol="QQQ",
    )

    assert fields["signal_id"] == _signal_id(spec, row, binding, side="short")
    assert fields["multi_leg_group_id"] == "group-1"
    assert fields["multi_leg_leg_index"] == 2
    assert fields["multi_leg_leg_count"] == 3
    assert fields["multi_leg_anchor_real_market_symbol"] == "QQQ"
    assert fields["side"] == "short"
