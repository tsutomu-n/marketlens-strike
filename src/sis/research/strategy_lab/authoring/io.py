from __future__ import annotations

from pathlib import Path

import yaml

from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)
from sis.research.strategy_lab.authoring.contracts.spec import (
    StrategyAuthoringBundleSpec,
    StrategyAuthoringSpec,
)


def load_authoring_spec(path: Path) -> StrategyAuthoringSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyAuthoringValidationError("spec must be a YAML object")
    return StrategyAuthoringSpec.model_validate(payload)


def load_authoring_bundle_spec(path: Path) -> StrategyAuthoringBundleSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyAuthoringValidationError("bundle spec must be a YAML object")
    return StrategyAuthoringBundleSpec.model_validate(payload)


def template_yaml() -> str:
    return """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_pullback_user_v1
  strategy_family: trend_pullback
  strategy_version: v1
  description: Long only trend pullback example for Strategy Lab paper research.
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
      country: US
      currency: USD
  run_profile_id: strategy_lab_research_only
data:
  feature_panel_path: data/research/feature_panel.parquet
  quote_data_path: data/normalized/quotes.parquet
  cost_model_path: data/research/venue_cost_matrix.csv
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: close_above_sma20
        op: is_true
      - column: vix_level
        op: lt
        value: 30
    any:
      - column: research_return_1d
        op: gt
        value: 0
      - column: research_return_4h
        op: gt
        value: 0
  hold:
    any:
      - column: vix_level
        op: gte
        value: 30
  exit:
    stop_loss_bps: 150
    min_stop_loss_bps: 50
    max_stop_loss_bps: 1000
    take_profit_bps: 300
    min_take_profit_bps: 100
    max_take_profit_bps: 1000
    trailing_stop_bps: 120
    trailing_stop_activation_bps: 0
    partial_take_profit_bps: 200
    partial_exit_fraction: 0.5
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  portfolio:
    max_signals_per_timestamp: 3
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
  confidence: 0.7
  reason_code: trend_pullback_authoring_v1
  hold_reason_code: risk_hold_v1
backtest:
  split_method: purged_walk_forward
  era_unit: trading_day
  label_horizon_minutes: 240
  purge_minutes: 0
  embargo_minutes: 0
  min_trade_count: 1
  primary_metric: total_return
  pass_thresholds:
    max_drawdown: -0.2
optimizer:
  parameter_sweep:
    rules.exit.stop_loss_bps: [100, 150]
    rules.exit.take_profit_bps: [250, 300]
  selection_metric: total_return
  selection_direction: maximize
  max_variants: 8
promotion:
  default_decision: hold
  allow_paper_preview: true
"""


def write_template(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template_yaml(), encoding="utf-8")
    return path
