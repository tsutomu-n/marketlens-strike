from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_data_guard_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "max_feature_age_minutes",
        "max_feature_age_minutes_column",
        "feature_age_column",
        "min_source_confidence",
        "min_source_confidence_column",
        "source_confidence_column",
        "min_venue_quality_score",
        "min_venue_quality_score_column",
        "venue_quality_score_column",
        "max_staleness_bps",
        "max_staleness_bps_column",
        "staleness_bps_column",
        "max_regime_transition_score",
        "max_regime_transition_score_column",
        "regime_transition_score_column",
    }

    assert not any(name in text for name in forbidden)
