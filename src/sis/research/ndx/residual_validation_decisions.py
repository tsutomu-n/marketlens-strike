from __future__ import annotations

from typing import Any, Literal

from sis.research.ndx.residual_validation_metrics import max_abs_neutralized_ic


ResidualValidationDecision = Literal[
    "APPROVE_STRATEGY_LAB_EXPORT",
    "REVISE_2_3",
    "REVISE_2_2",
    "REJECT_RESIDUAL",
]
CounterDagStatus = Literal["blocked", "survives_for_research_only", "deferred", "not_applicable"]

COUNTER_DAG_IDS = [
    "BroadMarketOnly",
    "RatesOnly",
    "SemiconductorOnly",
    "MegaCapOnly",
    "VolRegimeOnly",
    "ETFTrackingNoise",
    "FuturesPriceDiscovery",
    "IndexMethodologyEvent",
    "MacroEvent",
    "CalendarEffect",
    "SelectionBias",
    "DataSourceLag",
]


def metric_reason_codes(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    reason_codes: list[str] = []
    if int(metrics["row_count"]) < int(thresholds["approval_min_residual_rows"]):
        reason_codes.append("INSUFFICIENT_VALIDATION_SAMPLE")
    if float(metrics["missing_rate"]) != 0.0:
        reason_codes.append("VALIDATION_MISSING_VALUES")
    if int(metrics["era_summary"]["qualified_era_count"]) < int(
        thresholds["approval_min_era_count"]
    ):
        reason_codes.append("INSUFFICIENT_VALIDATION_ERAS")
    if float(metrics["combined"]["variance_retention"]) < float(
        thresholds["reject_max_combined_variance_retention"]
    ):
        max_abs_ic = max_abs_neutralized_ic(metrics)
        if max_abs_ic < float(thresholds["reject_max_abs_neutralized_ic"]):
            reason_codes.append("KNOWN_FACTOR_MIRAGE")
    return reason_codes


def decision_from_metrics(
    reason_codes: list[str],
    metrics: dict[str, Any],
    counter_dags: dict[str, dict[str, Any]],
    thresholds: dict[str, float],
) -> ResidualValidationDecision:
    revise_codes = {
        "SOURCE_TIMESTAMP_AUDIT_MISSING",
        "SOURCE_TIMESTAMP_MAX_EXCEEDS_FEATURE_TS",
        "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS",
        "SOURCE_TIMESTAMP_MAX_MISMATCH",
        "FEATURE_PANEL_LINEAGE_MISMATCH",
        "RESIDUAL_LINEAGE_MISMATCH",
        "NEUTRALIZED_LINEAGE_MISMATCH",
        "RESIDUAL_NEUTRALIZED_ALIGNMENT_MISSING_DATE",
        "RESIDUAL_NEUTRALIZED_ALIGNMENT_MISMATCH",
        "FEATURE_PANEL_LEAKAGE_CHECK_FAILED",
        "RESIDUAL_TRAINING_WINDOW_NOT_STRICTLY_PRIOR",
        "RESIDUAL_TRAINING_WINDOW_MISSING",
        "MODEL_FACTOR_COLUMNS_INVALID",
        "VALIDATION_MISSING_VALUES",
        "INSUFFICIENT_VALIDATION_SAMPLE",
        "INSUFFICIENT_VALIDATION_ERAS",
    }
    if any(code in reason_codes for code in revise_codes):
        return "REVISE_2_3"
    if "KNOWN_FACTOR_MIRAGE" in reason_codes:
        return "REJECT_RESIDUAL"
    if any(item["status"] == "blocked" for item in counter_dags.values()):
        return "REVISE_2_3"
    if (
        int(metrics["row_count"]) >= int(thresholds["approval_min_residual_rows"])
        and float(metrics["missing_rate"]) == 0.0
        and int(metrics["era_summary"]["qualified_era_count"])
        >= int(thresholds["approval_min_era_count"])
        and float(metrics["combined"]["variance_retention"])
        >= float(thresholds["approval_min_combined_variance_retention"])
        and max_abs_neutralized_ic(metrics) >= float(thresholds["approval_min_abs_neutralized_ic"])
    ):
        return "APPROVE_STRATEGY_LAB_EXPORT"
    return "REVISE_2_3"


def counter_dag_statuses(
    *,
    metrics: dict[str, Any],
    artifact_checks: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for counter_dag_id in COUNTER_DAG_IDS:
        status: CounterDagStatus = "survives_for_research_only"
        reason_code = f"{counter_dag_id.upper()}_SURVIVES_FOR_RESEARCH_ONLY"
        if counter_dag_id in {
            "ETFTrackingNoise",
            "FuturesPriceDiscovery",
            "IndexMethodologyEvent",
            "MacroEvent",
            "CalendarEffect",
        }:
            status = "deferred"
            reason_code = f"{counter_dag_id.upper()}_DEFERRED_NO_DIRECT_INPUT"
        if (
            counter_dag_id == "DataSourceLag"
            and artifact_checks["source_timestamp_audit"]["status"] != "pass"
        ):
            status = "blocked"
            reason_code = str(artifact_checks["source_timestamp_audit"]["reason_code"])
        if (
            counter_dag_id
            in {
                "BroadMarketOnly",
                "RatesOnly",
                "SemiconductorOnly",
                "MegaCapOnly",
                "VolRegimeOnly",
            }
            and float(metrics["combined"]["variance_retention"]) < 0.25
        ):
            status = "blocked"
            reason_code = f"{counter_dag_id.upper()}_EXPLAINS_RESIDUAL"
        statuses[counter_dag_id] = {
            "status": status,
            "reason_code": reason_code,
            "notes": counter_dag_note(counter_dag_id),
        }
    return statuses


def counter_dag_note(counter_dag_id: str) -> str:
    if counter_dag_id == "SemiconductorOnly":
        return "Uses SMH proxy; SOX direct remains out of scope."
    if counter_dag_id == "DataSourceLag":
        return "Requires per-source timestamp audit, not only aggregate source_ts_max."
    return "Research-only validation status; not a causal proof."
