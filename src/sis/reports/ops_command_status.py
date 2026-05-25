from __future__ import annotations

from pathlib import Path

from sis.ops.daily_loss_limit import DailyLossStatus
from sis.ops.scheduler import ScheduledRun
from sis.storage.jsonl_store import write_json


def _recommended_read_order() -> list[str]:
    return [
        "docs/ACCEPTANCE_AUDIT.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "data/ops/operations_dashboard_summary.json",
        "data/ops/current_state_index.json",
        "data/ops/readiness_snapshot.json",
        "data/ops/phase_gate_review_summary.json",
    ]


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "ops_command_report": str(out_path),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def _write_report(
    *,
    title: str,
    summary: dict[str, object],
    detail_lines: list[str],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    lines = [f"# {title}", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(["## Overview", "", *detail_lines, "", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in _recommended_read_order())
    lines.append("")
    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text


def build_healthcheck_report(
    *,
    health: dict[str, object],
    daily_loss_status: DailyLossStatus,
    exposure_status: DailyLossStatus,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        **health,
        "daily_loss_allowed": daily_loss_status.allowed,
        "daily_loss_reason": daily_loss_status.reason,
        "exposure_allowed": exposure_status.allowed,
        "exposure_reason": exposure_status.reason,
        "healthcheck_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Ops Healthcheck",
        summary=summary,
        detail_lines=[
            f"- status: {summary.get('status')}",
            f"- kill_switch_enabled: {summary.get('kill_switch_enabled')}",
            f"- decision_summary_exists: {summary.get('decision_summary_exists')}",
            f"- audit_overall_status: {summary.get('audit_overall_status')}",
            f"- phase_gate_decision: {summary.get('phase_gate_decision')}",
            f"- phase2_entry_allowed: {summary.get('phase2_entry_allowed')}",
            f"- phase_gate_reason: {summary.get('phase_gate_reason')}",
            f"- execution_drift_overview_status: {summary.get('execution_drift_overview_status')}",
            f"- readiness_next_phase_candidate: {summary.get('readiness_next_phase_candidate')}",
            f"- readiness_execution_ready: {summary.get('readiness_execution_ready')}",
            f"- reconciliation_store_present: {summary.get('reconciliation_store_present')}",
            f"- daily_loss_allowed: {summary['daily_loss_allowed']}",
            f"- daily_loss_reason: {summary['daily_loss_reason']}",
            f"- exposure_allowed: {summary['exposure_allowed']}",
            f"- exposure_reason: {summary['exposure_reason']}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_kill_switch_report(
    *,
    status: dict[str, object],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        **status,
        "kill_switch_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Ops Kill Switch Status",
        summary=summary,
        detail_lines=[
            f"- enabled: {summary.get('enabled')}",
            f"- path: {summary.get('path')}",
            f"- details: {summary.get('details')}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_schedule_run_report(
    *,
    run: ScheduledRun,
    scheduled_run_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "run_type": run.run_type,
        "scheduled_for": run.scheduled_for.isoformat(),
        "command": run.command,
        "notes": run.notes,
        "scheduled_run_path": scheduled_run_path,
        "schedule_run_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Ops Scheduled Run",
        summary=summary,
        detail_lines=[
            f"- run_type: {summary['run_type']}",
            f"- scheduled_for: {summary['scheduled_for']}",
            f"- command: {summary['command']}",
            f"- notes: {','.join(run.notes)}",
            f"- scheduled_run_path: {summary['scheduled_run_path']}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_alert_report(
    *,
    level: str,
    title: str,
    body: str,
    source: str,
    alert_path: str,
    rendered_text: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "level": level,
        "title": title,
        "body": body,
        "source": source,
        "alert_path": alert_path,
        "rendered_text": rendered_text,
        "alert_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Ops Alert",
        summary=summary,
        detail_lines=[
            f"- level: {summary['level']}",
            f"- title: {summary['title']}",
            f"- source: {summary['source']}",
            f"- alert_path: {summary['alert_path']}",
            f"- rendered_text: {summary['rendered_text'].strip()}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )
