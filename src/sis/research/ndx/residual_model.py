from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import polars as pl

from sis.research.ndx.artifacts import (
    DAG_ID,
    read_json,
    sha256_file,
    sha256_json,
    utc_now_iso,
    write_json,
)
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS
from sis.research.ndx.leakage import validate_residual_training_columns


TARGET_COLUMN = "qqq_gap"


@dataclass(frozen=True)
class ResidualResult:
    residuals_path: Path
    manifest_path: Path
    report_path: Path
    row_count: int


def build_open_gap_residuals(
    *,
    feature_panel_path: Path,
    feature_manifest_path: Path,
    out_dir: Path,
    min_window: int = 4,
    factor_columns: list[str] | None = None,
) -> ResidualResult:
    factor_columns = factor_columns or MODEL_FACTOR_COLUMNS
    validate_residual_training_columns(factor_columns=factor_columns, target_column=TARGET_COLUMN)
    feature_frame = pl.read_parquet(feature_panel_path).sort("date")
    manifest = read_json(feature_manifest_path)
    residual_frame = build_rolling_ols_frame(
        feature_frame,
        factor_columns=factor_columns,
        min_window=min_window,
        feature_manifest_hash=str(manifest["feature_manifest_hash"]),
    )
    residuals_path = out_dir / "open_gap_residuals.parquet"
    residuals_path.parent.mkdir(parents=True, exist_ok=True)
    residual_frame.write_parquet(residuals_path)
    manifest_payload = {
        "schema_version": "ndx_open_gap_residual_manifest.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": manifest["dag_artifact_hash"],
        "feature_manifest_hash": manifest["feature_manifest_hash"],
        "created_at": utc_now_iso(),
        "residuals_path": residuals_path.as_posix(),
        "residuals_hash": sha256_file(residuals_path),
        "row_count": residual_frame.height,
        "target_column": TARGET_COLUMN,
        "factor_columns": factor_columns,
        "min_window": min_window,
        "training_policy": "strictly_before_prediction_date",
        "model": "rolling_ols_no_regularization",
        "emits_strategy_signals": False,
    }
    manifest_payload["model_config_hash"] = sha256_json(
        {
            "factor_columns": factor_columns,
            "min_window": min_window,
            "target_column": TARGET_COLUMN,
            "training_policy": "strictly_before_prediction_date",
        }
    )
    manifest_path = write_json(out_dir / "open_gap_residual_manifest.json", manifest_payload)
    report_path = _write_report(
        out_dir / "reports/ndx_open_gap_residual.md",
        row_count=residual_frame.height,
        manifest_hash=str(manifest_payload["model_config_hash"]),
    )
    return ResidualResult(
        residuals_path=residuals_path,
        manifest_path=manifest_path,
        report_path=report_path,
        row_count=residual_frame.height,
    )


def build_rolling_ols_frame(
    feature_frame: pl.DataFrame,
    *,
    factor_columns: list[str],
    min_window: int,
    feature_manifest_hash: str = "",
) -> pl.DataFrame:
    rows = feature_frame.sort("date").to_dicts()
    output: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        training_rows = rows[:index]
        if len(training_rows) < min_window:
            continue
        coefficients = fit_ols(
            [[float(train[column]) for column in factor_columns] for train in training_rows],
            [float(train[TARGET_COLUMN]) for train in training_rows],
        )
        factors = [float(row[column]) for column in factor_columns]
        expected = coefficients[0] + sum(
            coeff * value for coeff, value in zip(coefficients[1:], factors)
        )
        model_config_hash = sha256_json(
            {
                "factor_columns": factor_columns,
                "min_window": min_window,
                "target_column": TARGET_COLUMN,
                "prediction_date": str(row["date"]),
            }
        )
        output.append(
            {
                "date": row["date"],
                "actual_qqq_gap": float(row[TARGET_COLUMN]),
                "expected_qqq_gap": expected,
                "open_gap_residual": float(row[TARGET_COLUMN]) - expected,
                "qqq_open_to_close_return": float(row["qqq_open_to_close_return"]),
                "model_window_start": training_rows[0]["date"],
                "model_window_end": training_rows[-1]["date"],
                "model_training_row_count": len(training_rows),
                "factor_columns": json.dumps(factor_columns),
                "model_config_hash": model_config_hash,
                "dag_id": row["dag_id"],
                "dag_artifact_hash": row["dag_artifact_hash"],
                "feature_manifest_hash": feature_manifest_hash,
                **{column: float(row[column]) for column in factor_columns},
            }
        )
    if not output:
        raise ValueError("not enough feature rows to build rolling OLS residuals.")
    frame = pl.DataFrame(output).with_columns(
        [
            pl.col("date").cast(pl.Date),
            pl.col("model_window_start").cast(pl.Date),
            pl.col("model_window_end").cast(pl.Date),
        ]
    )
    return frame


def fit_ols(x_rows: list[list[float]], y: list[float]) -> list[float]:
    if len(x_rows) != len(y):
        raise ValueError("x/y row count mismatch.")
    if not x_rows:
        raise ValueError("OLS requires at least one row.")
    design = [[1.0, *row] for row in x_rows]
    width = len(design[0])
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, target in zip(design, y):
        for i in range(width):
            xty[i] += row[i] * target
            for j in range(width):
                xtx[i][j] += row[i] * row[j]
    return _solve_linear_system(xtx, xty)


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        pivot = augmented[pivot_row][column]
        if abs(pivot) < 1e-12:
            raise ValueError("rolling OLS design matrix is singular.")
        if pivot_row != column:
            augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row_index in range(size):
            if row_index == column:
                continue
            factor = augmented[row_index][column]
            if factor == 0.0:
                continue
            augmented[row_index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row_index], augmented[column])
            ]
    return [row[-1] for row in augmented]


def _write_report(path: Path, *, row_count: int, manifest_hash: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Layer 2.3 Open Gap Residual\n\n"
        f"- dag_id: {DAG_ID}\n"
        f"- residual_row_count: {row_count}\n"
        f"- model_config_hash: {manifest_hash}\n"
        "- training_policy: strictly_before_prediction_date\n"
        "- emits_strategy_signals: false\n",
        encoding="utf-8",
    )
    return path
