from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.build_signal_row import _build_signal_row
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _feature_rows, load_authoring_spec


def _spec(tmp_path, yaml_text: str | None = None):
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml_text or template_yaml(), encoding="utf-8")
    return load_authoring_spec(spec_path)


def _spec_with_markers(tmp_path):
    return _spec(
        tmp_path,
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
    )


def _call_build_signal_row(
    *,
    spec,
    row: dict,
    cooldown_until_by_symbol: dict | None = None,
):
    binding = spec.experiment.symbol_bindings[0]
    bindings = {binding.real_market_symbol: binding}
    cooldown_state = cooldown_until_by_symbol if cooldown_until_by_symbol is not None else {}
    return _build_signal_row(
        spec=spec,
        row=row,
        symbol=binding.real_market_symbol,
        binding=binding,
        bindings=bindings,
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        cooldown_until_by_symbol=cooldown_state,
    )


def test_build_signal_row_prefers_marker_before_hold_and_entry(tmp_path) -> None:
    spec = _spec_with_markers(tmp_path)
    row = {
        **_feature_rows()[0],
        "close_signal": True,
        "reduce_signal": True,
        "add_signal": True,
        "rebalance_signal": True,
        "vix_level": 35.0,
    }

    rows = _call_build_signal_row(spec=spec, row=row)

    assert len(rows) == 1
    assert rows[0]["side"] == "close"
    assert rows[0]["reason_codes"] == [spec.rules.close_reason_code]
    assert rows[0]["block_reasons"] == []


def test_build_signal_row_returns_empty_when_no_side_selected(tmp_path) -> None:
    spec = _spec(tmp_path)
    row = _feature_rows()[0] | {"trade_allowed": False}

    assert _call_build_signal_row(spec=spec, row=row) == []


def test_build_signal_row_keeps_risk_throttle_cooldown_state(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor: -0.15\n"
            "    cooldown_minutes: 90",
        ),
    )
    first_row, second_row, *_ = _feature_rows()
    first_row = first_row | {"strategy_drawdown": -0.20}
    second_row = second_row | {
        "ts": first_row["ts"] + timedelta(minutes=30),
        "strategy_drawdown": -0.05,
    }
    cooldown_until_by_symbol = {}

    first_rows = _call_build_signal_row(
        spec=spec,
        row=first_row,
        cooldown_until_by_symbol=cooldown_until_by_symbol,
    )
    second_rows = _call_build_signal_row(
        spec=spec,
        row=second_row,
        cooldown_until_by_symbol=cooldown_until_by_symbol,
    )

    assert [row["block_reasons"] for row in first_rows + second_rows] == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_cooldown"],
    ]
    assert [row["max_fill_fraction"] for row in first_rows + second_rows] == [0.0, 0.0]
