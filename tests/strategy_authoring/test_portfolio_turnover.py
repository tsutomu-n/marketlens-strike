from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.compiler.portfolio_turnover import (
    _apply_portfolio_turnover_budget,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _spec(tmp_path: Path, *, portfolio_yaml: str) -> object:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        f"""
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: portfolio_turnover_direct_v1
  strategy_family: portfolio_turnover_direct
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
  reason_code: turnover_direct_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_portfolio_turnover_budget_blocks_lower_rank_rows_after_budget(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        portfolio_yaml="    max_turnover_weight_per_timestamp: 1.0\n",
    )

    rows = _apply_portfolio_turnover_budget(
        [
            {
                "ts_signal": "2026-01-01T00:00:00Z",
                "execution_symbol": "AAA100",
                "side": "long",
                "rank_score": 0.9,
                "_portfolio_turnover_weight": 0.6,
                "position_weight": 0.1,
            },
            {
                "ts_signal": "2026-01-01T00:00:00Z",
                "execution_symbol": "BBB100",
                "side": "long",
                "rank_score": 0.8,
                "_portfolio_turnover_weight": 0.5,
                "position_weight": 0.1,
            },
            {
                "ts_signal": "2026-01-01T00:00:00Z",
                "execution_symbol": "CCC100",
                "side": "long",
                "rank_score": 0.7,
                "_portfolio_turnover_weight": 0.4,
                "position_weight": 0.1,
            },
        ],
        spec,
    )

    assert [(row["execution_symbol"], row["side"]) for row in rows] == [
        ("BBB100", "none"),
        ("AAA100", "long"),
        ("CCC100", "long"),
    ]
    assert rows[0]["block_reasons"] == ["portfolio_turnover_budget_limit"]


def test_portfolio_turnover_budget_falls_back_to_position_weight(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        portfolio_yaml="    max_turnover_weight_per_timestamp: 0.9\n",
    )

    rows = _apply_portfolio_turnover_budget(
        [
            {
                "ts_signal": "2026-01-01T00:00:00Z",
                "execution_symbol": "AAA100",
                "side": "long",
                "rank_score": 0.9,
                "position_weight": 0.5,
            },
            {
                "ts_signal": "2026-01-01T00:00:00Z",
                "execution_symbol": "BBB100",
                "side": "long",
                "rank_score": 0.8,
                "position_weight": 0.5,
            },
        ],
        spec,
    )

    assert [(row["execution_symbol"], row["side"]) for row in rows] == [
        ("BBB100", "none"),
        ("AAA100", "long"),
    ]


def test_portfolio_turnover_budget_returns_original_rows_when_disabled(tmp_path) -> None:
    spec = _spec(tmp_path, portfolio_yaml="    {}\n")
    rows = [{"side": "long", "position_weight": 0.5}]

    selected = _apply_portfolio_turnover_budget(rows, spec)

    assert selected is rows
