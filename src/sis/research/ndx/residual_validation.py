from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import statistics
from typing import Any, Literal

import polars as pl

from sis.research.ndx.artifacts import (
    DAG_ID,
    read_json,
    sha256_file,
    sha256_json,
    utc_now_iso,
    write_json,
)
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS, SOURCE_TIMESTAMP_COLUMNS
from sis.research.ndx.leakage import ISO_TS_FORMAT, BANNED_MODEL_INPUT_COLUMNS
from sis.research.ndx.start_conditions import require_layer23_start_conditions


ResidualValidationDecision = Literal[
    "APPROVE_STRATEGY_LAB_EXPORT",
    "REVISE_2_3",
    "REVISE_2_2",
    "REJECT_RESIDUAL",
]
CounterDagStatus = Literal["blocked", "survives_for_research_only", "deferred", "not_applicable"]

DEFAULT_THRESHOLDS = {
    "approval_min_residual_rows": 60,
    "approval_min_era_count": 3,
    "approval_min_rows_per_era": 10,
    "approval_min_combined_variance_retention": 0.25,
    "approval_min_abs_neutralized_ic": 0.02,
    "reject_max_combined_variance_retention": 0.25,
    "reject_max_abs_neutralized_ic": 0.01,
}
REQUIRED_ARTIFACTS = {
    "source_resolution": "source_resolution/data_source_resolution.json",
    "feature_panel": "ndx_feature_panel.parquet",
    "feature_manifest": "ndx_feature_manifest.json",
    "residuals": "open_gap_residuals.parquet",
    "residual_manifest": "open_gap_residual_manifest.json",
    "diagnostics": "../reports/ndx_residual_diagnostics.json",
    "neutralized_residuals": "../reports/neutralized_residuals.parquet",
    "neutralization_pre_report": "../reports/ndx_neutralization_pre_report.md",
    "counter_dag_skeleton": "../reports/ndx_counter_dag_refutation_skeleton.md",
}
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


@dataclass(frozen=True)
class ResidualValidationResult:
    summary_path: Path
    decision_path: Path
    report_path: Path
    counter_dag_report_path: Path
    decision: ResidualValidationDecision
    reason_codes: list[str]


