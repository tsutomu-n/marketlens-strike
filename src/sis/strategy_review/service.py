from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_summary import build_strategy_backtest_artifact_summary
from sis.backtest.artifact_summary_registry import ARTIFACT_SUMMARY_SPECS
from sis.research.strategy_lab.authoring.io import load_authoring_spec
from sis.strategy_review.manifest import (
    BuilderSafety,
    EvaluationFlags,
    ReviewPaths,
    ReviewStatus,
    ReviewSummary,
    SourceSafety,
    SourceSafetyFlags,
    SourceSafetyStatus,
    SourceArtifact,
    SourceArtifactStatus,
    StrategyReviewManifest,
)
from sis.strategy_review.provenance import (
    boundary_true_paths,
    collect_source_artifact,
    observed_boundary_flags,
    read_source_json,
    repo_relative_path,
    validate_review_id,
)
from sis.strategy_review.renderer import render_strategy_review_markdown
from sis.strategy_review.sections import ReviewSection


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
DEFAULT_LIFECYCLE_REVIEW_PATH = Path(
    "data/research/strategy_lifecycle/strategy_lifecycle_review.json"
)

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
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        path=path,
        required=required,
        summary=summary,
    )
    if exists and artifact.status is SourceArtifactStatus.PRESENT:
        payload = read_source_json(path)
        artifact.summary["observed_boundary_flags"] = observed_boundary_flags(payload)
        violations = boundary_true_paths(payload)
        if violations:
            artifact.summary["boundary_violations"] = violations
            return artifact.model_copy(
                update={
                    "status": SourceArtifactStatus.BLOCKED,
                    "error": f"source boundary violation: {', '.join(violations)}",
                }
            )
    return artifact


def _artifact_from_path_after_summary_error(
    artifact_key: str,
    path: Path,
    *,
    error: Exception,
) -> SourceArtifact:
    required = artifact_key in REQUIRED_ARTIFACT_KEYS
    exists = path.exists()
    if not exists:
        return collect_source_artifact(artifact_key=artifact_key, path=path, required=required)
    summary: dict[str, Any] = {}
    try:
        payload = read_source_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        artifact = collect_source_artifact(
            artifact_key=artifact_key,
            path=path,
            required=required,
            summary=summary,
        )
        if artifact.status is SourceArtifactStatus.INVALID:
            return artifact
        return artifact.model_copy(
            update={"status": SourceArtifactStatus.INVALID, "error": str(exc)}
        )

    violations = boundary_true_paths(payload)
    summary["observed_boundary_flags"] = observed_boundary_flags(payload)
    if violations:
        summary["boundary_violations"] = violations
    summary["summary_unavailable_due_to"] = str(error)
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        required=required,
        path=path,
        summary=summary,
    )
    if violations:
        return artifact.model_copy(
            update={
                "status": SourceArtifactStatus.BLOCKED,
                "error": f"source boundary violation: {', '.join(violations)}",
            }
        )
    return artifact


def _missing_optional_artifact(artifact_key: str, path: Path) -> SourceArtifact:
    return collect_source_artifact(artifact_key=artifact_key, path=path, required=False)


def _invalid_optional_artifact(
    artifact_key: str, path: Path, error: Exception | str
) -> SourceArtifact:
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        path=path,
        required=False,
        summary={"error": str(error)},
    )
    return artifact.model_copy(update={"status": SourceArtifactStatus.INVALID, "error": str(error)})


def _present_optional_artifact(
    artifact_key: str,
    path: Path,
    summary: dict[str, Any],
    *,
    payload: Any,
) -> SourceArtifact:
    violations = boundary_true_paths(payload)
    summary["observed_boundary_flags"] = observed_boundary_flags(payload)
    if violations:
        summary = {**summary, "boundary_violations": violations}
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        required=False,
        path=path,
        summary=summary,
    )
    if violations:
        return artifact.model_copy(
            update={
                "status": SourceArtifactStatus.BLOCKED,
                "error": f"source boundary violation: {', '.join(violations)}",
            }
        )
    return artifact


def _condition_count(value: Any) -> int:
    total = 0
    for field_name in ("all", "any", "none"):
        items = getattr(value, field_name, None)
        if isinstance(items, list):
            total += len(items)
    return total


def _configured_field_names(model: Any) -> list[str]:
    if not hasattr(model, "model_dump"):
        return []
    values = model.model_dump(exclude_none=True, exclude_defaults=True)
    return sorted(str(key) for key, value in values.items() if value not in (False, [], {}, None))


