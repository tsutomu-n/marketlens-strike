from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sis.backtest.artifact_summary import build_strategy_backtest_artifact_summary
from sis.backtest.artifact_summary_registry import ARTIFACT_SUMMARY_SPECS
from sis.strategy_review.backtest_pack_section import (
    backtest_pack_section as _backtest_pack_section,
)
from sis.strategy_review.input_sources import (
    strategy_idea_summary,
    strategy_input_contract_summary,
)
from sis.strategy_review.lifecycle_summary import (
    lifecycle_review_summary as _lifecycle_review_summary,
)
from sis.strategy_review.manifest import (
    StrategyReviewManifest,
)
from sis.strategy_review.manifest_builder import (
    build_strategy_review_manifest as _build_manifest,
)
from sis.strategy_review.path_manifest_helpers import (
    created_at_value as _created_at_value,
    default_path as _default_path,
    derive_authoring_spec_path as _derive_authoring_spec_path,
    manifest_json_payload as _manifest_json_payload,
    summary_paths as _summary_paths,
)
from sis.strategy_review.provenance import (
    repo_relative_path,
    validate_review_id,
)
from sis.strategy_review.renderer import render_strategy_review_markdown
from sis.strategy_review.sections import ReviewSection
from sis.strategy_review.source_artifacts import (
    artifact_from_path_after_summary_error as _artifact_from_path_after_summary_error,
    artifact_from_summary as _artifact_from_summary,
    invalid_optional_artifact as _invalid_optional_artifact,
    missing_optional_artifact as _missing_optional_artifact,
    present_optional_artifact as _present_optional_artifact,
)
from sis.strategy_review.strategy_definition_summary import (
    not_configured_strategy_definition_section as _not_configured_strategy_definition_section,
    strategy_definition_summary as _strategy_definition_summary,
)


DEFAULT_LIFECYCLE_REVIEW_PATH = Path(
    "data/research/strategy_lifecycle/strategy_lifecycle_review.json"
)


@dataclass(frozen=True)
class StrategyReviewBuildResult:
    manifest: StrategyReviewManifest
    review_markdown_path: Path
    manifest_path: Path


class StrategyReviewBuildError(ValueError):
    exit_code = 2


class StrategyReviewOutputExistsError(StrategyReviewBuildError):
    pass


def _atomic_write_pair(
    first_path: Path, first_text: str, second_path: Path, second_text: str
) -> None:
    first_path.parent.mkdir(parents=True, exist_ok=True)
    second_path.parent.mkdir(parents=True, exist_ok=True)
    first_tmp = first_path.parent / f".{first_path.name}.tmp"
    second_tmp = second_path.parent / f".{second_path.name}.tmp"
    try:
        first_tmp.write_text(first_text, encoding="utf-8")
        second_tmp.write_text(second_text, encoding="utf-8")
        first_tmp.replace(first_path)
        second_tmp.replace(second_path)
    finally:
        for tmp_path in (first_tmp, second_tmp):
            if tmp_path.exists():
                tmp_path.unlink()


def build_strategy_review(
    *,
    review_id: str,
    out_dir: Path,
    pack_path: Path,
    validation_path: Path,
    authoring_spec_path: Path | None = None,
    input_contract_path: Path | None = None,
    strategy_idea_path: Path | None = None,
    lifecycle_review_path: Path | None = None,
    strict: bool = False,
    replace_existing: bool = False,
    created_at: datetime | str | None = None,
) -> StrategyReviewBuildResult:
    validate_review_id(review_id)

    review_dir = out_dir / review_id
    if review_dir.exists():
        if not replace_existing:
            raise StrategyReviewOutputExistsError(
                f"strategy review output already exists: {repo_relative_path(review_dir)}"
            )

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
            _artifact_from_path_after_summary_error(
                spec.key,
                paths[spec.path_field],
                error=exc,
            )
            for spec in ARTIFACT_SUMMARY_SPECS
        ]

    sections: list[ReviewSection] = []
    resolved_authoring_spec_path = authoring_spec_path or _derive_authoring_spec_path(pack_path)
    if resolved_authoring_spec_path is None:
        sections.append(_not_configured_strategy_definition_section())
    elif not resolved_authoring_spec_path.exists():
        source_artifacts.append(
            _missing_optional_artifact("authoring_spec", resolved_authoring_spec_path)
        )
        sections.append(
            ReviewSection(
                section_id="strategy_definition",
                title="Strategy Definition",
                status="missing",
                markdown=f"- status: `missing`\n- path: `{repo_relative_path(resolved_authoring_spec_path)}`",
                source_artifact_keys=("authoring_spec",),
            )
        )
    else:
        artifact, section = _strategy_definition_summary(resolved_authoring_spec_path)
        source_artifacts.append(artifact)
        sections.append(section)

    sections.append(_backtest_pack_section(source_artifacts))

    if input_contract_path is not None:
        input_contract_artifact, input_contract_section = strategy_input_contract_summary(
            input_contract_path,
            missing_artifact_fn=_missing_optional_artifact,
            invalid_artifact_fn=_invalid_optional_artifact,
            present_artifact_fn=_present_optional_artifact,
        )
        source_artifacts.append(input_contract_artifact)
        sections.append(input_contract_section)

    if strategy_idea_path is not None:
        strategy_idea_artifact, strategy_idea_section = strategy_idea_summary(
            strategy_idea_path,
            missing_artifact_fn=_missing_optional_artifact,
            invalid_artifact_fn=_invalid_optional_artifact,
            present_artifact_fn=_present_optional_artifact,
        )
        source_artifacts.append(strategy_idea_artifact)
        sections.append(strategy_idea_section)

    resolved_lifecycle_review_path = lifecycle_review_path or _default_path(
        DEFAULT_LIFECYCLE_REVIEW_PATH
    )
    lifecycle_artifact, lifecycle_section = _lifecycle_review_summary(
        resolved_lifecycle_review_path
    )
    source_artifacts.append(lifecycle_artifact)
    sections.append(lifecycle_section)

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

    review_text = render_strategy_review_markdown(manifest, sections)
    manifest_text = (
        json.dumps(
            _manifest_json_payload(manifest),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _atomic_write_pair(review_markdown_path, review_text, manifest_path, manifest_text)
    return StrategyReviewBuildResult(
        manifest=manifest,
        review_markdown_path=review_markdown_path,
        manifest_path=manifest_path,
    )