def run_residual_validation_gate(
    *,
    root: Path,
    artifact_dir: Path,
    reports_dir: Path,
    out_dir: Path,
    thresholds: dict[str, float] | None = None,
) -> ResidualValidationResult:
    effective_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    reason_codes: list[str] = []
    start_context: dict[str, Any] = {}
    try:
        start = require_layer23_start_conditions(root=root, artifact_dir=artifact_dir)
        start_context = {
            "layer_2_2_pack_hash": start.pack_hash,
            "exit_decision_path": start.decision_path.as_posix(),
            "freeze_manifest_path": start.freeze_manifest_path.as_posix(),
        }
    except Exception as exc:  # noqa: BLE001 - gate converts all start failures into decision artifacts.
        reason_codes.append("REVISE_2_2_START_CONDITIONS_FAILED")
        payload = _base_payload(
            decision="REVISE_2_2",
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context={"error": str(exc)},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    paths = _artifact_paths(artifact_dir=artifact_dir, reports_dir=reports_dir)
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        reason_codes.append("REVISE_2_3_MISSING_ARTIFACT")
        payload = _base_payload(
            decision="REVISE_2_3",
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context=start_context,
            artifact_checks={"missing": missing},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    try:
        checks = _load_and_check_artifacts(paths)
    except ValueError as exc:
        reason_codes.append(str(exc))
        decision: ResidualValidationDecision = (
            "REVISE_2_2" if str(exc).startswith("REVISE_2_2") else "REVISE_2_3"
        )
        payload = _base_payload(
            decision=decision,
            reason_codes=reason_codes,
            thresholds=effective_thresholds,
            start_context=start_context,
            artifact_checks={"error": str(exc)},
        )
        return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)

    metrics = _validation_metrics(
        residuals=checks["residuals"],
        neutralized=checks["neutralized"],
    )
    counter_dags = _counter_dag_statuses(metrics=metrics, artifact_checks=checks["artifact_checks"])
    reason_codes.extend(_artifact_reason_codes(checks["artifact_checks"]))
    reason_codes.extend(_metric_reason_codes(metrics, effective_thresholds))
    reason_codes.extend(
        status["reason_code"] for status in counter_dags.values() if status["status"] == "blocked"
    )
    decision = _decision_from_metrics(reason_codes, metrics, counter_dags, effective_thresholds)
    payload = _base_payload(
        decision=decision,
        reason_codes=reason_codes,
        thresholds=effective_thresholds,
        start_context=start_context,
        artifact_checks=checks["artifact_checks"],
        metrics=metrics,
        counter_dags=counter_dags,
    )
    return _write_outputs(out_dir=out_dir, reports_dir=reports_dir, payload=payload)


def _artifact_paths(*, artifact_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "source_resolution": artifact_dir / "source_resolution/data_source_resolution.json",
        "feature_panel": artifact_dir / "ndx_feature_panel.parquet",
        "feature_manifest": artifact_dir / "ndx_feature_manifest.json",
        "residuals": artifact_dir / "open_gap_residuals.parquet",
        "residual_manifest": artifact_dir / "open_gap_residual_manifest.json",
        "diagnostics": reports_dir / "ndx_residual_diagnostics.json",
        "neutralized_residuals": reports_dir / "neutralized_residuals.parquet",
        "neutralization_pre_report": reports_dir / "ndx_neutralization_pre_report.md",
        "counter_dag_skeleton": reports_dir / "ndx_counter_dag_refutation_skeleton.md",
    }


def _load_and_check_artifacts(paths: dict[str, Path]) -> dict[str, Any]:
    source_resolution = read_json(paths["source_resolution"])
    feature_manifest = read_json(paths["feature_manifest"])
    residual_manifest = read_json(paths["residual_manifest"])
    diagnostics = read_json(paths["diagnostics"])
    feature_panel = pl.read_parquet(paths["feature_panel"])
    residuals = pl.read_parquet(paths["residuals"])
    neutralized = pl.read_parquet(paths["neutralized_residuals"])
    json_artifacts = [source_resolution, feature_manifest, residual_manifest, diagnostics]
    dag_ids = {str(item.get("dag_id")) for item in json_artifacts}
    if dag_ids != {DAG_ID}:
        raise ValueError("REVISE_2_2_DAG_ID_MISMATCH")
    dag_hashes = {str(item.get("dag_artifact_hash")) for item in json_artifacts}
    if len(dag_hashes) != 1 or "" in dag_hashes:
        raise ValueError("REVISE_2_2_DAG_ARTIFACT_HASH_MISMATCH")
    dag_hash = next(iter(dag_hashes))
    feature_manifest_hash = str(feature_manifest.get("feature_manifest_hash", ""))
    if not feature_manifest_hash:
        raise ValueError("REVISE_2_3_FEATURE_MANIFEST_HASH_MISSING")
    expected_feature_manifest_hash = sha256_json(
        {key: value for key, value in feature_manifest.items() if key != "feature_manifest_hash"}
    )
    if feature_manifest_hash != expected_feature_manifest_hash:
        raise ValueError("REVISE_2_3_FEATURE_MANIFEST_HASH_MISMATCH")
    for payload in (residual_manifest, diagnostics):
        if str(payload.get("feature_manifest_hash")) != feature_manifest_hash:
            raise ValueError("REVISE_2_3_FEATURE_MANIFEST_HASH_MISMATCH")
    if sha256_file(paths["feature_panel"]) != feature_manifest.get("feature_panel_hash"):
        raise ValueError("REVISE_2_3_FEATURE_PANEL_HASH_MISMATCH")
    if sha256_file(paths["residuals"]) != residual_manifest.get("residuals_hash"):
        raise ValueError("REVISE_2_3_RESIDUAL_HASH_MISMATCH")
    if sha256_file(paths["neutralized_residuals"]) != diagnostics.get("neutralized_residuals_hash"):
        raise ValueError("REVISE_2_3_NEUTRALIZED_RESIDUAL_HASH_MISMATCH")
    artifact_checks = {
        "lineage": "pass",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "feature_manifest_hash": feature_manifest_hash,
        "feature_panel_lineage": _frame_lineage_status(
            feature_panel,
            dag_hash=dag_hash,
            reason_code="FEATURE_PANEL_LINEAGE_MISMATCH",
        ),
        "residual_lineage": _frame_lineage_status(
            residuals,
            dag_hash=dag_hash,
            feature_manifest_hash=feature_manifest_hash,
            reason_code="RESIDUAL_LINEAGE_MISMATCH",
        ),
        "neutralized_lineage": _frame_lineage_status(
            neutralized,
            dag_hash=dag_hash,
            feature_manifest_hash=feature_manifest_hash,
            reason_code="NEUTRALIZED_LINEAGE_MISMATCH",
        ),
        "residual_neutralized_alignment": _residual_neutralized_alignment_status(
            residuals, neutralized
        ),
        "source_timestamp_audit": _source_timestamp_audit_status(feature_panel),
        "leakage": _feature_panel_leakage_status(feature_panel),
        "residual_training_window": _residual_training_window_status(residuals),
        "model_factor_columns": _factor_column_status(residual_manifest),
    }
    return {
        "artifact_checks": artifact_checks,
        "feature_panel": feature_panel,
        "residuals": residuals,
        "neutralized": neutralized,
        "feature_manifest": feature_manifest,
        "residual_manifest": residual_manifest,
        "diagnostics": diagnostics,
    }


def _frame_lineage_status(
    frame: pl.DataFrame,
    *,
    dag_hash: str,
    reason_code: str,
    feature_manifest_hash: str | None = None,
) -> dict[str, Any]:
    required = {"dag_id", "dag_artifact_hash"}
    if feature_manifest_hash is not None:
        required.add("feature_manifest_hash")
    missing = sorted(required - set(frame.columns))
    if missing:
        return {
            "status": "fail",
            "reason_code": reason_code,
            "missing_columns": missing,
            "mismatch_count": frame.height,
        }
    mismatch = frame.filter(
        (pl.col("dag_id") != DAG_ID)
        | (pl.col("dag_artifact_hash") != dag_hash)
        | (
            pl.lit(False)
            if feature_manifest_hash is None
            else pl.col("feature_manifest_hash") != feature_manifest_hash
        )
    ).height
    return {
        "status": "pass" if mismatch == 0 else "fail",
        "reason_code": "ok" if mismatch == 0 else reason_code,
        "missing_columns": [],
        "mismatch_count": mismatch,
    }


def _residual_neutralized_alignment_status(
    residuals: pl.DataFrame, neutralized: pl.DataFrame
) -> dict[str, Any]:
    if "date" not in residuals.columns or "date" not in neutralized.columns:
        return {
            "status": "fail",
            "reason_code": "RESIDUAL_NEUTRALIZED_ALIGNMENT_MISSING_DATE",
            "residual_row_count": residuals.height,
            "neutralized_row_count": neutralized.height,
        }
    residual_dates = [str(value) for value in residuals.sort("date")["date"].to_list()]
    neutralized_dates = [str(value) for value in neutralized.sort("date")["date"].to_list()]
    aligned = residual_dates == neutralized_dates
    return {
        "status": "pass" if aligned else "fail",
        "reason_code": "ok" if aligned else "RESIDUAL_NEUTRALIZED_ALIGNMENT_MISMATCH",
        "residual_row_count": residuals.height,
        "neutralized_row_count": neutralized.height,
    }


def _source_timestamp_audit_status(feature_panel: pl.DataFrame) -> dict[str, Any]:
    missing_source_columns = [
        column for column in SOURCE_TIMESTAMP_COLUMNS if column not in feature_panel.columns
    ]
    aggregate_late = _late_or_invalid_timestamp_count(feature_panel, "source_ts_max")
    per_source_late_counts = {
        column: _late_or_invalid_timestamp_count(feature_panel, column)
        for column in SOURCE_TIMESTAMP_COLUMNS
        if column in feature_panel.columns
    }
    source_ts_max_mismatch_count = (
        0
        if missing_source_columns
        else _source_ts_max_mismatch_count(feature_panel, SOURCE_TIMESTAMP_COLUMNS)
    )
    status = (
        "pass"
        if not missing_source_columns
        and aggregate_late == 0
        and all(count == 0 for count in per_source_late_counts.values())
        and source_ts_max_mismatch_count == 0
        else "fail"
    )
    reason = (
        "SOURCE_TIMESTAMP_AUDIT_MISSING"
        if missing_source_columns
        else "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS"
        if any(count > 0 for count in per_source_late_counts.values())
        else "SOURCE_TIMESTAMP_MAX_EXCEEDS_FEATURE_TS"
        if aggregate_late
        else "SOURCE_TIMESTAMP_MAX_MISMATCH"
        if source_ts_max_mismatch_count
        else "ok"
    )
    return {
        "status": status,
        "reason_code": reason,
        "missing_source_columns": missing_source_columns,
        "source_ts_max_late_count": aggregate_late,
        "per_source_late_counts": per_source_late_counts,
        "source_ts_max_mismatch_count": source_ts_max_mismatch_count,
    }


def _late_or_invalid_timestamp_count(feature_panel: pl.DataFrame, source_column: str) -> int:
    if not {source_column, "feature_ts"}.issubset(feature_panel.columns):
        return feature_panel.height
    parsed = feature_panel.select(
        [
            pl.col(source_column).str.to_datetime(ISO_TS_FORMAT, strict=False).alias("__source_ts"),
            pl.col("feature_ts").str.to_datetime(ISO_TS_FORMAT, strict=False).alias("__feature_ts"),
        ]
    )
    return parsed.filter(
        pl.col("__source_ts").is_null()
        | pl.col("__feature_ts").is_null()
        | (pl.col("__source_ts") > pl.col("__feature_ts"))
    ).height


def _source_ts_max_mismatch_count(feature_panel: pl.DataFrame, source_columns: list[str]) -> int:
    if not {"source_ts_max", *source_columns}.issubset(feature_panel.columns):
        return feature_panel.height
    parsed = feature_panel.select(
        [
            pl.col("source_ts_max")
            .str.to_datetime(ISO_TS_FORMAT, strict=False)
            .alias("__source_ts_max"),
            pl.max_horizontal(
                [
                    pl.col(column).str.to_datetime(ISO_TS_FORMAT, strict=False)
                    for column in source_columns
                ]
            ).alias("__computed_source_ts_max"),
        ]
    )
    return parsed.filter(
        pl.col("__source_ts_max").is_null()
        | pl.col("__computed_source_ts_max").is_null()
        | (pl.col("__source_ts_max") != pl.col("__computed_source_ts_max"))
    ).height


def _feature_panel_leakage_status(feature_panel: pl.DataFrame) -> dict[str, Any]:
    missing = [
        column
        for column in ("feature_ts", "source_ts_max", "source_tier", "dag_id", "dag_artifact_hash")
        if column not in feature_panel.columns
    ]
    late_or_invalid = (
        0 if missing else _late_or_invalid_timestamp_count(feature_panel, "source_ts_max")
    )
    return {
        "status": "pass" if not missing and late_or_invalid == 0 else "fail",
        "reason_code": "ok"
        if not missing and late_or_invalid == 0
        else "FEATURE_PANEL_LEAKAGE_CHECK_FAILED",
        "missing_columns": missing,
    }


def _residual_training_window_status(residuals: pl.DataFrame) -> dict[str, Any]:
    required = {"date", "model_window_end", "model_training_row_count"}
    missing = sorted(required - set(residuals.columns))
    if missing:
        return {
            "status": "fail",
            "reason_code": "RESIDUAL_TRAINING_WINDOW_MISSING",
            "missing_columns": missing,
        }
    invalid = residuals.filter(pl.col("model_window_end") >= pl.col("date")).height
    return {
        "status": "pass" if invalid == 0 else "fail",
        "reason_code": "ok" if invalid == 0 else "RESIDUAL_TRAINING_WINDOW_NOT_STRICTLY_PRIOR",
        "invalid_row_count": invalid,
    }


def _factor_column_status(residual_manifest: dict[str, Any]) -> dict[str, Any]:
    factor_columns = [str(item) for item in residual_manifest.get("factor_columns", [])]
    banned = sorted(BANNED_MODEL_INPUT_COLUMNS.intersection(factor_columns))
    suspicious = [
        column
        for column in factor_columns
        if column.endswith("_close") or "open_to_close" in column or column.startswith("future_")
    ]
    missing = sorted(set(MODEL_FACTOR_COLUMNS) - set(factor_columns))
    status = "pass" if not banned and not suspicious and not missing else "fail"
    return {
        "status": status,
        "reason_code": "ok" if status == "pass" else "MODEL_FACTOR_COLUMNS_INVALID",
        "factor_columns": factor_columns,
        "banned_columns": banned,
        "suspicious_columns": suspicious,
        "missing_expected_columns": missing,
    }


def _validation_metrics(*, residuals: pl.DataFrame, neutralized: pl.DataFrame) -> dict[str, Any]:
    raw = _float_series(residuals, "open_gap_residual")
    outcome = _float_series(residuals, "qqq_open_to_close_return")
    neutralized_columns = [
        column for column in neutralized.columns if column.endswith("_neutralized_residual")
    ]
    neutralized_metrics = {
        column: _residual_metric_bundle(_float_series(neutralized, column), outcome)
        for column in neutralized_columns
    }
    combined = _float_series(neutralized, "combined_neutralized_residual")
    raw_variance = _variance(raw)
    combined_variance = _variance(combined)
    return {
        "schema_version": "ndx_residual_validation_metrics.v1",
        "row_count": residuals.height,
        "missing_rate": _missing_rate(residuals, neutralized),
        "era_summary": _era_summary(residuals),
        "raw": _residual_metric_bundle(raw, outcome),
        "neutralized": neutralized_metrics,
        "combined": _residual_metric_bundle(combined, outcome)
        | {
            "variance_retention": _safe_ratio(combined_variance, raw_variance),
            "variance_shrinkage": 1.0 - _safe_ratio(combined_variance, raw_variance),
        },
    }


def _residual_metric_bundle(values: list[float], outcome: list[float]) -> dict[str, float | int]:
    return {
        "sample_count": len(values),
        "variance": _variance(values),
        "ic": _pearson(values, outcome),
        "rank_ic": _pearson(_ranks(values), _ranks(outcome)),
        "sign_stability": _sign_stability_ratio(values),
        "sign_flip_rate": _sign_flip_rate(values),
    }


def _metric_reason_codes(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
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
        max_abs_ic = _max_abs_neutralized_ic(metrics)
        if max_abs_ic < float(thresholds["reject_max_abs_neutralized_ic"]):
            reason_codes.append("KNOWN_FACTOR_MIRAGE")
    return reason_codes


def _artifact_reason_codes(artifact_checks: dict[str, Any]) -> list[str]:
    reason_codes: list[str] = []
    for value in artifact_checks.values():
        if not isinstance(value, dict):
            continue
        if value.get("status") != "fail":
            continue
        reason = str(value.get("reason_code", "")).strip()
        if reason and reason != "ok":
            reason_codes.append(reason)
    return reason_codes


def _decision_from_metrics(
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
        and _max_abs_neutralized_ic(metrics) >= float(thresholds["approval_min_abs_neutralized_ic"])
    ):
        return "APPROVE_STRATEGY_LAB_EXPORT"
    return "REVISE_2_3"


def _counter_dag_statuses(
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
            "notes": _counter_dag_note(counter_dag_id),
        }
    return statuses


def _counter_dag_note(counter_dag_id: str) -> str:
    if counter_dag_id == "SemiconductorOnly":
        return "Uses SMH proxy; SOX direct remains out of scope."
    if counter_dag_id == "DataSourceLag":
        return "Requires per-source timestamp audit, not only aggregate source_ts_max."
    return "Research-only validation status; not a causal proof."


def _base_payload(
    *,
    decision: ResidualValidationDecision,
    reason_codes: list[str],
    thresholds: dict[str, float],
    start_context: dict[str, Any] | None = None,
    artifact_checks: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    counter_dags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "ndx_residual_validation_summary.v1",
        "dag_id": DAG_ID,
        "created_at": utc_now_iso(),
        "decision": decision,
        "reason_codes": sorted(set(reason_codes)),
        "thresholds": thresholds,
        "start_context": start_context or {},
        "artifact_checks": artifact_checks or {},
        "metrics": metrics or {},
        "counter_dags": counter_dags or {},
        "scope": {
            "strategy_lab_export_written": False,
            "strategy_signals_written": False,
            "backtest_run": False,
            "paper_candidate_written": False,
            "paper_intent_preview_written": False,
            "live_order_written": False,
        },
    }


def _write_outputs(
    *,
    out_dir: Path,
    reports_dir: Path,
    payload: dict[str, Any],
) -> ResidualValidationResult:
    summary_path = write_json(out_dir / "residual_validation_summary.json", payload)
    decision_payload = {
        "schema_version": "ndx_residual_validation_decision.v1",
        "dag_id": DAG_ID,
        "decision_id": sha256_json(
            {
                "dag_id": DAG_ID,
                "decision": payload["decision"],
                "reason_codes": payload["reason_codes"],
                "created_at": payload["created_at"],
            }
        ),
        "decision": payload["decision"],
        "reason_codes": payload["reason_codes"],
        "summary_path": summary_path.as_posix(),
        "created_at": payload["created_at"],
        "permits_strategy_lab_research_only_export": payload["decision"]
        == "APPROVE_STRATEGY_LAB_EXPORT",
        "permits_backtest": False,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "permits_live_order": False,
    }
    decision_path = write_json(out_dir / "residual_validation_decision.json", decision_payload)
    report_path = _write_validation_report(
        reports_dir / "ndx_residual_validation_report.md",
        payload=payload,
        decision_path=decision_path,
    )
    counter_dag_report_path = _write_counter_dag_report(
        reports_dir / "ndx_counter_dag_refutation_report.md",
        payload=payload,
    )
    return ResidualValidationResult(
        summary_path=summary_path,
        decision_path=decision_path,
        report_path=report_path,
        counter_dag_report_path=counter_dag_report_path,
        decision=payload["decision"],
        reason_codes=list(payload["reason_codes"]),
    )


def _write_validation_report(path: Path, *, payload: dict[str, Any], decision_path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = payload.get("metrics", {})
    combined = metrics.get("combined", {}) if isinstance(metrics, dict) else {}
    path.write_text(
        "# NDX Layer 2.4 Residual Validation Report\n\n"
        f"- dag_id: {DAG_ID}\n"
        f"- decision: {payload['decision']}\n"
        f"- reason_codes: {', '.join(payload['reason_codes']) or 'none'}\n"
        f"- residual_row_count: {metrics.get('row_count', 'unknown') if isinstance(metrics, dict) else 'unknown'}\n"
        f"- combined_variance_retention: {combined.get('variance_retention', 'unknown')}\n"
        f"- permits_strategy_lab_research_only_export: {payload['decision'] == 'APPROVE_STRATEGY_LAB_EXPORT'}\n"
        f"- decision_artifact: {decision_path}\n"
        "- strategy_signals_written: false\n"
        "- backtest_run: false\n"
        "- paper_or_live_allowed: false\n",
        encoding="utf-8",
    )
    return path


def _write_counter_dag_report(path: Path, *, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = payload.get("counter_dags", {})
    lines = [
        "# NDX Layer 2.4 Counter-DAG Refutation Report",
        "",
        f"- dag_id: {DAG_ID}",
        f"- decision: {payload['decision']}",
        "",
        "| counter_dag | status | reason |",
        "| --- | --- | --- |",
    ]
    if isinstance(rows, dict) and rows:
        for key in COUNTER_DAG_IDS:
            item = rows.get(key, {})
            lines.append(
                f"| {key} | {item.get('status', 'missing')} | {item.get('reason_code', 'missing')} |"
            )
    else:
        lines.append(
            "| unavailable | not_applicable | validation did not reach counter-DAG scoring |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _float_series(frame: pl.DataFrame, column: str) -> list[float]:
    if column not in frame.columns:
        return []
    return [float(value) for value in frame[column].to_list() if value is not None]


def _missing_rate(*frames: pl.DataFrame) -> float:
    cells = sum(frame.height * len(frame.columns) for frame in frames)
    if cells == 0:
        return 1.0
    missing = sum(frame[column].null_count() for frame in frames for column in frame.columns)
    return missing / cells


def _variance(values: list[float]) -> float:
    return float(statistics.variance(values)) if len(values) > 1 else 0.0


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_den = sum((x - left_mean) ** 2 for x in left)
    right_den = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_den * right_den)
    return 0.0 if denominator == 0.0 else numerator / denominator


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        average_rank = (index + end - 1) / 2.0 + 1.0
        for original_index, _ in indexed[index:end]:
            ranks[original_index] = average_rank
        index = end
    return ranks


def _sign_stability_ratio(values: list[float]) -> float:
    if not values:
        return 0.0
    positive = sum(1 for value in values if value > 0)
    negative = sum(1 for value in values if value < 0)
    return max(positive, negative) / len(values)


def _sign_flip_rate(values: list[float]) -> float:
    signs = [1 if value > 0 else -1 if value < 0 else 0 for value in values]
    pairs = [(left, right) for left, right in zip(signs, signs[1:]) if left and right]
    if not pairs:
        return 0.0
    return sum(1 for left, right in pairs if left != right) / len(pairs)


def _era_summary(residuals: pl.DataFrame) -> dict[str, Any]:
    if "date" not in residuals.columns:
        return {"era_count": 0, "qualified_era_count": 0, "rows_by_era": {}}
    rows_by_era: dict[str, int] = {}
    for value in residuals["date"].to_list():
        text = str(value)
        era = text[:7]
        rows_by_era[era] = rows_by_era.get(era, 0) + 1
    return {
        "era_count": len(rows_by_era),
        "qualified_era_count": sum(1 for count in rows_by_era.values() if count >= 10),
        "rows_by_era": rows_by_era,
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _max_abs_neutralized_ic(metrics: dict[str, Any]) -> float:
    neutralized = metrics.get("neutralized", {})
    if not isinstance(neutralized, dict) or not neutralized:
        return 0.0
    return max(abs(float(item.get("ic", 0.0))) for item in neutralized.values())
