from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.derived import DerivedFeature
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.derived_arithmetic import (
    ARITHMETIC_DERIVED_OPS,
    arithmetic_expression,
)
from sis.research.strategy_lab.authoring.derived_bands_channels import (
    BANDS_CHANNEL_DERIVED_OPS,
    bands_channel_expression,
)
from sis.research.strategy_lab.authoring.derived_cross_sectional import (
    CROSS_SECTIONAL_DERIVED_OPS,
    cross_sectional_expression,
)
from sis.research.strategy_lab.authoring.derived_drawdown import (
    DRAWDOWN_DERIVED_OPS,
    drawdown_expression,
)
from sis.research.strategy_lab.authoring.derived_execution_costs import (
    EXECUTION_COST_DERIVED_OPS,
    execution_cost_expression,
)
from sis.research.strategy_lab.authoring.derived_external_signals import (
    EXTERNAL_SIGNAL_DERIVED_OPS,
    external_signal_expression,
)
from sis.research.strategy_lab.authoring.derived_liquidity import (
    LIQUIDITY_DERIVED_OPS,
    liquidity_expression,
)
from sis.research.strategy_lab.authoring.derived_quality import (
    QUALITY_DERIVED_OPS,
    quality_expression,
)
from sis.research.strategy_lab.authoring.derived_relative_correlation import (
    RELATIVE_CORRELATION_DERIVED_OPS,
    relative_correlation_expression,
)
from sis.research.strategy_lab.authoring.derived_return_transforms import (
    RETURN_TRANSFORM_DERIVED_OPS,
    return_transform_expression,
)
from sis.research.strategy_lab.authoring.derived_rolling_stats import (
    ROLLING_STAT_DERIVED_OPS,
    rolling_stat_expression,
)
from sis.research.strategy_lab.authoring.derived_rolling_risk_stats import (
    ROLLING_RISK_STAT_DERIVED_OPS,
    rolling_risk_stat_expression,
)
from sis.research.strategy_lab.authoring.derived_timestamp_features import (
    TIMESTAMP_DERIVED_OPS,
    timestamp_expression,
)
from sis.research.strategy_lab.authoring.derived_trend_transforms import (
    TREND_TRANSFORM_DERIVED_OPS,
    trend_transform_expression,
)
from sis.research.strategy_lab.authoring.derived_trend_indicators import (
    TREND_INDICATOR_DERIVED_OPS,
    trend_indicator_expression,
)
from sis.research.strategy_lab.authoring.derived_volume_indicators import (
    VOLUME_INDICATOR_DERIVED_OPS,
    volume_indicator_expression,
)


def derived_expression(feature: DerivedFeature) -> pl.Expr:
    if feature.op in ARITHMETIC_DERIVED_OPS:
        expr = arithmetic_expression(feature)
    elif feature.op in BANDS_CHANNEL_DERIVED_OPS:
        expr = bands_channel_expression(feature)
    elif feature.op in TREND_INDICATOR_DERIVED_OPS:
        expr = trend_indicator_expression(feature)
    elif feature.op in VOLUME_INDICATOR_DERIVED_OPS:
        expr = volume_indicator_expression(feature)
    elif feature.op in TIMESTAMP_DERIVED_OPS:
        expr = timestamp_expression(feature)
    elif feature.op in RETURN_TRANSFORM_DERIVED_OPS:
        expr = return_transform_expression(feature)
    elif feature.op in ROLLING_STAT_DERIVED_OPS:
        expr = rolling_stat_expression(feature)
    elif feature.op in ROLLING_RISK_STAT_DERIVED_OPS:
        expr = rolling_risk_stat_expression(feature)
    elif feature.op in TREND_TRANSFORM_DERIVED_OPS:
        expr = trend_transform_expression(feature)
    elif feature.op in RELATIVE_CORRELATION_DERIVED_OPS:
        expr = relative_correlation_expression(feature)
    elif feature.op in LIQUIDITY_DERIVED_OPS:
        expr = liquidity_expression(feature)
    elif feature.op in EXTERNAL_SIGNAL_DERIVED_OPS:
        expr = external_signal_expression(feature)
    elif feature.op in CROSS_SECTIONAL_DERIVED_OPS:
        expr = cross_sectional_expression(feature)
    elif feature.op in EXECUTION_COST_DERIVED_OPS:
        expr = execution_cost_expression(feature)
    elif feature.op in QUALITY_DERIVED_OPS:
        expr = quality_expression(feature)
    elif feature.op in DRAWDOWN_DERIVED_OPS:
        expr = drawdown_expression(feature)
    else:
        raise StrategyAuthoringValidationError(f"Unsupported derived feature op: {feature.op}")
    if feature.fill_null is not None:
        expr = expr.fill_null(feature.fill_null)
    return expr.alias(feature.name)


def apply_derived_features(frame: pl.DataFrame, spec: StrategyAuthoringSpec) -> pl.DataFrame:
    if not spec.rules.derived_features:
        return frame
    derived = frame.sort(["canonical_symbol", "ts"])
    for feature in spec.rules.derived_features:
        derived = derived.with_columns(derived_expression(feature))
    return derived
