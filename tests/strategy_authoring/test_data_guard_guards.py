from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.data_guard_guards import (
    _data_guard_block_reason,
)

from .helpers import load_authoring_spec, template_yaml


def _spec_with_rules(tmp_path, rules_yaml: str):
    spec_path = tmp_path / "data-guard-spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n" + rules_yaml,
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_data_guard_block_reason_returns_none_when_disabled(tmp_path) -> None:
    spec = _spec_with_rules(tmp_path, "")

    assert _data_guard_block_reason({"feature_age_minutes": 999}, spec) is None


def test_data_guard_block_reason_preserves_priority_and_valid_behavior(tmp_path) -> None:
    spec = _spec_with_rules(
        tmp_path,
        "  data_guard:\n"
        "    max_feature_age_minutes: 30\n"
        "    min_source_confidence: 0.8\n"
        "    min_venue_quality_score: 0.7\n"
        "    max_staleness_bps: 5\n"
        "    max_regime_transition_score: 0.4\n",
    )

    assert _data_guard_block_reason({}, spec) == "data_guard_feature_age_missing"
    assert (
        _data_guard_block_reason(
            {
                "feature_age_minutes": 10,
                "source_confidence": 0.9,
                "venue_quality_score": 0.6,
                "staleness_bps": 10.0,
                "regime_transition_score": 0.9,
            },
            spec,
        )
        == "data_guard_venue_quality_too_low"
    )
    assert (
        _data_guard_block_reason(
            {
                "feature_age_minutes": 10,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
                "staleness_bps": 1.0,
                "regime_transition_score": 0.1,
            },
            spec,
        )
        is None
    )
