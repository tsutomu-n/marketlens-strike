from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.trade_control_fields import (
    _trade_control_fields,
)

from .helpers import _feature_rows, _write_spec, load_authoring_spec, template_yaml


def _spec(tmp_path, text: str | None = None):
    spec_path = tmp_path / "spec.yaml"
    if text is None:
        _write_spec(spec_path)
    else:
        spec_path.write_text(text, encoding="utf-8")
    return load_authoring_spec(spec_path)


def test_trade_control_fields_compose_default_controls(tmp_path) -> None:
    fields = _trade_control_fields(row=_feature_rows()[0], spec=_spec(tmp_path))

    assert fields["entry_order_type"] == "market"
    assert fields["entry_reduce_only"] is False
    assert fields["slippage_bps"] == 0.0
    assert fields["stop_loss_bps"] == 150.0
    assert fields["take_profit_bps"] == 300.0
    assert fields["reduce_fraction"] is None
    assert fields["bracket_type"] == "none"


def test_trade_control_fields_uses_reduce_only_when_resolving_exit_controls(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        template_yaml().replace(
            "    partial_exit_fraction: 0.5",
            "    partial_exit_fraction: 0.5\n    reduce_fraction: 0.4",
        ),
    )

    fields = _trade_control_fields(
        row=_feature_rows()[0],
        spec=spec,
        order_overrides={"reduce_only": True},
    )

    assert fields["entry_reduce_only"] is True
    assert fields["reduce_fraction"] == 0.4
