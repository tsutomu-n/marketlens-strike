from __future__ import annotations

from pathlib import Path

import typer

from sis.ops.daemon import DaemonDryRunResult, DaemonLoopResult, DaemonRunManifest


def daemon_manifest_lines(manifest: DaemonRunManifest) -> list[str]:
    return [
        f"run_id={manifest.run_id}",
        f"mode={manifest.mode}",
    ]


def echo_daemon_manifest(manifest: DaemonRunManifest) -> None:
    for line in daemon_manifest_lines(manifest):
        typer.echo(line)


def daemon_dry_run_lines(result: DaemonDryRunResult) -> list[str]:
    return [
        f"run_id={result.run_id}",
        f"status={result.status}",
        f"scheduled_for={result.scheduled_for}",
        f"operation_chain={result.operation_chain_path}",
    ]


def echo_daemon_dry_run(result: DaemonDryRunResult) -> None:
    for line in daemon_dry_run_lines(result):
        typer.echo(line)


def daemon_loop_lines(
    result: DaemonLoopResult, *, report_path: Path, summary_path: Path
) -> list[str]:
    return [
        f"run_id={result.run_id}",
        f"status={result.status}",
        f"cycles_requested={result.cycles_requested}",
        f"cycles_completed={result.cycles_completed}",
        f"daemon_loop_path={result.loop_snapshot_path}",
        f"daemon_loop_report_path={report_path}",
        f"daemon_loop_summary_path={summary_path}",
        f"daemon_loop_events_path={result.event_log_path}",
        f"operation_chain={result.operation_chain_path}",
    ]


def echo_daemon_loop(result: DaemonLoopResult, *, report_path: Path, summary_path: Path) -> None:
    for line in daemon_loop_lines(result, report_path=report_path, summary_path=summary_path):
        typer.echo(line)
