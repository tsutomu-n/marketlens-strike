from pathlib import Path

from sis.commands.ops_daemon_echo import (
    daemon_dry_run_lines,
    daemon_loop_lines,
    daemon_manifest_lines,
)
from sis.ops.daemon import DaemonDryRunResult, DaemonLoopResult, DaemonRunManifest


def test_daemon_loop_lines_preserve_cli_order() -> None:
    result = DaemonLoopResult(
        run_id="run-1",
        status="completed",
        cycles_requested=1,
        cycles_completed=1,
        daemon_manifest_path=Path("data/ops/daemon_manifest.json"),
        event_log_path=Path("data/ops/daemon_loop_events.jsonl"),
        loop_snapshot_path=Path("data/ops/daemon_loop.json"),
        operation_chain_path=Path("data/ops/operation_manifests.jsonl"),
    )

    assert daemon_loop_lines(
        result,
        report_path=Path("data/reports/daemon_loop.md"),
        summary_path=Path("data/ops/daemon_loop_summary.json"),
    ) == [
        "run_id=run-1",
        "status=completed",
        "cycles_requested=1",
        "cycles_completed=1",
        "daemon_loop_path=data/ops/daemon_loop.json",
        "daemon_loop_report_path=data/reports/daemon_loop.md",
        "daemon_loop_summary_path=data/ops/daemon_loop_summary.json",
        "daemon_loop_events_path=data/ops/daemon_loop_events.jsonl",
        "operation_chain=data/ops/operation_manifests.jsonl",
    ]


def test_daemon_loop_lines_preserve_persistent_cycle_value() -> None:
    result = DaemonLoopResult(
        run_id="run-2",
        status="blocked",
        cycles_requested=None,
        cycles_completed=0,
        daemon_manifest_path=Path("daemon_manifest.json"),
        event_log_path=Path("events.jsonl"),
        loop_snapshot_path=Path("loop.json"),
        operation_chain_path=Path("operation_manifests.jsonl"),
    )

    assert (
        daemon_loop_lines(
            result,
            report_path=Path("daemon_loop.md"),
            summary_path=Path("daemon_loop_summary.json"),
        )[2]
        == "cycles_requested=None"
    )


def test_daemon_dry_run_lines_preserve_cli_order() -> None:
    result = DaemonDryRunResult(
        run_id="dry-1",
        status="planned",
        scheduled_for="2026-06-26T01:30:00+00:00",
        daemon_manifest_path=Path("data/ops/daemon_manifest.json"),
        schedule_path=Path("data/ops/scheduled_run.json"),
        operation_chain_path=Path("data/ops/operation_manifests.jsonl"),
        dry_run_snapshot_path=Path("data/ops/daemon_dry_run.json"),
    )

    assert daemon_dry_run_lines(result) == [
        "run_id=dry-1",
        "status=planned",
        "scheduled_for=2026-06-26T01:30:00+00:00",
        "operation_chain=data/ops/operation_manifests.jsonl",
    ]


def test_daemon_manifest_lines_preserve_cli_order() -> None:
    manifest = DaemonRunManifest(
        run_id="daemon-1",
        created_at="2026-06-26T01:00:00+00:00",
        mode="paper",
        command="uv run sis paper-step",
        state_store_path="data/state/marketlens.sqlite",
        notes=[],
    )

    assert daemon_manifest_lines(manifest) == [
        "run_id=daemon-1",
        "mode=paper",
    ]
