from __future__ import annotations

from pathlib import Path

from sis.backtest.artifact_io import write_json_object
from sis.backtest.artifact_summary_registry import (
    ARTIFACT_SUMMARY_SPECS,
    ArtifactSummarySpec,
    summarize_artifact,
)


def test_artifact_summary_specs_keep_current_top_level_key_order() -> None:
    assert [spec.key for spec in ARTIFACT_SUMMARY_SPECS] == [
        "pack",
        "pack_validation",
        "framework_run",
        "benchmark_relative",
        "metric_extension",
        "report_extension",
        "stress",
        "regime_split",
        "rolling_stability",
        "data_availability",
        "baseline_comparison",
        "trial_ledger",
        "assumption_ledger",
        "no_lookahead_diff",
        "execution_simulation",
        "comparison",
    ]


def test_summarize_artifact_returns_exists_false_for_missing_path(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    spec = ArtifactSummarySpec("example", "example_path", "example")

    assert summarize_artifact(path, spec, {"example": lambda payload: payload}) == {
        "path": path.as_posix(),
        "exists": False,
    }


def test_summarize_artifact_merges_summary_for_existing_json(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    write_json_object(path, {"status": "pass"})
    spec = ArtifactSummarySpec("example", "example_path", "example")

    assert summarize_artifact(
        path,
        spec,
        {"example": lambda payload: {"status": payload["status"]}},
    ) == {
        "path": path.as_posix(),
        "exists": True,
        "status": "pass",
    }
