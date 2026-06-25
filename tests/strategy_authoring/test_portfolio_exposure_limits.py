from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_limits import (
    _apply_portfolio_exposure_limits,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _spec(tmp_path: Path, portfolio_yaml: str) -> object:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        f"""
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: portfolio_exposure_limits_direct_v1
  strategy_family: portfolio_exposure_limits_direct
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
  reason_code: exposure_limits_direct_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_portfolio_exposure_limits_return_original_rows_when_disabled(tmp_path) -> None:
    rows = [{"side": "long", "position_weight": 0.5}]

    selected = _apply_portfolio_exposure_limits(
        rows,
        _spec(tmp_path, "    exposure_limits_enabled: false"),
    )

    assert selected is rows


def test_portfolio_exposure_limits_block_lower_ranked_excess_gross_weight(tmp_path) -> None:
    selected = _apply_portfolio_exposure_limits(
        [
            {
                "execution_symbol": "HOLD100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "none",
                "position_weight": 0.0,
            },
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
        ],
        _spec(
            tmp_path,
            "    max_total_position_weight: 1.0\n    max_symbol_position_weight: 1.0\n",
        ),
    )

    assert [(row["execution_symbol"], row["side"]) for row in selected] == [
        ("HOLD100", "none"),
        ("LOW100", "none"),
        ("HIGH100", "long"),
    ]
    assert selected[1]["block_reasons"] == ["portfolio_total_exposure_limit"]