def _strategy_definition_summary(path: Path) -> tuple[SourceArtifact, ReviewSection]:
    try:
        spec = load_authoring_spec(path)
    except Exception as exc:
        return (
            _invalid_optional_artifact("authoring_spec", path, exc),
            ReviewSection(
                section_id="strategy_definition",
                title="Strategy Definition",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("authoring_spec",),
            ),
        )

    first_binding = spec.experiment.symbol_bindings[0]
    exit_fields = _configured_field_names(spec.rules.exit)
    summary: dict[str, Any] = {
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "execution_venue": first_binding.execution_venue,
        "execution_symbol": first_binding.execution_symbol,
        "real_market_symbol": first_binding.real_market_symbol,
        "run_profile_id": spec.experiment.run_profile_id,
        "side": spec.rules.side,
        "timeframe": spec.rules.timeframe,
        "entry_rule_count": _condition_count(spec.rules.entry),
        "hold_rule_count": _condition_count(spec.rules.hold) if spec.rules.hold is not None else 0,
        "exit_rule_fields": exit_fields,
        "position_weight": spec.rules.sizing.position_weight,
        "notional_usd": spec.rules.sizing.notional_usd,
        "split_method": spec.backtest.split_method,
        "label_horizon_minutes": spec.backtest.label_horizon_minutes,
        "primary_metric": spec.backtest.primary_metric,
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- strategy_id: `{summary['strategy_id']}`",
            f"- strategy_family: `{summary['strategy_family']}`",
            f"- strategy_version: `{summary['strategy_version']}`",
            f"- execution_venue: `{summary['execution_venue']}`",
            f"- execution_symbol: `{summary['execution_symbol']}`",
            f"- real_market_symbol: `{summary['real_market_symbol']}`",
            f"- run_profile_id: `{summary['run_profile_id']}`",
            f"- side: `{summary['side']}`",
            f"- timeframe: `{summary['timeframe']}`",
            f"- entry_rule_count: `{summary['entry_rule_count']}`",
            f"- hold_rule_count: `{summary['hold_rule_count']}`",
            f"- exit_rule_fields: `{', '.join(exit_fields) if exit_fields else 'none'}`",
            f"- sizing.position_weight: `{summary['position_weight']}`",
            f"- sizing.notional_usd: `{summary['notional_usd']}`",
            f"- backtest.split_method: `{summary['split_method']}`",
            f"- backtest.label_horizon_minutes: `{summary['label_horizon_minutes']}`",
            f"- backtest.primary_metric: `{summary['primary_metric']}`",
        ]
    )
    return (
        _present_optional_artifact(
            "authoring_spec",
            path,
            summary,
            payload=spec.model_dump(mode="json"),
        ),
        ReviewSection(
            section_id="strategy_definition",
            title="Strategy Definition",
            status="present",
            markdown=markdown,
            source_artifact_keys=("authoring_spec",),
        ),
    )


def _not_configured_strategy_definition_section() -> ReviewSection:
    return ReviewSection(
        section_id="strategy_definition",
        title="Strategy Definition",
        status="not_configured",
        markdown="- status: `not_configured`\n- reason: `authoring spec path was not provided or derivable`",
    )


