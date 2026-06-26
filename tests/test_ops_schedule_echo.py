from datetime import datetime, timezone

from sis.commands.ops_schedule_echo import schedule_run_lines
from sis.ops.scheduler import ScheduledRun


def test_schedule_run_lines_preserve_cli_order() -> None:
    run = ScheduledRun(
        run_type="paper",
        scheduled_for=datetime(2026, 6, 26, 1, 30, tzinfo=timezone.utc),
        command="uv run sis paper-run",
        notes=[],
    )

    assert schedule_run_lines(run) == [
        "run_type=paper",
        "scheduled_for=2026-06-26T01:30:00+00:00",
    ]


def test_schedule_run_lines_use_scheduled_for_isoformat() -> None:
    run = ScheduledRun(
        run_type="audit",
        scheduled_for=datetime(2026, 6, 26, 10, 11, 12, 123456),
        command="uv run sis phase-gate-review",
        notes=["manual"],
    )

    assert schedule_run_lines(run)[1] == "scheduled_for=2026-06-26T10:11:12.123456"
