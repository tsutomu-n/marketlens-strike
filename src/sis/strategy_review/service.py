from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_summary import build_strategy_backtest_artifact_summary
from sis.backtest.artifact_summary_registry import ARTIFACT_SUMMARY_SPECS
from sis.strategy_review.manifest import (
    EvaluationFlags,
    ReviewPaths,
    ReviewSafety,
    ReviewStatus,
    ReviewSummary,
    SourceArtifact,
    SourceArtifactStatus,
    StrategyReviewManifest,
)
from sis.strategy_review.provenance import (
    boundary_true_paths,
    read_source_json,
    repo_relative_path,
    source_hash,
)
from sis.strategy_review.renderer import render_strategy_review_markdown


DEFAULT_BENCHMARK_RELATIVE_PATH = Path(
    "data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json"
)
DEFAULT_METRIC_EXTENSION_PATH = Path(
    "data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"
)
DEFAULT_REPORT_EXTENSION_PATH = Path(
    "data/research/backtest_report_extension/strategy_backtest_report_extension.json"
)
DEFAULT_STRESS_PATH = Path("data/research/backtest_stress/strategy_backtest_stress.json")
DEFAULT_REGIME_SPLIT_PATH = Path(
    "data/research/backtest_regime_split/strategy_backtest_regime_split.json"
)
DEFAULT_ROLLING_STABILITY_PATH = Path(
    "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
)
DEFAULT_DATA_AVAILABILITY_PATH = Path(
    "data/research/backtest_data_availability/backtest_data_availability_ledger.json"
)
DEFAULT_BASELINE_COMPARISON_PATH = Path(
    "data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json"
)
DEFAULT_TRIAL_LEDGER_PATH = Path(
    "data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"
)
DEFAULT_ASSUMPTION_LEDGER_PATH = Path(
    "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
)
DEFAULT_NO_LOOKAHEAD_PATH = Path(
    "data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"
)
DEFAULT_EXECUTION_SIMULATION_PATH = Path(
    "data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json"
)
DEFAULT_COMPARISON_PATH = Path("data/research/backtest_compare/strategy_backtest_comparison.json")

REQUIRED_ARTIFACT_KEYS = {"pack", "pack_validation"}


@dataclass(frozen=True)
class StrategyReviewBuildResult:
    manifest: StrategyReviewManifest
    review_markdown_path: Path
    manifest_path: Path


class StrategyReviewBuildError(ValueError):
    exit_code = 2


class StrategyReviewOutputExistsError(StrategyReviewBuildError):
    pass


def _created_at_value(created_at: datetime | str | None) -> str:
    if isinstance(created_at, str):
        return created_at
    value = created_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_path(path: Path) -> Path:
    return path if path.is_absolute() else (Path.cwd() / path)


def _summary_paths(pack_path: Path, validation_path: Path) -> dict[str, Path]:
    framework_run_path = pack_path.parent / "strategy_backtest_framework_run.json"
    if pack_path.parent.name == "backtest_pack" and pack_path.parent.parent.name == "research":
        framework_run_path = (
            pack_path.parent.parent / "backtest_framework_run/strategy_backtest_framework_run.json"
        )
    return {
        "pack_path": pack_path,
        "validation_path": validation_path,
        "framework_run_path": framework_run_path,
        "benchmark_relative_path": _default_path(DEFAULT_BENCHMARK_RELATIVE_PATH),
        "metric_extension_path": _default_path(DEFAULT_METRIC_EXTENSION_PATH),
        "report_extension_path": _default_path(DEFAULT_REPORT_EXTENSION_PATH),
        "stress_path": _default_path(DEFAULT_STRESS_PATH),
        "regime_split_path": _default_path(DEFAULT_REGIME_SPLIT_PATH),
        "rolling_stability_path": _default_path(DEFAULT_ROLLING_STABILITY_PATH),
        "data_availability_path": _default_path(DEFAULT_DATA_AVAILABILITY_PATH),
        "baseline_comparison_path": _default_path(DEFAULT_BASELINE_COMPARISON_PATH),
        "trial_ledger_path": _default_path(DEFAULT_TRIAL_LEDGER_PATH),
        "assumption_ledger_path": _default_path(DEFAULT_ASSUMPTION_LEDGER_PATH),
        "no_lookahead_path": _default_path(DEFAULT_NO_LOOKAHEAD_PATH),
        "execution_simulation_path": _default_path(DEFAULT_EXECUTION_SIMULATION_PATH),
        "comparison_path": _default_path(DEFAULT_COMPARISON_PATH),
    }


def _artifact_from_summary(artifact_key: str, row: dict[str, Any]) -> SourceArtifact:
    exists = row.get("exists") is True
    required = artifact_key in REQUIRED_ARTIFACT_KEYS
    path = Path(str(row.get("path", "")))
    summary = {key: value for key, value in row.items() if key not in {"path", "exists"}}
    status = SourceArtifactStatus.MISSING
    digest: str | None = None
    if exists:
        digest = source_hash(path)
        status = SourceArtifactStatus.PRESENT
        violations = boundary_true_paths(read_source_json(path))
        if violations:
            summary["boundary_violations"] = violations
    return SourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        exists=exists,
        required=required,
        status=status,
        sha256=digest,
        summary=summary,
    )


