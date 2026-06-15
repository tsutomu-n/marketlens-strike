from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from sis.backtest.artifact_io import read_json_object


@dataclass(frozen=True)
class ArtifactSummarySpec:
    key: str
    path_field: str
    summarizer_id: str


ARTIFACT_SUMMARY_SPECS: tuple[ArtifactSummarySpec, ...] = (
    ArtifactSummarySpec("pack", "pack_path", "pack"),
    ArtifactSummarySpec("pack_validation", "validation_path", "validation"),
    ArtifactSummarySpec("framework_run", "framework_run_path", "framework_run"),
    ArtifactSummarySpec("benchmark_relative", "benchmark_relative_path", "benchmark_relative"),
    ArtifactSummarySpec("metric_extension", "metric_extension_path", "metric_extension"),
    ArtifactSummarySpec("report_extension", "report_extension_path", "report_extension"),
    ArtifactSummarySpec("stress", "stress_path", "stress"),
    ArtifactSummarySpec("regime_split", "regime_split_path", "regime_split"),
    ArtifactSummarySpec("rolling_stability", "rolling_stability_path", "rolling_stability"),
    ArtifactSummarySpec("data_availability", "data_availability_path", "completion_artifact"),
    ArtifactSummarySpec("baseline_comparison", "baseline_comparison_path", "completion_artifact"),
    ArtifactSummarySpec("trial_ledger", "trial_ledger_path", "completion_artifact"),
    ArtifactSummarySpec("assumption_ledger", "assumption_ledger_path", "completion_artifact"),
    ArtifactSummarySpec("no_lookahead_diff", "no_lookahead_path", "completion_artifact"),
    ArtifactSummarySpec("execution_simulation", "execution_simulation_path", "completion_artifact"),
    ArtifactSummarySpec("comparison", "comparison_path", "comparison"),
)


def summarize_artifact(
    path: Path,
    spec: ArtifactSummarySpec,
    summarizers: Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    row: dict[str, Any] = {"path": path.as_posix(), "exists": path.exists()}
    if not path.exists():
        return row
    payload = read_json_object(path)
    row.update(summarizers[spec.summarizer_id](payload))
    return row
