from __future__ import annotations

from sis.research.strategy_lab.authoring.io import load_authoring_spec, template_yaml
from sis.research.strategy_lab.authoring.required_columns import _required_columns


def test_required_columns_collects_template_inputs(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(template_yaml(), encoding="utf-8")
    columns = _required_columns(load_authoring_spec(spec_path))

    assert {
        "ts",
        "canonical_symbol",
        "trade_allowed",
        "close_above_sma20",
        "vix_level",
        "research_return_1d",
        "research_return_4h",
    }.issubset(columns)


def test_required_columns_do_not_require_derived_outputs(tmp_path) -> None:
    spec_path = tmp_path / "derived.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  entry:\n    all:",
            "  derived_features:\n"
            "    - name: trend_spread\n"
            "      op: diff\n"
            "      columns: [fast_ma, slow_ma]\n"
            "  entry:\n"
            "    all:\n"
            "      - column: trend_spread\n"
            "        op: gt\n"
            "        value: 0\n",
        ),
        encoding="utf-8",
    )
    columns = _required_columns(load_authoring_spec(spec_path))

    assert "fast_ma" in columns
    assert "slow_ma" in columns
    assert "trend_spread" not in columns
