from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_net import (
    _apply_portfolio_group_net_exposure_limit,
    _apply_portfolio_net_exposure_limit,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _spec(tmp_path: Path) -> object:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: portfolio_exposure_net_direct_v1
  strategy_family: portfolio_exposure_net_direct
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
  reason_code: exposure_net_direct_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_portfolio_net_exposure_limit_blocks_lowest_rank_overweight_side(tmp_path) -> None:
    spec = _spec(tmp_path)

    accepted, blocked = _apply_portfolio_net_exposure_limit(
        [
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
        ],
        max_abs_net_position_weight=0.3,
        spec=spec,
    )

    assert [row["execution_symbol"] for row in accepted] == ["AAA100", "CCC100"]
    assert [(row["execution_symbol"], row["side"], row["block_reasons"]) for row in blocked] == [
        ("BBB100", "none", ["portfolio_net_exposure_limit"])
    ]


def test_portfolio_group_net_exposure_limit_blocks_within_overweight_group(tmp_path) -> None:
    spec = _spec(tmp_path)

    accepted, blocked = _apply_portfolio_group_net_exposure_limit(
        [
            {
                "execution_symbol": "AAA100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "long",
                "position_weight": 0.6,
                "rank_score": 0.9,
                "_portfolio_group": "tech",
            },
            {
                "execution_symbol": "BBB100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "long",
                "position_weight": 0.5,
                "rank_score": 0.3,
                "_portfolio_group": "tech",
            },
            {
                "execution_symbol": "CCC100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "short",
                "position_weight": 0.4,
                "rank_score": 0.8,
                "_portfolio_group": "tech",
            },
            {
                "execution_symbol": "DDD100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "long",
                "position_weight": 0.7,
                "rank_score": 0.2,
                "_portfolio_group": "energy",
            },
            {
                "execution_symbol": "EEE100",
                "ts_signal": "2026-01-01T00:00:00Z",
                "side": "short",
                "position_weight": 0.7,
                "rank_score": 0.1,
                "_portfolio_group": "energy",
            },
        ],
        max_group_abs_net_position_weight=0.3,
        spec=spec,
    )

    assert [row["execution_symbol"] for row in accepted] == [
        "AAA100",
        "CCC100",
        "DDD100",
        "EEE100",
    ]
    assert [(row["execution_symbol"], row["side"], row["block_reasons"]) for row in blocked] == [
        ("BBB100", "none", ["portfolio_group_net_exposure_limit"])
    ]


def test_portfolio_net_exposure_limit_returns_original_rows_when_disabled(tmp_path) -> None:
    spec = _spec(tmp_path)
    rows = [{"side": "long", "position_weight": 0.5}]

    accepted, blocked = _apply_portfolio_net_exposure_limit(
        rows,
        max_abs_net_position_weight=None,
        spec=spec,
    )

    assert accepted is rows
    assert blocked == []
