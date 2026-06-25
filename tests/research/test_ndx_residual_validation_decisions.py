from __future__ import annotations

from sis.research.ndx.residual_validation_decisions import COUNTER_DAG_IDS
from sis.research.ndx.residual_validation_decisions import counter_dag_note
from sis.research.ndx.residual_validation_decisions import counter_dag_statuses
from sis.research.ndx.residual_validation_decisions import decision_from_metrics
from sis.research.ndx.residual_validation_decisions import metric_reason_codes


THRESHOLDS = {
    "approval_min_residual_rows": 60,
    "approval_min_era_count": 3,
    "approval_min_rows_per_era": 10,
    "approval_min_combined_variance_retention": 0.25,
    "approval_min_abs_neutralized_ic": 0.02,
    "reject_max_combined_variance_retention": 0.25,
    "reject_max_abs_neutralized_ic": 0.01,
}


def _metrics(
    *,
    row_count: int = 90,
    missing_rate: float = 0.0,
    qualified_era_count: int = 3,
    variance_retention: float = 0.42,
    neutralized_ic: float = 0.03,
) -> dict[str, object]:
    return {
        "row_count": row_count,
        "missing_rate": missing_rate,
        "era_summary": {"qualified_era_count": qualified_era_count},
        "combined": {"variance_retention": variance_retention},
        "neutralized": {"broad": {"ic": neutralized_ic}},
    }


def test_metric_reason_codes_detect_sample_era_missing_and_mirage() -> None:
    reasons = metric_reason_codes(
        _metrics(
            row_count=12,
            missing_rate=0.1,
            qualified_era_count=1,
            variance_retention=0.1,
            neutralized_ic=0.005,
        ),
        THRESHOLDS,
    )

    assert reasons == [
        "INSUFFICIENT_VALIDATION_SAMPLE",
        "VALIDATION_MISSING_VALUES",
        "INSUFFICIENT_VALIDATION_ERAS",
        "KNOWN_FACTOR_MIRAGE",
    ]


def test_decision_from_metrics_preserves_precedence() -> None:
    passing_counter_dags = {
        "BroadMarketOnly": {"status": "survives_for_research_only"},
    }

    assert (
        decision_from_metrics([], _metrics(), passing_counter_dags, THRESHOLDS)
        == "APPROVE_STRATEGY_LAB_EXPORT"
    )
    assert (
        decision_from_metrics(
            ["SOURCE_TIMESTAMP_AUDIT_MISSING", "KNOWN_FACTOR_MIRAGE"],
            _metrics(variance_retention=0.1, neutralized_ic=0.005),
            passing_counter_dags,
            THRESHOLDS,
        )
        == "REVISE_2_3"
    )
    assert (
        decision_from_metrics(
            ["KNOWN_FACTOR_MIRAGE"],
            _metrics(variance_retention=0.1, neutralized_ic=0.005),
            passing_counter_dags,
            THRESHOLDS,
        )
        == "REJECT_RESIDUAL"
    )
    assert (
        decision_from_metrics(
            [],
            _metrics(),
            {"DataSourceLag": {"status": "blocked"}},
            THRESHOLDS,
        )
        == "REVISE_2_3"
    )


def test_counter_dag_statuses_preserve_order_and_blocking_rules() -> None:
    statuses = counter_dag_statuses(
        metrics=_metrics(variance_retention=0.1),
        artifact_checks={
            "source_timestamp_audit": {
                "status": "fail",
                "reason_code": "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS",
            }
        },
    )

    assert list(statuses) == COUNTER_DAG_IDS
    assert statuses["BroadMarketOnly"]["status"] == "blocked"
    assert statuses["BroadMarketOnly"]["reason_code"] == "BROADMARKETONLY_EXPLAINS_RESIDUAL"
    assert statuses["DataSourceLag"]["status"] == "blocked"
    assert statuses["DataSourceLag"]["reason_code"] == "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS"
    assert statuses["ETFTrackingNoise"]["status"] == "deferred"
    assert (
        statuses["ETFTrackingNoise"]["reason_code"] == "ETFTRACKINGNOISE_DEFERRED_NO_DIRECT_INPUT"
    )
    assert (
        counter_dag_note("SemiconductorOnly") == "Uses SMH proxy; SOX direct remains out of scope."
    )
    assert (
        counter_dag_note("DataSourceLag")
        == "Requires per-source timestamp audit, not only aggregate source_ts_max."
    )
