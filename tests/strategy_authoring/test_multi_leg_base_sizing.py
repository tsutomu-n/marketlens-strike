from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.multi_leg_base_sizing import (
    _multi_leg_base_sizing,
)

from .helpers import _write_spec, load_authoring_spec, template_yaml


def _spec(tmp_path, text: str | None = None):
    spec_path = tmp_path / "spec.yaml"
    if text is None:
        _write_spec(spec_path)
    else:
        spec_path.write_text(text, encoding="utf-8")
    return load_authoring_spec(spec_path)


def test_multi_leg_base_sizing_uses_fixed_strategy_sizing(tmp_path) -> None:
    sizing = _multi_leg_base_sizing(
        row={},
        spec=_spec(tmp_path),
    )

    assert sizing.position_weight == 1.0
    assert sizing.notional_usd == 1000.0


def test_multi_leg_base_sizing_uses_dynamic_row_sizing_columns(tmp_path) -> None:
    spec_text = template_yaml().replace(
        "  sizing:\n    position_weight: 1.0\n    notional_usd: 1000",
        "  sizing:\n"
        "    position_weight: 1.0\n"
        "    position_weight_column: row_weight\n"
        "    notional_usd: 1000\n"
        "    notional_usd_column: row_notional",
    )
    sizing = _multi_leg_base_sizing(
        row={"row_weight": "0.75", "row_notional": "2500"},
        spec=_spec(tmp_path, spec_text),
    )

    assert sizing.position_weight == 0.75
    assert sizing.notional_usd == 2500.0
