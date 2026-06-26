from __future__ import annotations

from pathlib import Path

from sis.reports.remediation_command_results import build_remediation_command_results
from sis.reports.remediation_evaluator import build_remediation_evaluator
from sis.reports.remediation_evidence import build_remediation_evidence
from sis.reports.remediation_execution_plan import build_remediation_execution_plan
from sis.reports.remediation_planner import build_remediation_planner
from sis.reports.remediation_scoreboard import build_remediation_scoreboard
from sis.reports.remediation_session import build_remediation_session
from sis.reports.remediation_session_checkpoint import build_remediation_session_checkpoint


def _write_remediation_planner(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_planner.md"
    summary_out = settings_data_dir / "ops/remediation_planner_summary.json"
    text = build_remediation_planner(
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_execution_plan(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_execution_plan.md"
    summary_out = settings_data_dir / "ops/remediation_execution_plan_summary.json"
    text = build_remediation_execution_plan(
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session.md"
    summary_out = settings_data_dir / "ops/remediation_session_summary.json"
    text = build_remediation_session(
        remediation_execution_plan_summary_path=settings_data_dir
        / "ops/remediation_execution_plan_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session_checkpoint(
    settings_data_dir: Path,
    *,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session_checkpoint.md"
    summary_out = settings_data_dir / "ops/remediation_session_checkpoint_summary.json"
    text = build_remediation_session_checkpoint(
        remediation_session_summary_path=settings_data_dir / "ops/remediation_session_summary.json",
        checkpoint_summary_path=summary_out,
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    return out, summary_out, text


def _write_remediation_scoreboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_scoreboard.md"
    summary_out = settings_data_dir / "ops/remediation_scoreboard_summary.json"
    text = build_remediation_scoreboard(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evaluator(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evaluator.md"
    summary_out = settings_data_dir / "ops/remediation_evaluator_summary.json"
    text = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evidence(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evidence.md"
    summary_out = settings_data_dir / "ops/remediation_evidence_summary.json"
    text = build_remediation_evidence(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_command_results(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_command_results.md"
    summary_out = settings_data_dir / "ops/remediation_command_results_summary.json"
    text = build_remediation_command_results(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
