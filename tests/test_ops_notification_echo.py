from pathlib import Path

from sis.commands.ops_notification_echo import notification_outbox_lines


def test_notification_outbox_lines_preserve_cli_order(tmp_path: Path) -> None:
    record = {
        "notification_id": "note-123",
        "status": "queued",
        "sink": "local_outbox",
    }
    outbox_path = tmp_path / "notifications/outbox.jsonl"
    latest_path = tmp_path / "notifications/latest_notification.json"
    report_path = tmp_path / "reports/notification_outbox.md"
    summary_path = tmp_path / "ops/notification_outbox_summary.json"
    operation_chain_path = tmp_path / "ops/operation_manifests.jsonl"

    assert notification_outbox_lines(
        record,
        outbox_path=outbox_path,
        latest_path=latest_path,
        report_path=report_path,
        summary_path=summary_path,
        operation_chain_path=operation_chain_path,
    ) == [
        "notification_id=note-123",
        "status=queued",
        "sink=local_outbox",
        f"outbox_path={outbox_path}",
        f"latest_path={latest_path}",
        f"notification_outbox_report_path={report_path}",
        f"notification_outbox_summary_path={summary_path}",
        f"operation_chain={operation_chain_path}",
    ]


def test_notification_outbox_lines_match_missing_value_echo_behavior(tmp_path: Path) -> None:
    assert notification_outbox_lines(
        {},
        outbox_path=tmp_path / "outbox.jsonl",
        latest_path=tmp_path / "latest.json",
        report_path=tmp_path / "report.md",
        summary_path=tmp_path / "summary.json",
        operation_chain_path=tmp_path / "operation_manifests.jsonl",
    )[:3] == [
        "notification_id=None",
        "status=None",
        "sink=None",
    ]
