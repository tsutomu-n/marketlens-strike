from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DerivedFeature(BaseModel):
    name: str
    op: Literal[
        "add",
        "sub",
        "mul",
        "div",
        "ratio",
        "diff",
        "pct_diff",
        "abs",
        "neg",
        "max",
        "min",
        "mean",
        "true_range",
        "atr",
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_width",
        "bollinger_percent_b",
        "donchian_upper",
        "donchian_lower",
        "donchian_mid",
        "donchian_width",
        "keltner_upper",
        "keltner_lower",
        "keltner_width",
        "ichimoku_conversion",
        "ichimoku_base",
        "ichimoku_span_a",
        "ichimoku_span_b",
        "macd_line",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "obv",
        "volume_zscore",
        "ts_weekday",
        "ts_hour",
        "ts_month",
        "ts_day",
        "pct_change",
        "log_return",
        "lag",
        "rolling_return",
        "ewm_mean",
        "rsi",
        "rolling_min",
        "rolling_max",
        "rolling_sum",
        "rolling_mean",
        "rolling_std",
        "rolling_zscore",
        "rolling_percentile_rank",
        "rolling_volatility",
        "rolling_skew",
        "rolling_kurtosis",
        "annualized_volatility",
        "realized_variance",
        "downside_volatility",
        "sharpe_like",
        "sortino_like",
        "kelly_fraction",
        "historical_var",
        "expected_shortfall",
        "cumulative_return",
        "slope",
        "mean_reversion_score",
        "distance_from_ma",
        "rolling_corr",
        "rolling_beta",
        "rolling_spread_zscore",
        "tracking_error",
        "information_ratio",
        "rolling_autocorr",
        "order_flow_imbalance",
        "liquidity_depth_ratio",
        "spread_bps",
        "funding_bps",
        "carry_adjusted_return",
        "vol_risk_premium",
        "put_call_skew",
        "liquidity_stress",
        "net_exchange_flow",
        "onchain_activity_ratio",
        "sentiment_weighted_score",
        "event_surprise",
        "fundamental_value_gap",
        "risk_adjusted_score",
        "inverse_volatility_weight",
        "cross_sectional_rank",
        "cross_sectional_zscore",
        "cross_sectional_demean",
        "group_cross_sectional_rank",
        "group_cross_sectional_zscore",
        "group_cross_sectional_demean",
        "queue_position_score",
        "latency_penalty_bps",
        "maker_taker_fee_edge_bps",
        "borrow_cost_bps",
        "borrow_availability_ratio",
        "tax_drag_bps",
        "rebalance_drift",
        "freshness_score",
        "staleness_bps",
        "data_quality_blend",
        "ensemble_vote_count",
        "ensemble_vote_ratio",
        "regime_transition_score",
        "drawdown_from_peak",
        "rolling_max_drawdown",
        "drawdown_duration",
        "turnover_pressure",
        "capacity_usage_ratio",
        "correlation_crowding_score",
    ]
    columns: list[str] = Field(default_factory=list)
    value: float | None = None
    window: int | None = None
    fill_null: float | None = None

    @model_validator(mode="after")
    def validate_derived_feature(self) -> DerivedFeature:
        if not self.name.strip():
            raise ValueError("rules.derived_features[].name must be non-empty")
        if not self.columns or any(not column.strip() for column in self.columns):
            raise ValueError(f"rules.derived_features.{self.name}.columns must be non-empty")
        if self.op in {
            "abs",
            "neg",
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "macd_line",
            "stochastic_d",
            "volume_zscore",
            "ts_weekday",
            "ts_hour",
            "ts_month",
            "ts_day",
            "pct_change",
            "log_return",
            "cumulative_return",
            "freshness_score",
            "staleness_bps",
            "drawdown_from_peak",
            "rolling_max_drawdown",
            "drawdown_duration",
            "lag",
            "rolling_return",
            "ewm_mean",
            "rsi",
            "rolling_min",
            "rolling_max",
            "rolling_sum",
            "rolling_mean",
            "rolling_std",
            "rolling_zscore",
            "rolling_percentile_rank",
            "rolling_volatility",
            "rolling_skew",
            "rolling_kurtosis",
            "annualized_volatility",
            "realized_variance",
            "downside_volatility",
            "sharpe_like",
            "sortino_like",
            "kelly_fraction",
            "historical_var",
            "expected_shortfall",
            "slope",
            "mean_reversion_score",
            "distance_from_ma",
            "rolling_autocorr",
        }:
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires one column"
                )
        if self.op in {"sub", "div", "ratio", "diff", "pct_diff"}:
            if len(self.columns) != 2 and self.value is None:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns or value"
                )
        if self.op in {
            "rolling_corr",
            "rolling_beta",
            "rolling_spread_zscore",
            "tracking_error",
            "information_ratio",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns"
                )
        if self.op in {
            "order_flow_imbalance",
            "liquidity_depth_ratio",
            "spread_bps",
            "carry_adjusted_return",
            "vol_risk_premium",
            "put_call_skew",
            "net_exchange_flow",
            "onchain_activity_ratio",
            "sentiment_weighted_score",
            "event_surprise",
            "fundamental_value_gap",
            "risk_adjusted_score",
            "group_cross_sectional_rank",
            "group_cross_sectional_zscore",
            "group_cross_sectional_demean",
            "queue_position_score",
            "maker_taker_fee_edge_bps",
            "borrow_cost_bps",
            "borrow_availability_ratio",
            "tax_drag_bps",
            "rebalance_drift",
            "regime_transition_score",
            "turnover_pressure",
            "capacity_usage_ratio",
            "correlation_crowding_score",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires two columns"
                )
        if self.op in {"data_quality_blend", "ensemble_vote_count", "ensemble_vote_ratio"}:
            if len(self.columns) < 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires at least one column"
                )
        if self.op == "latency_penalty_bps":
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.latency_penalty_bps requires one column"
                )
        if self.op in {
            "inverse_volatility_weight",
            "cross_sectional_rank",
            "cross_sectional_zscore",
            "cross_sectional_demean",
        }:
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires one column"
                )
        if self.op in {
            "group_cross_sectional_rank",
            "group_cross_sectional_zscore",
            "group_cross_sectional_demean",
        }:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires score and group columns"
                )
        if self.op == "funding_bps":
            if len(self.columns) != 1:
                raise ValueError(
                    f"rules.derived_features.{self.name}.funding_bps requires one column"
                )
        if self.op == "liquidity_stress":
            if len(self.columns) != 3:
                raise ValueError(
                    f"rules.derived_features.{self.name}.liquidity_stress requires bid, ask, depth columns"
                )
        if self.op == "obv":
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.obv requires close and volume columns"
                )
        if self.op in {"donchian_upper", "donchian_lower", "donchian_mid", "donchian_width"}:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high and low columns"
                )
        if self.op in {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_b"}:
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high and low columns"
                )
        if self.op == "ichimoku_span_a":
            if len(self.columns) != 2:
                raise ValueError(
                    f"rules.derived_features.{self.name}.ichimoku_span_a requires conversion and base columns"
                )
        if self.op in {
            "true_range",
            "atr",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
            "stochastic_k",
            "adx",
        }:
            if len(self.columns) != 3:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires high, low, close columns"
                )
        if self.op in {
            "atr",
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "donchian_upper",
            "donchian_lower",
            "donchian_mid",
            "donchian_width",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
            "ichimoku_conversion",
            "ichimoku_base",
            "ichimoku_span_b",
            "macd_line",
            "stochastic_k",
            "stochastic_d",
            "adx",
            "volume_zscore",
            "lag",
            "rolling_return",
            "ewm_mean",
            "rsi",
            "rolling_min",
            "rolling_max",
            "rolling_sum",
            "rolling_mean",
            "rolling_std",
            "rolling_zscore",
            "rolling_percentile_rank",
            "rolling_volatility",
            "rolling_skew",
            "rolling_kurtosis",
            "annualized_volatility",
            "realized_variance",
            "downside_volatility",
            "sharpe_like",
            "sortino_like",
            "kelly_fraction",
            "historical_var",
            "expected_shortfall",
            "slope",
            "mean_reversion_score",
            "distance_from_ma",
            "rolling_corr",
            "rolling_beta",
            "rolling_spread_zscore",
            "tracking_error",
            "information_ratio",
            "rolling_autocorr",
            "drawdown_from_peak",
            "rolling_max_drawdown",
            "drawdown_duration",
        }:
            if self.window is None or self.window <= 0:
                raise ValueError(
                    f"rules.derived_features.{self.name}.{self.op} requires positive window"
                )
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"rules.derived_features.{self.name}.value must be finite")
        if self.op in {
            "bollinger_upper",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_percent_b",
            "keltner_upper",
            "keltner_lower",
            "keltner_width",
        } and (self.value is not None and self.value < 0):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires non-negative value"
            )
        if self.op == "macd_line" and (
            self.value is None or self.value <= 0 or self.value <= float(self.window or 0)
        ):
            raise ValueError(
                f"rules.derived_features.{self.name}.macd_line requires value greater than window"
            )
        if self.op in {
            "annualized_volatility",
            "sharpe_like",
            "sortino_like",
            "tracking_error",
            "information_ratio",
        } and (self.value is not None and self.value <= 0):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires positive value"
            )
        if self.op in {"historical_var", "expected_shortfall"} and (
            self.value is not None and not 0.0 < self.value < 1.0
        ):
            raise ValueError(
                f"rules.derived_features.{self.name}.{self.op} requires value between 0 and 1"
            )
        if self.fill_null is not None and not math.isfinite(self.fill_null):
            raise ValueError(f"rules.derived_features.{self.name}.fill_null must be finite")
        return self
