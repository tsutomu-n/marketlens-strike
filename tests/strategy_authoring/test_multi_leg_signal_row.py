from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.multi_leg_signal_row import (
    _multi_leg_signal_row,
)

from .helpers import load_authoring_spec


def _multi_leg_spec(tmp_path):
    spec_path = tmp_path / "pair.yaml"
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: pair_trade_authoring_v1
  strategy_family: pair_trade
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 0.6
        reason_code: long_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.4
        reason_code: hedge_leg
  sizing:
    position_weight: 2.0
    notional_usd: 1000
  reason_code: pair_trade_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_multi_leg_signal_row_builds_one_hedge_leg_trade_row(tmp_path) -> None:
    spec = _multi_leg_spec(tmp_path)
    leg = spec.rules.multi_leg.legs[1]
    binding = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}[
        "BBB"
    ]
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    row = _multi_leg_signal_row(
        spec=spec,
        row={
            "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "canonical_symbol": "AAA",
            "trade_allowed": True,
            "research_return_1d": 0.02,
        },
        binding=binding,
        leg=leg,
        base_side="long",
        generated_at=generated_at,
        raw_score=0.8,
        rank=0.8,
        base_weight=2.0,
        base_notional=1000.0,
        group_id="group-1",
        leg_index=2,
        leg_count=2,
        anchor_symbol="AAA",
        default_entry_type=spec.rules.order.entry_type,
        default_time_in_force=spec.rules.order.time_in_force,
    )

    assert row["generated_at"] == generated_at
    assert row["execution_symbol"] == "BBB100"
    assert row["real_market_symbol"] == "BBB"
    assert row["side"] == "short"
    assert row["position_weight"] == 0.8
    assert row["notional_usd"] == 400.0
    assert row["multi_leg_group_id"] == "group-1"
    assert row["multi_leg_leg_index"] == 2
    assert row["multi_leg_leg_count"] == 2
    assert row["multi_leg_anchor_real_market_symbol"] == "AAA"
    assert row["reason_codes"] == ["pair_trade_v1", "multi_leg", "hedge_leg"]
