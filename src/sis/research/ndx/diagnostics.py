from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import statistics

import polars as pl

from sis.research.ndx.artifacts import DAG_ID, read_json, sha256_file, utc_now_iso, write_json
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS


@dataclass(frozen=True)
class DiagnosticsResult:
    diagnostics_path: Path
    neutralized_path: Path
    neutralization_report_path: Path
    refutation_report_path: Path
    row_count: int


def build_ndx_diagnostics(
    *,
    residuals_path: Path,
    residual_manifest_path: Path,
    out_dir: Path,
) -> DiagnosticsResult:
    residuals = pl.read_parquet(residuals_path).sort("date")
    manifest = read_json(residual_manifest_path)
    neutralized = build_neutralized_frame(
        residuals, factor_columns=list(manifest["factor_columns"])
    )
    neutralized_path = out_dir / "neutralized_residuals.parquet"
    neutralized_path.parent.mkdir(parents=True, exist_ok=True)
    neutralized.write_parquet(neutralized_path)

    diagnostics_payload = {
        "schema_version": "ndx_residual_diagnostics.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": manifest["dag_artifact_hash"],
        "feature_manifest_hash": manifest["feature_manifest_hash"],
        "created_at": utc_now_iso(),
        "row_count": residuals.height,
        "missing_rate": _missing_rate(residuals),
        "residual_mean": _mean(residuals["open_gap_residual"].to_list()),
        "residual_std": _stdev(residuals["open_gap_residual"].to_list()),
        "residual_autocorr_lag1": _autocorr_lag1(residuals["open_gap_residual"].to_list()),
        "correlation_with_outcome": _corr(
            residuals["open_gap_residual"].to_list(),
            residuals["qqq_open_to_close_return"].to_list(),
        ),
        "correlation_with_factors": {
            column: _corr(residuals["open_gap_residual"].to_list(), residuals[column].to_list())
            for column in MODEL_FACTOR_COLUMNS
            if column in residuals.columns
        },
        "sign_stability": _sign_stability(residuals["open_gap_residual"].to_list()),
        "regime_split_by_vix": _regime_split_by_vix(residuals),
        "neutralized_residuals_path": neutralized_path.as_posix(),
        "neutralized_residuals_hash": sha256_file(neutralized_path),
        "emits_strategy_signals": False,
    }
    diagnostics_path = write_json(out_dir / "ndx_residual_diagnostics.json", diagnostics_payload)
    neutralization_report_path = _write_neutralization_report(
        out_dir / "ndx_neutralization_pre_report.md",
        diagnostics=diagnostics_payload,
        neutralized_path=neutralized_path,
    )
    refutation_report_path = _write_refutation_report(
        out_dir / "ndx_counter_dag_refutation_skeleton.md"
    )
    return DiagnosticsResult(
        diagnostics_path=diagnostics_path,
        neutralized_path=neutralized_path,
        neutralization_report_path=neutralization_report_path,
        refutation_report_path=refutation_report_path,
        row_count=residuals.height,
    )


def build_neutralized_frame(residuals: pl.DataFrame, *, factor_columns: list[str]) -> pl.DataFrame:
    rows = residuals.to_dicts()
    output: list[dict[str, object]] = []
    for row in rows:
        item: dict[str, object] = {
            "date": row["date"],
            "dag_id": row["dag_id"],
            "dag_artifact_hash": row["dag_artifact_hash"],
            "feature_manifest_hash": row["feature_manifest_hash"],
            "raw_open_gap_residual": float(row["open_gap_residual"]),
        }
        adjusted_values = []
        for column in factor_columns:
            adjusted = _single_factor_adjusted(residuals, row, factor_column=column)
            item[f"{column}_neutralized_residual"] = adjusted
            adjusted_values.append(adjusted)
        item["combined_neutralized_residual"] = _mean(adjusted_values)
        output.append(item)
    return pl.DataFrame(output).with_columns(pl.col("date").cast(pl.Date))


