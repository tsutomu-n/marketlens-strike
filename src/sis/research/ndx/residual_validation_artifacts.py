from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from sis.research.ndx.artifacts import DAG_ID
from sis.research.ndx.artifacts import read_json
from sis.research.ndx.artifacts import sha256_file
from sis.research.ndx.artifacts import sha256_json
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS, SOURCE_TIMESTAMP_COLUMNS
from sis.research.ndx.leakage import ISO_TS_FORMAT, BANNED_MODEL_INPUT_COLUMNS


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


def artifact_paths(*, artifact_dir: Path, reports_dir: Path) -> dict[str, Path]:
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


def load_and_check_artifacts(paths: dict[str, Path]) -> dict[str, Any]:
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
        "feature_panel_lineage": frame_lineage_status(
            feature_panel,
            dag_hash=dag_hash,
            reason_code="FEATURE_PANEL_LINEAGE_MISMATCH",
        ),
        "residual_lineage": frame_lineage_status(
            residuals,
            dag_hash=dag_hash,
            feature_manifest_hash=feature_manifest_hash,
            reason_code="RESIDUAL_LINEAGE_MISMATCH",
        ),
        "neutralized_lineage": frame_lineage_status(
            neutralized,
            dag_hash=dag_hash,
            feature_manifest_hash=feature_manifest_hash,
            reason_code="NEUTRALIZED_LINEAGE_MISMATCH",
        ),
        "residual_neutralized_alignment": residual_neutralized_alignment_status(
            residuals, neutralized
        ),
        "source_timestamp_audit": source_timestamp_audit_status(feature_panel),
        "leakage": feature_panel_leakage_status(feature_panel),
        "residual_training_window": residual_training_window_status(residuals),
        "model_factor_columns": factor_column_status(residual_manifest),
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


def frame_lineage_status(
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


def residual_neutralized_alignment_status(
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


def source_timestamp_audit_status(feature_panel: pl.DataFrame) -> dict[str, Any]:
    missing_source_columns = [
        column for column in SOURCE_TIMESTAMP_COLUMNS if column not in feature_panel.columns
    ]
    aggregate_late = late_or_invalid_timestamp_count(feature_panel, "source_ts_max")
    per_source_late_counts = {
        column: late_or_invalid_timestamp_count(feature_panel, column)
        for column in SOURCE_TIMESTAMP_COLUMNS
        if column in feature_panel.columns
    }
    source_ts_max_mismatch_count = (
        0
        if missing_source_columns
        else source_ts_max_mismatch_count_for_columns(feature_panel, SOURCE_TIMESTAMP_COLUMNS)
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


def late_or_invalid_timestamp_count(feature_panel: pl.DataFrame, source_column: str) -> int:
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


def source_ts_max_mismatch_count_for_columns(
    feature_panel: pl.DataFrame, source_columns: list[str]
) -> int:
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


def feature_panel_leakage_status(feature_panel: pl.DataFrame) -> dict[str, Any]:
    missing = [
        column
        for column in ("feature_ts", "source_ts_max", "source_tier", "dag_id", "dag_artifact_hash")
        if column not in feature_panel.columns
    ]
    late_or_invalid = (
        0 if missing else late_or_invalid_timestamp_count(feature_panel, "source_ts_max")
    )
    return {
        "status": "pass" if not missing and late_or_invalid == 0 else "fail",
        "reason_code": "ok"
        if not missing and late_or_invalid == 0
        else "FEATURE_PANEL_LEAKAGE_CHECK_FAILED",
        "missing_columns": missing,
    }


def residual_training_window_status(residuals: pl.DataFrame) -> dict[str, Any]:
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


def factor_column_status(residual_manifest: dict[str, Any]) -> dict[str, Any]:
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


def artifact_reason_codes(artifact_checks: dict[str, Any]) -> list[str]:
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
