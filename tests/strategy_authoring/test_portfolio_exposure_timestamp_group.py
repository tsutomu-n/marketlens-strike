from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_timestamp_group import (
    _apply_portfolio_exposure_timestamp_group_limits,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _spec(tmp_path: Path, portfolio_yaml: str) -> object:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        f"""
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: portfolio_exposure_timestamp_group_direct_v1
  strategy_family: portfolio_exposure_timestamp_group_direct
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  portfolio:
{portfolio_yaml}
  reason_code: exposure_timestamp_group_direct_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_portfolio_exposure_timestamp_group_blocks_gross_excess_by_rank(
    tmp_path,
) -> None:
    rows = [
        {
            "execution_symbol": "LOW100",
            "ts_signal": "2026-01-01T00:00:00Z",
            "side": "long",
            "position_weight": 0.6,
            "rank_score": 0.2,
        },
        {
            "execution_symbol": "HIGH100",
            "ts_signal": "2026-01-01T00:00:00Z",
            "side": "long",
            "position_weight": 0.6,
            "rank_score": 0.9,
        },
    ]

    selected = _apply_portfolio_exposure_timestamp_group_limits(
        rows,
        _spec(
            tmp_path,
            "    max_total_position_weight: 1.0\n    max_symbol_position_weight: 1.0\n",
        ),
    )

    assert [(row["execution_symbol"], row["side"]) for row in selected] == [
        ("LOW100", "none"),
        ("HIGH100", "long"),
    ]
    assert selected[0]["block_reasons"] == ["portfolio_total_exposure_limit"]


def test_portfolio_exposure_timestamp_group_applies_net_limit_after_gross_acceptance(
    tmp_path,
) -> None:
    rows = [
        {
            "execution_symbol": "AAA100",
            "ts_signal": "2026-01-01T00:00:00Z",
            "side": "long",
            "position_weight": 0.6,
            "rank_score": 0.9,
        },
        {
            "execution_symbol": "BBB100",
            "ts_signal": "2026-01-01T00:00:00Z",
            "side": "long",
            "position_weight": 0.5,
            "rank_score": 0.4,
        },
        {
            "execution_symbol": "CCC100",
            "ts_signal": "2026-01-01T00:00:00Z",
            "side": "short",
            "position_weight": 0.4,
            "rank_score": 0.8,
        },
    ]

    selected = _apply_portfolio_exposure_timestamp_group_limits(
        rows,
        _spec(tmp_path, "    max_abs_net_position_weight: 0.3\n"),
    )

    assert [(row["execution_symbol"], row["side"]) for row in selected] == [
        ("BBB100", "none"),
        ("AAA100", "long"),
        ("CCC100", "short"),
    ]
    assert selected[0]["block_reasons"] == ["portfolio_net_exposure_limit"]
