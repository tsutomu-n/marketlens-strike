from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json


class _SummaryReportWriter(Protocol):
    def __call__(self, settings_data_dir: Path) -> tuple[Path, Path, str]: ...


class _ManifestAppenderWithKwargs(Protocol):
    def __call__(self, settings_data_dir: Path, **kwargs: object) -> Path: ...


def register_remediation_commands(
    app: typer.Typer,
    *,
    write_remediation_planner_fn: _SummaryReportWriter,
    write_remediation_execution_plan_fn: _SummaryReportWriter,
    write_remediation_session_fn: _SummaryReportWriter,
    write_remediation_session_checkpoint_fn: Callable[..., tuple[Path, Path, str]],
    write_remediation_command_results_fn: _SummaryReportWriter,
    write_remediation_scoreboard_fn: _SummaryReportWriter,
    write_remediation_evaluator_fn: _SummaryReportWriter,
    write_remediation_evidence_fn: _SummaryReportWriter,
    append_remediation_planner_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_execution_plan_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_session_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_session_checkpoint_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_evidence_ingest_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_scoreboard_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_evaluator_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_evidence_manifest_fn: _ManifestAppenderWithKwargs,
    append_remediation_command_results_manifest_fn: _ManifestAppenderWithKwargs,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("remediation-planner")
    def remediation_planner_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_planner_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_planner_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            planner_status=payload.get("planner_status") if isinstance(payload, dict) else None,
            rerun_trend=(
                payload.get("planner_rerun_diff", {}).get("trend")
                if isinstance(payload, dict) and isinstance(payload.get("planner_rerun_diff"), dict)
                else None
            ),
            next_best_command=payload.get("next_best_command") if isinstance(payload, dict) else None,
            next_feedback_priority_reason=(
                payload.get("entries", [{}])[0].get("feedback_priority_reason")
                if isinstance(payload, dict) and isinstance(payload.get("entries"), list) and payload.get("entries")
                else None
            ),
            planned_step_count=payload.get("planned_step_count") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-execution-plan")
    def remediation_execution_plan_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_execution_plan_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_execution_plan_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            execution_plan_status=payload.get("execution_plan_status") if isinstance(payload, dict) else None,
            next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
            next_action_feedback_priority_reason=(
                payload.get("actions", [{}])[0].get("feedback_priority_reason")
                if isinstance(payload, dict) and isinstance(payload.get("actions"), list) and payload.get("actions")
                else None
            ),
            planned_action_count=payload.get("planned_action_count") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-session")
    def remediation_session_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_session_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_session_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            session_status=payload.get("session_status") if isinstance(payload, dict) else None,
            next_pending_command=payload.get("next_pending_command") if isinstance(payload, dict) else None,
            next_pending_stage_signal_confidence=(
                payload.get("next_pending_stage_signal_confidence")
                if isinstance(payload, dict)
                else None
            ),
            next_pending_feedback_priority_reason=(
                payload.get("next_pending_feedback_priority_reason")
                if isinstance(payload, dict)
                else None
            ),
            pending_action_count=payload.get("pending_action_count") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-session-checkpoint")
    def remediation_session_checkpoint_cmd(
        action_key: str | None = typer.Option(None, "--action-key", help="Stable action key to update."),
        result: str | None = typer.Option(None, "--result", help="One of: pending, pass, fail, retry."),
        note: str | None = typer.Option(None, "--note", help="Optional operator note appended to the action."),
        evidence_path: str | None = typer.Option(
            None,
            "--evidence-path",
            help="Optional evidence artifact path recorded on the action.",
        ),
        observed_signal: str | None = typer.Option(
            None,
            "--observed-signal",
            help="Optional verification signal observed to have passed.",
        ),
        stdout_summary: str | None = typer.Option(
            None,
            "--stdout-summary",
            help="Optional stdout summary recorded on the action.",
        ),
        stderr_summary: str | None = typer.Option(
            None,
            "--stderr-summary",
            help="Optional stderr summary recorded on the action.",
        ),
        exit_code: int | None = typer.Option(
            None,
            "--exit-code",
            help="Optional command exit code recorded on the action.",
        ),
    ) -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_session_checkpoint_fn(
            settings.data_dir,
            action_key=action_key,
            result=result,
            note=note,
            evidence_path=evidence_path,
            observed_signal=observed_signal,
            stdout_summary=stdout_summary,
            stderr_summary=stderr_summary,
            exit_code=exit_code,
        )
        payload = read_json(summary_out)
        chain_out = append_remediation_session_checkpoint_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            checkpoint_status=payload.get("checkpoint_status") if isinstance(payload, dict) else None,
            next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
            next_action_stage_signal_confidence=(
                payload.get("next_action_stage_signal_confidence")
                if isinstance(payload, dict)
                else None
            ),
            next_action_feedback_priority_reason=(
                next(
                    (
                        item.get("feedback_priority_reason")
                        for item in payload.get("actions", [])
                        if isinstance(item, dict)
                        and item.get("command") == payload.get("next_action_command")
                    ),
                    None,
                )
                if isinstance(payload, dict)
                else None
            ),
            pending_action_count=payload.get("pending_action_count") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-evidence-ingest")
    def remediation_evidence_ingest_cmd(
        action_key: str = typer.Option(..., "--action-key", help="Stable action key to update."),
        result: str | None = typer.Option(None, "--result", help="One of: pending, pass, fail, retry."),
        note: str | None = typer.Option(None, "--note", help="Optional operator note appended to the action."),
        evidence_path: str | None = typer.Option(
            None,
            "--evidence-path",
            help="Optional evidence artifact path recorded on the action.",
        ),
        observed_signal: str | None = typer.Option(
            None,
            "--observed-signal",
            help="Optional verification signal observed to have passed.",
        ),
        stdout_summary: str | None = typer.Option(
            None,
            "--stdout-summary",
            help="Optional stdout summary recorded on the action.",
        ),
        stderr_summary: str | None = typer.Option(
            None,
            "--stderr-summary",
            help="Optional stderr summary recorded on the action.",
        ),
        exit_code: int | None = typer.Option(
            None,
            "--exit-code",
            help="Optional command exit code recorded on the action.",
        ),
    ) -> None:
        settings = get_settings()
        checkpoint_out, checkpoint_summary_out, _checkpoint_text = write_remediation_session_checkpoint_fn(
            settings.data_dir,
            action_key=action_key,
            result=result,
            note=note,
            evidence_path=evidence_path,
            observed_signal=observed_signal,
            stdout_summary=stdout_summary,
            stderr_summary=stderr_summary,
            exit_code=exit_code,
        )
        command_results_out, command_results_summary_out, command_results_text = write_remediation_command_results_fn(
            settings.data_dir
        )
        checkpoint_payload = read_json(checkpoint_summary_out)
        chain_out = append_remediation_evidence_ingest_manifest_fn(
            settings.data_dir,
            checkpoint_summary_path=checkpoint_summary_out,
            action_key=action_key,
            checkpoint_status=(
                checkpoint_payload.get("checkpoint_status")
                if isinstance(checkpoint_payload, dict)
                else None
            ),
            exit_code=exit_code,
        )
        logger.info("written: {}", checkpoint_out)
        logger.info("written: {}", checkpoint_summary_out)
        logger.info("written: {}", command_results_out)
        logger.info("written: {}", command_results_summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(command_results_text)
        typer.echo(f"remediation_session_checkpoint_path={checkpoint_out}")
        typer.echo(f"remediation_command_results_path={command_results_out}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-scoreboard")
    def remediation_scoreboard_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_scoreboard_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_scoreboard_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            scoreboard_status=payload.get("scoreboard_status") if isinstance(payload, dict) else None,
            next_action_command=payload.get("next_action_command") if isinstance(payload, dict) else None,
            next_action_stage_signal_confidence=(
                payload.get("next_action_stage_signal_confidence")
                if isinstance(payload, dict)
                else None
            ),
            next_action_feedback_priority_reason=(
                next(
                    (
                        item.get("feedback_priority_reason")
                        for item in payload.get("actions", [])
                        if isinstance(item, dict)
                        and item.get("command") == payload.get("next_action_command")
                    ),
                    None,
                )
                if isinstance(payload, dict)
                else None
            ),
            completion_rate=payload.get("completion_rate") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-evaluator")
    def remediation_evaluator_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_evaluator_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_evaluator_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            evaluator_status=payload.get("evaluator_status") if isinstance(payload, dict) else None,
            next_action_key=payload.get("next_action_key") if isinstance(payload, dict) else None,
            auto_fail_count=payload.get("auto_fail_count") if isinstance(payload, dict) else None,
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-evidence")
    def remediation_evidence_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_evidence_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_evidence_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            evidence_status=payload.get("evidence_status") if isinstance(payload, dict) else None,
            next_manual_review_action_key=(
                payload.get("next_manual_review_action_key")
                if isinstance(payload, dict)
                else None
            ),
            manual_review_action_count=(
                payload.get("manual_review_action_count")
                if isinstance(payload, dict)
                else None
            ),
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("remediation-command-results")
    def remediation_command_results_cmd() -> None:
        settings = get_settings()
        out, summary_out, text = write_remediation_command_results_fn(settings.data_dir)
        payload = read_json(summary_out)
        chain_out = append_remediation_command_results_manifest_fn(
            settings.data_dir,
            summary_path=summary_out,
            command_results_status=(
                payload.get("command_results_status")
                if isinstance(payload, dict)
                else None
            ),
            next_unobserved_action_key=(
                payload.get("next_unobserved_action_key")
                if isinstance(payload, dict)
                else None
            ),
            missing_observation_count=(
                payload.get("missing_observation_count")
                if isinstance(payload, dict)
                else None
            ),
        )
        logger.info("written: {}", out)
        logger.info("written: {}", summary_out)
        logger.info("appended: {}", chain_out)
        typer.echo(text)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
