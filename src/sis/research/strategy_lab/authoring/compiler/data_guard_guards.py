from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _non_negative_value,
    _optional_float_from_row,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _data_guard_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    guard = spec.rules.data_guard
    if not guard.enabled:
        return None
    feature_age = _optional_float_from_row(row, guard.feature_age_column)
    max_feature_age = _non_negative_value(
        row,
        fixed=guard.max_feature_age_minutes,
        column=guard.max_feature_age_minutes_column,
        field_name="rules.data_guard.max_feature_age_minutes",
    )
    if max_feature_age is not None:
        if feature_age is None:
            return "data_guard_feature_age_missing"
        if feature_age > max_feature_age:
            return "data_guard_feature_age_too_old"
    source_confidence = _optional_float_from_row(row, guard.source_confidence_column)
    min_source_confidence = _unit_interval_value(
        row,
        fixed=guard.min_source_confidence,
        column=guard.min_source_confidence_column,
        field_name="rules.data_guard.min_source_confidence",
    )
    if min_source_confidence is not None:
        if source_confidence is None:
            return "data_guard_source_confidence_missing"
        if source_confidence < min_source_confidence:
            return "data_guard_source_confidence_too_low"
    venue_quality = _optional_float_from_row(row, guard.venue_quality_score_column)
    min_venue_quality = _unit_interval_value(
        row,
        fixed=guard.min_venue_quality_score,
        column=guard.min_venue_quality_score_column,
        field_name="rules.data_guard.min_venue_quality_score",
    )
    if min_venue_quality is not None:
        if venue_quality is None:
            return "data_guard_venue_quality_missing"
        if venue_quality < min_venue_quality:
            return "data_guard_venue_quality_too_low"
    staleness_bps = _optional_float_from_row(row, guard.staleness_bps_column)
    max_staleness_bps = _non_negative_value(
        row,
        fixed=guard.max_staleness_bps,
        column=guard.max_staleness_bps_column,
        field_name="rules.data_guard.max_staleness_bps",
    )
    if max_staleness_bps is not None:
        if staleness_bps is None:
            return "data_guard_staleness_missing"
        if staleness_bps > max_staleness_bps:
            return "data_guard_staleness_too_high"
    regime_transition = _optional_float_from_row(row, guard.regime_transition_score_column)
    max_regime_transition = _non_negative_value(
        row,
        fixed=guard.max_regime_transition_score,
        column=guard.max_regime_transition_score_column,
        field_name="rules.data_guard.max_regime_transition_score",
    )
    if max_regime_transition is not None:
        if regime_transition is None:
            return "data_guard_regime_transition_missing"
        if regime_transition > max_regime_transition:
            return "data_guard_regime_transition_too_high"
    return None
