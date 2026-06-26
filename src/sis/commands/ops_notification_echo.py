from __future__ import annotations

from pathlib import Path
from typing import Any

import typer


def notification_outbox_lines(
    record: dict[str, Any],
    *,
    outbox_path: Path,
    latest_path: Path,
    report_path: Path,
    summary_path: Path,
    operation_chain_path: Path,
) -> list[str]:
    return [
        f"notification_id={record.get('notification_id')}",
        f"status={record.get('status')}",
        f"sink={record.get('sink')}",
        f"outbox_path={outbox_path}",
        f"latest_path={latest_path}",
        f"notification_outbox_report_path={report_path}",
        f"notification_outbox_summary_path={summary_path}",
        f"operation_chain={operation_chain_path}",
    ]


def echo_notification_outbox(
    record: dict[str, Any],
    *,
    outbox_path: Path,
    latest_path: Path,
    report_path: Path,
    summary_path: Path,
    operation_chain_path: Path,
) -> None:
    for line in notification_outbox_lines(
        record,
        outbox_path=outbox_path,
        latest_path=latest_path,
        report_path=report_path,
        summary_path=summary_path,
        operation_chain_path=operation_chain_path,
    ):
        typer.echo(line)