def _build_manifest(
    *,
    review_id: str,
    created_at: str,
    strict: bool,
    review_dir: Path,
    review_markdown_path: Path,
    manifest_path: Path,
    source_artifacts: list[SourceArtifact],
) -> StrategyReviewManifest:
    missing_required_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required and artifact.status is SourceArtifactStatus.MISSING
    )
    invalid_required_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required and artifact.status is SourceArtifactStatus.INVALID
    )
    boundary_violation_count = sum(
        len(artifact.summary.get("boundary_violations", [])) for artifact in source_artifacts
    )
    if boundary_violation_count:
        review_status = ReviewStatus.BLOCKED_BOUNDARY_VIOLATION
    elif invalid_required_count:
        review_status = ReviewStatus.INVALID_INPUT
    elif missing_required_count:
        review_status = ReviewStatus.INCOMPLETE_ARTIFACTS
    else:
        review_status = ReviewStatus.READY_FOR_HUMAN_REVIEW

    pack_validation = next(
        (artifact for artifact in source_artifacts if artifact.artifact_key == "pack_validation"),
        None,
    )
    pack_validation_status = None
    if pack_validation is not None:
        value = pack_validation.summary.get("decision")
        pack_validation_status = str(value) if value is not None else None

    return StrategyReviewManifest(
        review_id=review_id,
        created_at=created_at,
        review_status=review_status,
        strict=strict,
        paths=ReviewPaths(
            review_dir=repo_relative_path(review_dir),
            review_markdown_path=repo_relative_path(review_markdown_path),
            manifest_path=repo_relative_path(manifest_path),
        ),
        source_artifacts=source_artifacts,
        safety=ReviewSafety(),
        evaluation_flags=EvaluationFlags(pack_validation_status=pack_validation_status),
        summary=ReviewSummary(
            missing_required_count=missing_required_count,
            invalid_required_count=invalid_required_count,
            boundary_violation_count=boundary_violation_count,
        ),
    )


def build_strategy_review(
    *,
    review_id: str,
    out_dir: Path,
    pack_path: Path,
    validation_path: Path,
    strict: bool = False,
    replace_existing: bool = False,
    created_at: datetime | str | None = None,
) -> StrategyReviewBuildResult:
    # Validate review_id before it is used as a path segment.
    StrategyReviewManifest.model_validate(
        {
            "review_id": review_id,
            "created_at": _created_at_value(created_at),
            "review_status": "INVALID_INPUT",
            "strict": strict,
            "paths": {
                "review_dir": "data/strategy_reviews/placeholder",
                "review_markdown_path": "data/strategy_reviews/placeholder/review.md",
                "manifest_path": "data/strategy_reviews/placeholder/review_manifest.json",
            },
            "source_artifacts": [],
            "safety": {},
            "evaluation_flags": {},
            "summary": {
                "missing_required_count": 0,
                "invalid_required_count": 0,
                "boundary_violation_count": 0,
            },
        }
    )

    review_dir = out_dir / review_id
    if review_dir.exists():
        if not replace_existing:
            raise StrategyReviewOutputExistsError(
                f"strategy review output already exists: {repo_relative_path(review_dir)}"
            )
        shutil.rmtree(review_dir)

    paths = _summary_paths(pack_path, validation_path)
    try:
        summary_kwargs = {key: value for key, value in paths.items() if key != "framework_run_path"}
        summary = build_strategy_backtest_artifact_summary(**summary_kwargs).payload
        if isinstance(summary.get("framework_run"), dict):
            summary["framework_run"]["path"] = paths["framework_run_path"].as_posix()
        source_artifacts = [
            _artifact_from_summary(spec.key, summary[spec.key]) for spec in ARTIFACT_SUMMARY_SPECS
        ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        source_artifacts = [
            SourceArtifact(
                artifact_key=spec.key,
                path=repo_relative_path(paths[spec.path_field]),
                exists=paths[spec.path_field].exists(),
                required=spec.key in REQUIRED_ARTIFACT_KEYS,
                status=SourceArtifactStatus.INVALID
                if spec.key in REQUIRED_ARTIFACT_KEYS
                else SourceArtifactStatus.MISSING,
                summary={"error": str(exc)} if spec.key in REQUIRED_ARTIFACT_KEYS else {},
            )
            for spec in ARTIFACT_SUMMARY_SPECS
        ]

    review_markdown_path = review_dir / "review.md"
    manifest_path = review_dir / "review_manifest.json"
    manifest = _build_manifest(
        review_id=review_id,
        created_at=_created_at_value(created_at),
        strict=strict,
        review_dir=review_dir,
        review_markdown_path=review_markdown_path,
        manifest_path=manifest_path,
        source_artifacts=source_artifacts,
    )

    review_dir.mkdir(parents=True, exist_ok=True)
    review_markdown_path.write_text(render_strategy_review_markdown(manifest), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return StrategyReviewBuildResult(
        manifest=manifest,
        review_markdown_path=review_markdown_path,
        manifest_path=manifest_path,
    )
