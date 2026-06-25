from __future__ import annotations

import pytest
import polars as pl

from sis.research.ndx.residual_validation_metrics import (
    era_summary,
    float_series,
    max_abs_neutralized_ic,
    missing_rate,
    pearson,
    ranks,
    residual_metric_bundle,
    safe_ratio,
    sign_flip_rate,
    sign_stability_ratio,
    validation_metrics,
    variance,
)


def test_residual_validation_metric_math_helpers() -> None:
    assert variance([1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert variance([1.0]) == 0.0
    assert pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert pearson([1.0, 1.0, 1.0], [2.0, 4.0, 6.0]) == 0.0
    assert pearson([1.0], [1.0]) == 0.0
    assert ranks([10.0, 20.0, 20.0, 40.0]) == [1.0, 2.5, 2.5, 4.0]
    assert sign_stability_ratio([1.0, 2.0, -3.0, 0.0]) == pytest.approx(0.5)
    assert sign_flip_rate([1.0, -1.0, 0.0, -2.0, 3.0]) == pytest.approx(1.0)
    assert safe_ratio(3.0, 2.0) == pytest.approx(1.5)
    assert safe_ratio(3.0, 0.0) == 0.0


def test_residual_validation_frame_helpers() -> None:
    frame = pl.DataFrame(
        {
            "date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
                "2026-01-05",
                "2026-01-06",
                "2026-01-07",
                "2026-01-08",
                "2026-01-09",
                "2026-01-10",
                "2026-02-01",
            ],
            "value": [1.0, None, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
        }
    )
    other = pl.DataFrame({"other": [1.0, None]})

    assert float_series(frame, "value") == [1.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]
    assert float_series(frame, "missing") == []
    assert missing_rate(frame, other) == pytest.approx(2 / 24)
    assert missing_rate(pl.DataFrame()) == 1.0
    assert era_summary(frame) == {
        "era_count": 2,
        "qualified_era_count": 1,
        "rows_by_era": {"2026-01": 10, "2026-02": 1},
    }
    assert era_summary(pl.DataFrame({"value": [1.0]})) == {
        "era_count": 0,
        "qualified_era_count": 0,
        "rows_by_era": {},
    }


def test_residual_metric_bundle_and_max_abs_neutralized_ic() -> None:
    bundle = residual_metric_bundle([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])

    assert bundle["sample_count"] == 3
    assert bundle["variance"] == pytest.approx(1.0)
    assert bundle["ic"] == pytest.approx(-1.0)
    assert bundle["rank_ic"] == pytest.approx(-1.0)
    assert bundle["sign_stability"] == pytest.approx(1.0)
    assert bundle["sign_flip_rate"] == 0.0
    assert max_abs_neutralized_ic(
        {"neutralized": {"a": {"ic": -0.25}, "b": {"ic": 0.1}}}
    ) == pytest.approx(0.25)
    assert max_abs_neutralized_ic({"neutralized": {}}) == 0.0


def test_validation_metrics_composes_payload_and_discovers_neutralized_columns() -> None:
    residuals = pl.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-02-01"],
            "open_gap_residual": [1.0, 2.0, 3.0],
            "qqq_open_to_close_return": [3.0, 2.0, 1.0],
        }
    )
    neutralized = pl.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-02-01"],
            "factor_a_neutralized_residual": [0.5, 1.0, 1.5],
            "ignored_signal": [10.0, 11.0, 12.0],
            "combined_neutralized_residual": [0.5, 1.0, 1.5],
        }
    )

    metrics = validation_metrics(residuals=residuals, neutralized=neutralized)

    assert metrics["schema_version"] == "ndx_residual_validation_metrics.v1"
    assert metrics["row_count"] == 3
    assert metrics["missing_rate"] == 0.0
    assert metrics["era_summary"] == {
        "era_count": 2,
        "qualified_era_count": 0,
        "rows_by_era": {"2026-01": 2, "2026-02": 1},
    }
    assert set(metrics["neutralized"]) == {
        "factor_a_neutralized_residual",
        "combined_neutralized_residual",
    }
    assert "ignored_signal" not in metrics["neutralized"]
    assert metrics["raw"]["variance"] == pytest.approx(1.0)
    assert metrics["raw"]["ic"] == pytest.approx(-1.0)
    assert metrics["combined"]["variance"] == pytest.approx(0.25)
    assert metrics["combined"]["ic"] == pytest.approx(-1.0)
    assert metrics["combined"]["variance_retention"] == pytest.approx(0.25)
    assert metrics["combined"]["variance_shrinkage"] == pytest.approx(0.75)