def _single_factor_adjusted(
    residuals: pl.DataFrame, row: dict[str, object], *, factor_column: str
) -> float:
    factor_values = [float(value) for value in residuals[factor_column].to_list()]
    residual_values = [float(value) for value in residuals["open_gap_residual"].to_list()]
    factor_mean = _mean(factor_values)
    residual_mean = _mean(residual_values)
    denominator = sum((value - factor_mean) ** 2 for value in factor_values)
    beta = (
        0.0
        if abs(denominator) < 1e-12
        else sum(
            (x_value - factor_mean) * (y_value - residual_mean)
            for x_value, y_value in zip(factor_values, residual_values)
        )
        / denominator
    )
    return _as_float(row["open_gap_residual"]) - beta * (
        _as_float(row[factor_column]) - factor_mean
    )


def _missing_rate(frame: pl.DataFrame) -> float:
    cells = frame.height * len(frame.columns)
    if cells == 0:
        return 0.0
    missing = sum(frame[column].null_count() for column in frame.columns)
    return missing / cells


def _as_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"expected numeric value, got {type(value).__name__}")


def _mean(values: list[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _stdev(values: list[float]) -> float:
    return float(statistics.stdev(values)) if len(values) > 1 else 0.0


def _corr(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_den = sum((x - left_mean) ** 2 for x in left)
    right_den = sum((y - right_mean) ** 2 for y in right)
    denominator = (left_den * right_den) ** 0.5
    return 0.0 if denominator == 0.0 else numerator / denominator


def _autocorr_lag1(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    return _corr(values[1:], values[:-1])


def _sign_stability(values: list[float]) -> dict[str, int]:
    positive = sum(1 for value in values if value > 0)
    negative = sum(1 for value in values if value < 0)
    zero = len(values) - positive - negative
    return {"positive": positive, "negative": negative, "zero": zero}


def _regime_split_by_vix(frame: pl.DataFrame) -> dict[str, dict[str, float]]:
    if "vix_change" not in frame.columns:
        return {}
    sorted_vix = sorted(float(value) for value in frame["vix_change"].to_list())
    threshold = sorted_vix[len(sorted_vix) // 2]
    high = frame.filter(pl.col("vix_change") >= threshold)
    low = frame.filter(pl.col("vix_change") < threshold)
    return {
        "low_vix_change": {
            "row_count": float(low.height),
            "residual_mean": _mean(low["open_gap_residual"].to_list()) if low.height else 0.0,
        },
        "high_vix_change": {
            "row_count": float(high.height),
            "residual_mean": _mean(high["open_gap_residual"].to_list()) if high.height else 0.0,
        },
    }


def _write_neutralization_report(
    path: Path, *, diagnostics: dict[str, object], neutralized_path: Path
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Layer 2.3 Neutralization Pre-Report\n\n"
        f"- dag_id: {DAG_ID}\n"
        f"- row_count: {diagnostics['row_count']}\n"
        f"- residual_mean: {diagnostics['residual_mean']}\n"
        f"- residual_std: {diagnostics['residual_std']}\n"
        f"- correlation_with_outcome: {diagnostics['correlation_with_outcome']}\n"
        f"- neutralized_residuals: {neutralized_path}\n"
        "- emits_strategy_signals: false\n",
        encoding="utf-8",
    )
    return path


def _write_refutation_report(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    enabled = [
        "BroadMarketOnly",
        "RatesOnly",
        "SOXOnlyUsingSMHProxy",
        "MegaCapOnly",
        "VolRegimeOnly",
        "SelectionBias",
        "DataSourceLag",
    ]
    deferred = [
        "ETFTrackingNoise",
        "FuturesPriceDiscovery",
        "IndexRebalance",
        "MacroEvent",
        "CalendarEffect",
    ]
    path.write_text(
        "# NDX Layer 2.3 Counter-DAG Refutation Skeleton\n\n"
        f"- dag_id: {DAG_ID}\n"
        "## Enabled Skeletons\n\n"
        + "\n".join(f"- {item}: not_yet_refuted" for item in enabled)
        + "\n\n## Deferred Skeletons\n\n"
        + "\n".join(f"- {item}: deferred" for item in deferred)
        + "\n",
        encoding="utf-8",
    )
    return path
