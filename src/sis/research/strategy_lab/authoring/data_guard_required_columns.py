from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import DataGuardRules


def _data_guard_required_columns(data_guard: DataGuardRules) -> set[str]:
    columns: set[str] = set()
    for threshold, threshold_column, observed_column in (
        (
            data_guard.max_feature_age_minutes,
            data_guard.max_feature_age_minutes_column,
            data_guard.feature_age_column,
        ),
        (
            data_guard.min_source_confidence,
            data_guard.min_source_confidence_column,
            data_guard.source_confidence_column,
        ),
        (
            data_guard.min_venue_quality_score,
            data_guard.min_venue_quality_score_column,
            data_guard.venue_quality_score_column,
        ),
        (
            data_guard.max_staleness_bps,
            data_guard.max_staleness_bps_column,
            data_guard.staleness_bps_column,
        ),
        (
            data_guard.max_regime_transition_score,
            data_guard.max_regime_transition_score_column,
            data_guard.regime_transition_score_column,
        ),
    ):
        if (threshold is not None or threshold_column is not None) and observed_column is not None:
            columns.add(observed_column)
        if threshold_column is not None:
            columns.add(threshold_column)
    return columns
