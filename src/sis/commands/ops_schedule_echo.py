from __future__ import annotations

import typer

from sis.ops.scheduler import ScheduledRun


def schedule_run_lines(run: ScheduledRun) -> list[str]:
    return [
        f"run_type={run.run_type}",
        f"scheduled_for={run.scheduled_for.isoformat()}",
    ]


def echo_schedule_run(run: ScheduledRun) -> None:
    for line in schedule_run_lines(run):
        typer.echo(line)
