from __future__ import annotations

import polars as pl


class NdxLeakageError(ValueError):
    """Raised when the NDX preflight feature/residual flow would leak future information."""


BANNED_MODEL_INPUT_COLUMNS = {
    "qqq_close",
    "qqq_open_to_close_return",
    "actual_qqq_gap",
    "expected_qqq_gap",
    "open_gap_residual",
}
ISO_TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def validate_feature_panel(frame: pl.DataFrame, *, model_input_columns: list[str]) -> None:
    missing = [
        column
        for column in ("feature_ts", "source_ts_max", "source_tier")
        if column not in frame.columns
    ]
    if missing:
        raise NdxLeakageError("feature panel missing leakage guard columns: " + ", ".join(missing))
    if frame.get_column("source_tier").null_count() > 0:
        raise NdxLeakageError("feature panel contains null source_tier.")
    banned = sorted(BANNED_MODEL_INPUT_COLUMNS.intersection(model_input_columns))
    if banned:
        raise NdxLeakageError(
            "model input contains close/outcome/residual columns: " + ", ".join(banned)
        )
    suspicious = [
        column
        for column in model_input_columns
        if column.endswith("_close") or "open_to_close" in column or column.startswith("future_")
    ]
    if suspicious:
        raise NdxLeakageError(
            "model input contains suspicious future/close columns: " + ", ".join(suspicious)
        )
    late = frame.filter(
        pl.col("source_ts_max").str.to_datetime(ISO_TS_FORMAT)
        > pl.col("feature_ts").str.to_datetime(ISO_TS_FORMAT)
    )
    if late.height:
        raise NdxLeakageError("source_ts_max exceeds feature_ts.")


def validate_residual_training_columns(*, factor_columns: list[str], target_column: str) -> None:
    if target_column != "qqq_gap":
        raise NdxLeakageError(f"unexpected residual target column: {target_column}")
    validate_feature_panel(
        pl.DataFrame(
            {
                "feature_ts": ["2026-01-01T14:31:00+00:00"],
                "source_ts_max": ["2026-01-01T14:30:00+00:00"],
                "source_tier": ["fixture_required"],
            }
        ),
        model_input_columns=factor_columns,
    )
