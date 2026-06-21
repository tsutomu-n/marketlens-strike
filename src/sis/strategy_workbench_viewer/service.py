from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import StageProducer
from sis.strategy_workbench_viewer.models import (
    StrategyWorkbenchViewerManifest,
    ViewerArtifactFormat,
    ViewerSourceArtifact,
)
from sis.strategy_workbench_viewer.rendering import render_strategy_workbench_viewer_html


@dataclass(frozen=True)
class StrategyWorkbenchViewerResult:
    manifest: StrategyWorkbenchViewerManifest
    manifest_path: Path
    html_path: Path


class StrategyWorkbenchViewerError(ValueError):
    pass


class StrategyWorkbenchViewerOutputExistsError(StrategyWorkbenchViewerError):
    pass


STATUS_KEYS = (
    "cycle_status",
    "gate_status",
    "tournament_status",
    "decision_status",
    "plan_status",
    "ingest_status",
    "review_status",
    "status",
    "validation_status",
    "readiness_status",
    "recommended_action",
)

SUMMARY_KEYS = (
    "gate_id",
    "gate_status",
    "cycle_status",
    "human_summary",
    "report_id",
    "tournament_status",
    "leader_action",
    "primary_metric",
    "event_count",
    "leader_actual_cash_result_usd",
    "proxy_gap_count",
    "failed_condition_count",
    "present_stage_count",
    "missing_artifact_path_count",
    "known_gap_count",
    "stop_reason_count",
    "strategy_id",
    "review_id",
    "decision_id",
    "plan_id",
    "manifest_id",
    "recommended_action",
    "latest_status",
    "open_action_count",
    "pending_human_review_count",
    "boundary_violation_count",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _display_path(path: Path) -> str:
    try:
        return repo_relative_path(path)
    except ValueError:
        return path.as_posix()


def _scan_artifacts(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    paths: list[Path] = []
    for path in data_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
            if any(part.startswith(".") for part in path.parts):
                continue
            paths.append(path)
    return sorted(paths)


def _first_status(payload: dict[str, Any]) -> str | None:
    for key in STATUS_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _compact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in SUMMARY_KEYS:
        value = payload.get(key)
        if value is not None:
            summary[key] = value
    nested = payload.get("summary")
    if isinstance(nested, dict):
        for key in SUMMARY_KEYS:
            value = nested.get(key)
            if value is not None and key not in summary:
                summary[key] = value
    stop_reasons = payload.get("stop_reasons")
    if isinstance(stop_reasons, list) and stop_reasons and "first_stop_reason" not in summary:
        summary["first_stop_reason"] = str(stop_reasons[0])
    return summary


def _json_title(path: Path, payload: dict[str, Any]) -> str:
    schema_version = payload.get("schema_version")
    strategy_id = payload.get("strategy_id")
    review_id = payload.get("review_id")
    title_parts = [str(schema_version or path.stem)]
    if strategy_id:
        title_parts.append(str(strategy_id))
    elif review_id:
        title_parts.append(str(review_id))
    return " / ".join(title_parts)


def _source_from_json(path: Path, artifact_key: str) -> ViewerSourceArtifact:
    payload = read_json_object(path)
    violations = boundary_true_paths(payload)
    return ViewerSourceArtifact(
        artifact_key=artifact_key,
        path=_display_path(path),
        sha256=sha256_file(path),
        artifact_format=ViewerArtifactFormat.JSON,
        schema_version=detect_json_schema_version(path),
        title=_json_title(path, payload),
        status=_first_status(payload),
        boundary_violations=violations,
        summary=_compact_summary(payload),
        preview=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)[:6000],
    )


def _source_from_text(path: Path, artifact_key: str) -> ViewerSourceArtifact:
    text = path.read_text(encoding="utf-8")
    artifact_format = (
        ViewerArtifactFormat.MARKDOWN if path.suffix.lower() == ".md" else ViewerArtifactFormat.TEXT
    )
    first_heading = next(
        (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
        path.stem,
    )
    return ViewerSourceArtifact(
        artifact_key=artifact_key,
        path=_display_path(path),
        sha256=sha256_file(path),
        artifact_format=artifact_format,
        schema_version=None,
        title=first_heading or path.stem,
        status=None,
        boundary_violations=[],
        summary={"artifact_format": artifact_format.value},
        preview=text[:6000],
    )


def _source_artifact(path: Path, artifact_key: str) -> ViewerSourceArtifact:
    if not path.exists():
        raise FileNotFoundError(f"artifact missing: {path}")
    if path.suffix.lower() == ".json":
        try:
            return _source_from_json(path, artifact_key)
        except (json.JSONDecodeError, ValueError) as exc:
            raise StrategyWorkbenchViewerError(f"invalid JSON artifact {path}: {exc}") from exc
    if path.suffix.lower() in {".md", ".txt"}:
        return _source_from_text(path, artifact_key)
    raise StrategyWorkbenchViewerError(f"unsupported artifact format: {path}")


def build_strategy_workbench_viewer(
    *,
    artifacts: list[Path] | None,
    data_dir: Path,
    out_dir: Path,
    viewer_id: str = "strategy-workbench-viewer",
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyWorkbenchViewerResult:
    selected_paths = artifacts or _scan_artifacts(data_dir)
    if not selected_paths:
        raise StrategyWorkbenchViewerError("no artifacts supplied or discovered")
    html_path = out_dir / "strategy_workbench_viewer.html"
    manifest_path = out_dir / "strategy_workbench_viewer_manifest.json"
    if not replace_existing and (html_path.exists() or manifest_path.exists()):
        raise StrategyWorkbenchViewerOutputExistsError(
            f"output already exists: {_display_path(out_dir)}"
        )

    sources = [
        _source_artifact(path, f"artifact_{index:03d}")
        for index, path in enumerate(selected_paths, 1)
    ]
    boundary_violation_count = sum(len(source.boundary_violations) for source in sources)
    manifest_without_hash = StrategyWorkbenchViewerManifest(
        viewer_id=viewer_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-workbench-viewer-build"),
        source_artifacts=sources,
        html_report_path=_display_path(html_path),
        html_report_hash="sha256:pending",
        artifact_count=len(sources),
        boundary_violation_count=boundary_violation_count,
    )
    html = render_strategy_workbench_viewer_html(manifest_without_hash)
    write_text_artifact(html_path, html)
    manifest = manifest_without_hash.model_copy(update={"html_report_hash": sha256_file(html_path)})
    write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    return StrategyWorkbenchViewerResult(
        manifest=manifest,
        manifest_path=manifest_path,
        html_path=html_path,
    )
