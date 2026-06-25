from __future__ import annotations

import math
import statistics
from typing import Any

import polars as pl


def float_series(frame: pl.DataFrame, column: str) -> list[float]:
    if column not in frame.columns:
        return []
    return [float(value) for value in frame[column].to_list() if value is not None]


def missing_rate(*frames: pl.DataFrame) -> float:
    cells = sum(frame.height * len(frame.columns) for frame in frames)
    if cells == 0:
        return 1.0
    missing = sum(frame[column].null_count() for frame in frames for column in frame.columns)
    return missing / cells


def variance(values: list[float]) -> float:
    return float(statistics.variance(values)) if len(values) > 1 else 0.0


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_den = sum((x - left_mean) ** 2 for x in left)
    right_den = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_den * right_den)
    return 0.0 if denominator == 0.0 else numerator / denominator


def ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    output = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        average_rank = (index + end - 1) / 2.0 + 1.0
        for original_index, _ in indexed[index:end]:
            output[original_index] = average_rank
        index = end
    return output


def sign_stability_ratio(values: list[float]) -> float:
    if not values:
        return 0.0
    positive = sum(1 for value in values if value > 0)
    negative = sum(1 for value in values if value < 0)
    return max(positive, negative) / len(values)


def sign_flip_rate(values: list[float]) -> float:
    signs = [1 if value > 0 else -1 if value < 0 else 0 for value in values]
    pairs = [(left, right) for left, right in zip(signs, signs[1:]) if left and right]
    if not pairs:
        return 0.0
    return sum(1 for left, right in pairs if left != right) / len(pairs)


def era_summary(residuals: pl.DataFrame) -> dict[str, Any]:
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


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def max_abs_neutralized_ic(metrics: dict[str, Any]) -> float:
    neutralized = metrics.get("neutralized", {})
    if not isinstance(neutralized, dict) or not neutralized:
        return 0.0
    return max(abs(float(item.get("ic", 0.0))) for item in neutralized.values())


def residual_metric_bundle(values: list[float], outcome: list[float]) -> dict[str, float | int]:
    return {
        "sample_count": len(values),
        "variance": variance(values),
        "ic": pearson(values, outcome),
        "rank_ic": pearson(ranks(values), ranks(outcome)),
        "sign_stability": sign_stability_ratio(values),
        "sign_flip_rate": sign_flip_rate(values),
    }


def validation_metrics(*, residuals: pl.DataFrame, neutralized: pl.DataFrame) -> dict[str, Any]:
    raw = float_series(residuals, "open_gap_residual")
    outcome = float_series(residuals, "qqq_open_to_close_return")
    neutralized_columns = [
        column for column in neutralized.columns if column.endswith("_neutralized_residual")
    ]
    neutralized_metrics = {
        column: residual_metric_bundle(float_series(neutralized, column), outcome)
        for column in neutralized_columns
    }
    combined = float_series(neutralized, "combined_neutralized_residual")
    raw_variance = variance(raw)
    combined_variance = variance(combined)
    return {
        "schema_version": "ndx_residual_validation_metrics.v1",
        "row_count": residuals.height,
        "missing_rate": missing_rate(residuals, neutralized),
        "era_summary": era_summary(residuals),
        "raw": residual_metric_bundle(raw, outcome),
        "neutralized": neutralized_metrics,
        "combined": residual_metric_bundle(combined, outcome)
        | {
            "variance_retention": safe_ratio(combined_variance, raw_variance),
            "variance_shrinkage": 1.0 - safe_ratio(combined_variance, raw_variance),
        },
    }
