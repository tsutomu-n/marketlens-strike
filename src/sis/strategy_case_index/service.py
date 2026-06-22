from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_case_index.models import (
    StrategyCaseIndex,
    StrategyCaseIndexCaseEntry,
    StrategyCaseIndexSourceArtifact,
    StrategyCaseIndexStrategySummary,
)
from sis.strategy_case_index.rendering import render_strategy_case_index_markdown
from sis.strategy_case_lite.models import StrategyCaseLite
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import boundary_true_paths, repo_relative_path
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyCaseIndexResult:
    index: StrategyCaseIndex
    index_path: Path
    report_path: Path


class StrategyCaseIndexError(ValueError):
    pass


class StrategyCaseIndexOutputExistsError(StrategyCaseIndexError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _read_case_lite(path: Path, *, explicit: bool) -> StrategyCaseLite | None:
    if not path.exists():
        raise FileNotFoundError(f"case artifact missing: {path}")
    try:
        payload = read_json_object(path)
    except (json.JSONDecodeError, ValueError) as exc:
        if explicit:
            raise StrategyCaseIndexError(f"invalid JSON case artifact {path}: {exc}") from exc
        return None
    schema_version = payload.get("schema_version")
    if schema_version != "strategy_case_lite.v1":
        if explicit:
            raise StrategyCaseIndexError(
                f"expected strategy_case_lite.v1 at {path}, found {schema_version!r}"
            )
        return None
    violations = boundary_true_paths(payload)
    if violations:
        raise StrategyCaseIndexError(
            f"case artifact boundary violation {path}: " + ", ".join(violations)
        )
    try:
        return StrategyCaseLite.model_validate(payload)
    except ValidationError as exc:
        raise StrategyCaseIndexError(f"invalid strategy_case_lite artifact {path}: {exc}") from exc


def _discover_case_paths(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted(path for path in data_dir.rglob("*.json") if path.is_file())


def _case_entry(path: Path, case: StrategyCaseLite) -> StrategyCaseIndexCaseEntry:
    return StrategyCaseIndexCaseEntry(
        case_id=case.case_id,
        strategy_id=case.strategy_id,
        case_path=repo_relative_path(path),
        case_sha256=sha256_file(path),
        latest_status=case.summary.latest_status,
        artifact_count=case.summary.artifact_count,
        timeline_count=case.summary.timeline_count,
        open_actions=case.summary.open_actions,
        blocked_reasons=case.summary.blocked_reasons,
        updated_at=case.updated_at,
    )


def _source_artifact(path: Path) -> StrategyCaseIndexSourceArtifact:
    return StrategyCaseIndexSourceArtifact(
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version="strategy_case_lite.v1",
    )


def _latest_case(cases: list[StrategyCaseIndexCaseEntry]) -> StrategyCaseIndexCaseEntry:
    return sorted(cases, key=lambda case: (case.updated_at, case.case_path))[-1]


def _strategy_summaries(
    cases: list[StrategyCaseIndexCaseEntry],
) -> list[StrategyCaseIndexStrategySummary]:
    grouped: dict[str, list[StrategyCaseIndexCaseEntry]] = {}
    for case in cases:
        grouped.setdefault(case.strategy_id, []).append(case)

    summaries: list[StrategyCaseIndexStrategySummary] = []
    for strategy_id, strategy_cases in sorted(grouped.items()):
        latest = _latest_case(strategy_cases)
        summaries.append(
            StrategyCaseIndexStrategySummary(
                strategy_id=strategy_id,
                case_count=len(strategy_cases),
                latest_case_id=latest.case_id,
                latest_case_path=latest.case_path,
                latest_status=latest.latest_status,
                open_actions=sorted(
                    {action for case in strategy_cases for action in case.open_actions}
                ),
                blocked_reasons=sorted(
                    {reason for case in strategy_cases for reason in case.blocked_reasons}
                ),
            )
        )
    return summaries


def _collect_cases(
    *,
    case_paths: list[Path],
    data_dir: Path | None,
) -> tuple[list[StrategyCaseIndexCaseEntry], list[StrategyCaseIndexSourceArtifact]]:
    selected: list[tuple[Path, StrategyCaseLite]] = []
    for path in case_paths:
        case = _read_case_lite(path, explicit=True)
        if case is not None:
            selected.append((path, case))
    if data_dir is not None:
        for path in _discover_case_paths(data_dir):
            case = _read_case_lite(path, explicit=False)
            if case is not None:
                selected.append((path, case))

    by_hash: dict[str, tuple[Path, StrategyCaseLite]] = {}
    for path, case in sorted(selected, key=lambda item: repo_relative_path(item[0])):
        digest = sha256_file(path)
        if digest not in by_hash:
            by_hash[digest] = (path, case)

    if not by_hash:
        raise StrategyCaseIndexError("no strategy_case_lite.v1 artifacts found")

    entries: list[StrategyCaseIndexCaseEntry] = []
    sources: list[StrategyCaseIndexSourceArtifact] = []
    for path, case in by_hash.values():
        entries.append(_case_entry(path, case))
        sources.append(_source_artifact(path))
    sorted_pairs = sorted(zip(entries, sources, strict=True), key=lambda pair: pair[0].case_path)
    return [entry for entry, _ in sorted_pairs], [source for _, source in sorted_pairs]


def _default_index_id(cases: list[StrategyCaseIndexCaseEntry]) -> str:
    latest = _latest_case(cases)
    return f"strategy-case-index-{latest.updated_at.strftime('%Y%m%d%H%M%S')}"


def build_strategy_case_index(
    *,
    case_paths: list[Path] | None,
    data_dir: Path | None,
    out_dir: Path,
    index_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyCaseIndexResult:
    cases, source_artifacts = _collect_cases(case_paths=case_paths or [], data_dir=data_dir)
    selected_index_id = index_id or _default_index_id(cases)
    index = StrategyCaseIndex(
        index_id=selected_index_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-case-index-build"),
        case_count=len(cases),
        strategy_count=len({case.strategy_id for case in cases}),
        cases=cases,
        strategies=_strategy_summaries(cases),
        source_artifacts=source_artifacts,
    )
    index_path = out_dir / f"{selected_index_id}.json"
    report_path = out_dir / f"{selected_index_id}.md"
    if not replace_existing and (index_path.exists() or report_path.exists()):
        raise StrategyCaseIndexOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(index_path, index.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_strategy_case_index_markdown(index))
    return StrategyCaseIndexResult(index=index, index_path=index_path, report_path=report_path)
