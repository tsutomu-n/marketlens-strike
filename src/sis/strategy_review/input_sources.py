from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.strategy_inputs.io import read_mapping_file
from sis.strategy_inputs.models import StrategyIdea, StrategyInputContract
from sis.strategy_review.manifest import SourceArtifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    repo_relative_path,
)
from sis.strategy_review.sections import ReviewSection


def strategy_input_contract_summary(
    path: Path,
    *,
    missing_artifact_fn,
    invalid_artifact_fn,
    present_artifact_fn,
) -> tuple[SourceArtifact, ReviewSection]:
    if not path.exists():
        return (
            missing_artifact_fn("input_contract", path),
            ReviewSection(
                section_id="input_contract_summary",
                title="Input Contract Summary",
                status="missing",
                markdown=f"- status: `missing`\n- path: `{repo_relative_path(path)}`",
                source_artifact_keys=("input_contract",),
            ),
        )
    try:
        payload = read_mapping_file(path)
        violations = boundary_true_paths(payload)
        if violations:
            summary = {
                "schema_version": payload.get("schema_version"),
                "contract_id": payload.get("contract_id"),
                "boundary_violations": violations,
            }
            artifact = present_artifact_fn("input_contract", path, summary, payload=payload)
            return (
                artifact,
                ReviewSection(
                    section_id="input_contract_summary",
                    title="Input Contract Summary",
                    status="blocked",
                    markdown=(
                        f"- status: `blocked`\n"
                        f"- path: `{repo_relative_path(path)}`\n"
                        f"- boundary_violations: `{', '.join(violations)}`"
                    ),
                    source_artifact_keys=("input_contract",),
                ),
            )
        contract = StrategyInputContract.model_validate(payload)
    except Exception as exc:
        return (
            invalid_artifact_fn("input_contract", path, exc),
            ReviewSection(
                section_id="input_contract_summary",
                title="Input Contract Summary",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("input_contract",),
            ),
        )

    required_count = sum(1 for source in contract.sources if source.required)
    optional_count = len(contract.sources) - required_count
    summary: dict[str, Any] = {
        "contract_id": contract.contract_id,
        "strategy_family": contract.strategy_scope.strategy_family,
        "instruments": contract.strategy_scope.instruments,
        "timeframe": contract.strategy_scope.timeframe,
        "intended_use": contract.strategy_scope.intended_use,
        "source_count": len(contract.sources),
        "required_source_count": required_count,
        "optional_source_count": optional_count,
        "known_gap_count": len(contract.known_gaps),
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- contract_id: `{summary['contract_id']}`",
            f"- strategy_family: `{summary['strategy_family']}`",
            f"- instruments: `{', '.join(summary['instruments'])}`",
            f"- timeframe: `{summary['timeframe']}`",
            f"- intended_use: `{summary['intended_use']}`",
            f"- source_count: `{summary['source_count']}`",
            f"- required_source_count: `{summary['required_source_count']}`",
            f"- optional_source_count: `{summary['optional_source_count']}`",
            f"- known_gap_count: `{summary['known_gap_count']}`",
        ]
    )
    return (
        present_artifact_fn(
            "input_contract",
            path,
            summary,
            payload=contract.model_dump(mode="json"),
        ),
        ReviewSection(
            section_id="input_contract_summary",
            title="Input Contract Summary",
            status="present",
            markdown=markdown,
            source_artifact_keys=("input_contract",),
        ),
    )


def strategy_idea_summary(
    path: Path,
    *,
    missing_artifact_fn,
    invalid_artifact_fn,
    present_artifact_fn,
) -> tuple[SourceArtifact, ReviewSection]:
    if not path.exists():
        return (
            missing_artifact_fn("strategy_idea", path),
            ReviewSection(
                section_id="idea_intake_summary",
                title="Idea Intake Summary",
                status="missing",
                markdown=f"- status: `missing`\n- path: `{repo_relative_path(path)}`",
                source_artifact_keys=("strategy_idea",),
            ),
        )
    try:
        payload = read_mapping_file(path)
        violations = boundary_true_paths(payload)
        if violations:
            summary = {
                "schema_version": payload.get("schema_version"),
                "idea_id": payload.get("idea_id"),
                "boundary_violations": violations,
            }
            artifact = present_artifact_fn("strategy_idea", path, summary, payload=payload)
            return (
                artifact,
                ReviewSection(
                    section_id="idea_intake_summary",
                    title="Idea Intake Summary",
                    status="blocked",
                    markdown=(
                        f"- status: `blocked`\n"
                        f"- path: `{repo_relative_path(path)}`\n"
                        f"- boundary_violations: `{', '.join(violations)}`"
                    ),
                    source_artifact_keys=("strategy_idea",),
                ),
            )
        idea = StrategyIdea.model_validate(payload)
    except Exception as exc:
        return (
            invalid_artifact_fn("strategy_idea", path, exc),
            ReviewSection(
                section_id="idea_intake_summary",
                title="Idea Intake Summary",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("strategy_idea",),
            ),
        )

    summary: dict[str, Any] = {
        "idea_id": idea.idea_id,
        "title": idea.title,
        "mechanism": idea.mechanism,
        "timeframe": idea.timeframe,
        "instruments": idea.instruments,
        "required_input_contract_ids": idea.required_input_contract_ids,
        "baseline_name": idea.baseline.name,
        "invalidation_count": len(idea.invalidation),
        "risk_kill_condition_count": len(idea.risk.kill_conditions),
        "authoring_target": idea.authoring_intent.target,
        "auto_generate_spec": idea.authoring_intent.auto_generate_spec,
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- idea_id: `{summary['idea_id']}`",
            f"- title: `{summary['title']}`",
            f"- mechanism: `{summary['mechanism']}`",
            f"- timeframe: `{summary['timeframe']}`",
            f"- instruments: `{', '.join(summary['instruments'])}`",
            f"- required_input_contract_ids: `{', '.join(summary['required_input_contract_ids'])}`",
            f"- baseline_name: `{summary['baseline_name']}`",
            f"- invalidation_count: `{summary['invalidation_count']}`",
            f"- risk_kill_condition_count: `{summary['risk_kill_condition_count']}`",
            f"- authoring_target: `{summary['authoring_target']}`",
            f"- auto_generate_spec: `{str(summary['auto_generate_spec']).lower()}`",
        ]
    )
    return (
        present_artifact_fn(
            "strategy_idea",
            path,
            summary,
            payload=idea.model_dump(mode="json"),
        ),
        ReviewSection(
            section_id="idea_intake_summary",
            title="Idea Intake Summary",
            status="present",
            markdown=markdown,
            source_artifact_keys=("strategy_idea",),
        ),
    )
