from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.marker_dispatch import _marker_rule_signal_row
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _feature_rows, _write_data, load_authoring_spec


def _spec_with_markers(tmp_path):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "marker-dispatch.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  close:\n    all:\n      - column: close_signal\n        op: is_true\n"
            "  reduce:\n    all:\n      - column: reduce_signal\n        op: is_true\n"
            "  add:\n    all:\n      - column: add_signal\n        op: is_true\n"
            "  rebalance:\n    all:\n      - column: rebalance_signal\n        op: is_true\n"
            "  entry:\n    all:",
        )
        .replace(
            "  exit:\n    stop_loss_bps: 150",
            "  exit:\n    reduce_fraction: 0.5\n    add_fraction: 0.25\n"
            "    rebalance_target_fraction: 0.8\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_marker_rule_signal_row_prefers_close_before_other_markers(tmp_path) -> None:
    spec = _spec_with_markers(tmp_path)
    row = {
        **_feature_rows()[0],
        "close_signal": True,
        "reduce_signal": True,
        "add_signal": True,
        "rebalance_signal": True,
        "vix_level": 35.0,
    }

    signal = _marker_rule_signal_row(
        spec=spec,
        row=row,
        binding=spec.experiment.symbol_bindings[0],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert signal is not None
    assert signal["side"] == "close"
    assert signal["reason_codes"] == [spec.rules.close_reason_code]
    assert signal["block_reasons"] == []


def test_marker_rule_signal_row_prefers_reduce_before_add_rebalance_and_hold(
    tmp_path,
) -> None:
    spec = _spec_with_markers(tmp_path)
    row = {
        **_feature_rows()[0],
        "close_signal": False,
        "reduce_signal": True,
        "add_signal": True,
        "rebalance_signal": True,
        "vix_level": 35.0,
    }

    signal = _marker_rule_signal_row(
        spec=spec,
        row=row,
        binding=spec.experiment.symbol_bindings[0],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert signal is not None
    assert signal["side"] == "reduce"
    assert signal["reason_codes"] == [spec.rules.reduce_reason_code]


def test_marker_rule_signal_row_returns_none_without_marker_match(tmp_path) -> None:
    spec = _spec_with_markers(tmp_path)

    signal = _marker_rule_signal_row(
        spec=spec,
        row={
            **_feature_rows()[0],
            "close_signal": False,
            "reduce_signal": False,
            "add_signal": False,
            "rebalance_signal": False,
            "vix_level": 20.0,
        },
        binding=spec.experiment.symbol_bindings[0],
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert signal is None
