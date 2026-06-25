from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.risk_controls import DataGuardRules
from sis.research.strategy_lab.authoring.data_guard_required_columns import (
    _data_guard_required_columns,
)


def test_data_guard_required_columns_returns_empty_set_when_disabled() -> None:
    assert _data_guard_required_columns(DataGuardRules()) == set()


def test_data_guard_required_columns_collects_fixed_threshold_observed_columns() -> None:
    rules = DataGuardRules(
        max_feature_age_minutes=30.0,
        min_source_confidence=0.8,
        min_venue_quality_score=0.7,
        max_staleness_bps=5.0,
        max_regime_transition_score=0.4,
    )

    assert _data_guard_required_columns(rules) == {
        "feature_age_minutes",
        "source_confidence",
        "venue_quality_score",
        "staleness_bps",
        "regime_transition_score",
    }


def test_data_guard_required_columns_collects_row_threshold_columns() -> None:
    rules = DataGuardRules(
        max_feature_age_minutes_column="row_max_feature_age",
        min_source_confidence_column="row_min_source_confidence",
        min_venue_quality_score_column="row_min_venue_quality",
        max_staleness_bps_column="row_max_staleness",
        max_regime_transition_score_column="row_max_regime_transition",
    )

    assert _data_guard_required_columns(rules) == {
        "feature_age_minutes",
        "row_max_feature_age",
        "source_confidence",
        "row_min_source_confidence",
        "venue_quality_score",
        "row_min_venue_quality",
        "staleness_bps",
        "row_max_staleness",
        "regime_transition_score",
        "row_max_regime_transition",
    }


def test_data_guard_required_columns_collects_strict_profile_defaults() -> None:
    rules = DataGuardRules(profile="strict")

    assert _data_guard_required_columns(rules) == {
        "feature_age_minutes",
        "source_confidence",
        "venue_quality_score",
        "staleness_bps",
        "regime_transition_score",
    }