def _string_list_field(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return value


def _object_field(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _lifecycle_review_summary(path: Path) -> tuple[SourceArtifact, ReviewSection]:
    if not path.exists():
        return (
            _missing_optional_artifact("lifecycle_review", path),
            ReviewSection(
                section_id="lifecycle_summary",
                title="Lifecycle Summary",
                status="missing",
                markdown=f"- status: `missing`\n- path: `{repo_relative_path(path)}`",
                source_artifact_keys=("lifecycle_review",),
            ),
        )
    try:
        payload = read_source_json(path)
        if payload.get("schema_version") != "strategy_lifecycle_review.v1":
            raise ValueError("schema_version must be strategy_lifecycle_review.v1")
        decision_reasons = _string_list_field(payload, "decision_reasons")
        next_actions = _string_list_field(payload, "next_actions")
        input_status = _object_field(payload, "input_status")
        blocker_counts = _object_field(payload, "blocker_counts")
    except Exception as exc:
        return (
            _invalid_optional_artifact("lifecycle_review", path, exc),
            ReviewSection(
                section_id="lifecycle_summary",
                title="Lifecycle Summary",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("lifecycle_review",),
            ),
        )

    summary = {
        "decision": payload.get("decision"),
        "decision_reasons": decision_reasons,
        "next_actions": next_actions,
        "input_status": input_status,
        "blocker_counts": blocker_counts,
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "venue_write_used": payload.get("venue_write_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- decision: `{summary['decision']}`",
            f"- decision_reasons: `{', '.join(summary['decision_reasons'])}`",
            f"- next_actions: `{', '.join(summary['next_actions'])}`",
            f"- input_status: `{json.dumps(summary['input_status'], sort_keys=True)}`",
            f"- blocker_counts: `{json.dumps(summary['blocker_counts'], sort_keys=True)}`",
            f"- permits_live_order: `{str(summary['permits_live_order']).lower()}`",
            f"- wallet_used: `{str(summary['wallet_used']).lower()}`",
            f"- venue_write_used: `{str(summary['venue_write_used']).lower()}`",
            f"- exchange_write_used: `{str(summary['exchange_write_used']).lower()}`",
        ]
    )
    return (
        _present_optional_artifact("lifecycle_review", path, summary, payload=payload),
        ReviewSection(
            section_id="lifecycle_summary",
            title="Lifecycle Summary",
            status="present",
            markdown=markdown,
            source_artifact_keys=("lifecycle_review",),
        ),
    )


def _backtest_pack_section(source_artifacts: list[SourceArtifact]) -> ReviewSection:
    by_key = {artifact.artifact_key: artifact for artifact in source_artifacts}
    pack = by_key.get("pack")
    validation = by_key.get("pack_validation")
    pack_summary = pack.summary if pack is not None else {}
    validation_summary = validation.summary if validation is not None else {}
    lines = [
        f"- pack_status: `{pack.status.value if pack else 'missing'}`",
        f"- validation_status: `{validation.status.value if validation else 'missing'}`",
        f"- validation_decision: `{validation_summary.get('decision')}`",
        f"- suite_run_count: `{pack_summary.get('suite_run_count', pack_summary.get('summary', {}).get('suite_run_count'))}`",
        f"- suite_method_count: `{pack_summary.get('suite_method_count', pack_summary.get('summary', {}).get('suite_method_count'))}`",
        f"- pack_validation_pass_is_readiness_proof: `{str(False).lower()}`",
    ]
    return ReviewSection(
        section_id="backtest_pack_validation_summary",
        title="Backtest Pack / Validation Summary",
        status="present",
        markdown="\n".join(lines),
        source_artifact_keys=("pack", "pack_validation"),
    )


def _derive_authoring_spec_path(pack_path: Path) -> Path | None:
    if not pack_path.exists():
        return None
    try:
        payload = read_source_json(pack_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    raw_path = payload.get("spec_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else Path.cwd() / path


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
    invalid_artifact_count = sum(
        1 for artifact in source_artifacts if artifact.status is SourceArtifactStatus.INVALID
    )
    unknown_boundary_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required
        and artifact.status in {SourceArtifactStatus.MISSING, SourceArtifactStatus.INVALID}
    )
    observed_flags = dict.fromkeys(
        (
            "permits_live_order",
            "live_conversion_allowed",
            "wallet_used",
            "signing_used",
            "exchange_write_used",
            "venue_write_used",
        ),
        False,
    )
    for artifact in source_artifacts:
        for key, value in artifact.summary.get("observed_boundary_flags", {}).items():
            if key in observed_flags:
                observed_flags[key] = bool(observed_flags[key] or value)

    if boundary_violation_count:
        review_status = ReviewStatus.BLOCKED_BOUNDARY_VIOLATION
        source_safety_status = SourceSafetyStatus.BLOCKED
    elif invalid_artifact_count:
        review_status = ReviewStatus.INVALID_INPUT
        source_safety_status = (
            SourceSafetyStatus.UNKNOWN if unknown_boundary_count else SourceSafetyStatus.PASS
        )
    elif missing_required_count:
        review_status = ReviewStatus.INCOMPLETE_ARTIFACTS
        source_safety_status = SourceSafetyStatus.UNKNOWN
    else:
        review_status = ReviewStatus.READY_FOR_HUMAN_REVIEW
        source_safety_status = SourceSafetyStatus.PASS

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
        builder_safety=BuilderSafety(),
        source_safety=SourceSafety(
            status=source_safety_status,
            boundary_violation_count=boundary_violation_count,
            unknown_boundary_count=unknown_boundary_count,
            observed_flags=SourceSafetyFlags(**observed_flags),
        ),
        evaluation_flags=EvaluationFlags(pack_validation_status=pack_validation_status),
        summary=ReviewSummary(
            missing_required_count=missing_required_count,
            invalid_required_count=invalid_required_count,
            boundary_violation_count=boundary_violation_count,
            unknown_boundary_count=unknown_boundary_count,
        ),
    )


def _manifest_json_payload(manifest: StrategyReviewManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    for artifact in payload["source_artifacts"]:
        for field_name in ("sha256", "bytes", "detected_schema_version", "error"):
            if artifact.get(field_name) is None:
                artifact.pop(field_name, None)
    return payload


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
