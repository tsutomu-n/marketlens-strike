from __future__ import annotations

from .helpers import _feature_rows, _write_spec, load_authoring_spec

from sis.research.strategy_lab.authoring.compiler.trade_sizing_fields import (
    _trade_sizing_fields,
)


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_trade_sizing_fields_preserve_explicit_values(tmp_path) -> None:
    assert _trade_sizing_fields(
        spec=_spec(tmp_path),
        row=_feature_rows()[0],
        position_weight=0.4,
        notional_usd=2500.0,
    ) == {
        "position_weight": 0.4,
        "notional_usd": 2500.0,
    }


def test_trade_sizing_fields_preserve_explicit_zero_weight(tmp_path) -> None:
    assert _trade_sizing_fields(
        spec=_spec(tmp_path),
        row=_feature_rows()[0],
        position_weight=0.0,
        notional_usd=None,
    ) == {
        "position_weight": 0.0,
        "notional_usd": 1000.0,
    }


def test_trade_sizing_fields_fall_back_to_spec_sizing(tmp_path) -> None:
    assert _trade_sizing_fields(
        spec=_spec(tmp_path),
        row=_feature_rows()[0],
        position_weight=None,
        notional_usd=None,
    ) == {
        "position_weight": 1.0,
        "notional_usd": 1000.0,
    }
