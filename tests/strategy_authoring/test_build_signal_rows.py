from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl

from sis.research.strategy_lab.authoring.compiler.build_signal_rows import (
    _build_signal_rows,
)

from .helpers import _feature_rows, load_authoring_spec, template_yaml


def _spec(tmp_path, yaml_text: str | None = None):
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml_text or template_yaml(), encoding="utf-8")
    return load_authoring_spec(spec_path)


def test_build_signal_rows_skips_missing_binding_and_emits_trade_row(tmp_path) -> None:
    spec = _spec(tmp_path)
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    qqq_row = _feature_rows()[0]
    missing_binding_row = qqq_row | {"canonical_symbol": "MSFT"}

    rows = _build_signal_rows(
        spec=spec,
        feature=pl.DataFrame([missing_binding_row, qqq_row]),
        generated_at=generated_at,
    )

    assert len(rows) == 1
    assert rows[0]["generated_at"] == generated_at
    assert rows[0]["real_market_symbol"] == "QQQ"
    assert rows[0]["side"] == "long"


def test_build_signal_rows_emits_hold_marker_before_trade_entry(tmp_path) -> None:
    spec = _spec(tmp_path)
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    hold_row = _feature_rows()[0] | {"vix_level": 31.0}

    rows = _build_signal_rows(
        spec=spec,
        feature=pl.DataFrame([hold_row]),
        generated_at=generated_at,
    )

    assert len(rows) == 1
    assert rows[0]["side"] == "none"
    assert rows[0]["reason_codes"] == ["risk_hold_v1"]
    assert rows[0]["block_reasons"] == ["hold_rule"]


def test_build_signal_rows_keeps_risk_throttle_cooldown_across_rows(tmp_path) -> None:
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
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    first_row, second_row, *_ = _feature_rows()
    first_row = first_row | {"strategy_drawdown": -0.20}
    second_row = second_row | {
        "ts": first_row["ts"] + timedelta(minutes=30),
        "strategy_drawdown": -0.05,
    }

    rows = _build_signal_rows(
        spec=spec,
        feature=pl.DataFrame([first_row, second_row]),
        generated_at=generated_at,
    )

    assert [row["block_reasons"] for row in rows] == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_cooldown"],
    ]
    assert [row["max_fill_fraction"] for row in rows] == [0.0, 0.0]
