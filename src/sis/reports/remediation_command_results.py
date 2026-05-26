from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_command_results_report": str(out_path),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_command_results_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _observed_sources(action: dict) -> list[str]:
    values = action.get("observed_sources")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


def _observed_source_counts(entries: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        observed_sources = item.get("observed_sources")
        if not isinstance(observed_sources, list):
            continue
        for source in observed_sources:
            if isinstance(source, str):
                counts[source] = counts.get(source, 0) + 1
    return counts


def _command_results_status(entries: list[dict[str, object]]) -> str:
    if not entries:
        return "no_actions"
    if all(str(item.get("observation_status")) == "observed" for item in entries):
        return "fully_observed"
    if any(str(item.get("observation_status")) == "observed" for item in entries):
        return "partially_observed"
    return "observation_missing"


def build_remediation_command_results(
    *,
    remediation_session_checkpoint_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    checkpoint = safe_read_json_dict(remediation_session_checkpoint_summary_path)
    actions = checkpoint.get("actions") if isinstance(checkpoint.get("actions"), list) else []
    entries: list[dict[str, object]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        evidence_paths = (
            action.get("evidence_paths") if isinstance(action.get("evidence_paths"), list) else []
        )
        observed_signals = (
            action.get("observed_signals")
            if isinstance(action.get("observed_signals"), list)
            else []
        )
        unique_evidence_paths = list(
            dict.fromkeys(str(value) for value in evidence_paths if isinstance(value, str))
        )
        unique_observed_signals = list(
            dict.fromkeys(str(value) for value in observed_signals if isinstance(value, str))
        )
        observation_status = (
            "observed" if unique_evidence_paths or unique_observed_signals else "missing"
        )
        entries.append(
            {
                "action_key": action.get("action_key"),
                "source": action.get("source"),
                "reason": action.get("reason"),
                "stage": action.get("stage"),
                "command": action.get("command"),
                "checkpoint_status": action.get("checkpoint_status"),
                "observation_status": observation_status,
                "observed_sources": _observed_sources(action),
                "signal_observed_sources": (
                    action.get("signal_observed_sources")
                    if isinstance(action.get("signal_observed_sources"), dict)
                    else {}
                ),
                "evidence_paths": unique_evidence_paths,
                "observed_signals": unique_observed_signals,
                "latest_exit_code": action.get("latest_exit_code"),
                "latest_stdout_summary": action.get("latest_stdout_summary"),
                "latest_stderr_summary": action.get("latest_stderr_summary"),
                "command_result_records": (
                    action.get("command_result_records")
                    if isinstance(action.get("command_result_records"), list)
                    else []
                ),
            }
        )

    observed_action_count = sum(
        1 for item in entries if str(item.get("observation_status")) == "observed"
    )
    missing_observation_count = sum(
        1 for item in entries if str(item.get("observation_status")) != "observed"
    )
    next_unobserved_action_key = next(
        (
            item.get("action_key")
            for item in entries
            if str(item.get("observation_status")) != "observed"
        ),
        None,
    )
    summary = {
        "command_results_status": _command_results_status(entries),
        "planned_action_count": len(entries),
        "observed_action_count": observed_action_count,
        "missing_observation_count": missing_observation_count,
        "next_unobserved_action_key": next_unobserved_action_key,
        "observed_source_counts": _observed_source_counts(entries),
        "remediation_session_checkpoint_summary_path": (
            str(remediation_session_checkpoint_summary_path)
            if remediation_session_checkpoint_summary_path is not None
            else None
        ),
        "entries": entries,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "remediation_command_results_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Remediation Command Results", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Command Results Summary",
            "",
            f"- command_results_status: {summary['command_results_status']}",
            f"- planned_action_count: {summary['planned_action_count']}",
            f"- observed_action_count: {summary['observed_action_count']}",
            f"- missing_observation_count: {summary['missing_observation_count']}",
            f"- next_unobserved_action_key: {summary['next_unobserved_action_key']}",
            f"- remediation_session_checkpoint_summary_path: {summary['remediation_session_checkpoint_summary_path']}",
            "",
            "## Observed Source Counts",
            "",
        ]
    )
    if summary["observed_source_counts"]:
        for key in sorted(summary["observed_source_counts"]):
            lines.append(f"- {key}: {summary['observed_source_counts'][key]}")
    else:
        lines.append("- observed_source_counts: none")

    lines.extend(
        [
            "",
            "## Action Command Results",
            "",
        ]
    )
    if entries:
        for item in entries:
            lines.append(f"- {item['action_key']}: `{item['command']}`")
            lines.append(f"  - checkpoint_status: {item['checkpoint_status']}")
            lines.append(f"  - observation_status: {item['observation_status']}")
            lines.append(f"  - observed_sources: {item['observed_sources']}")
            lines.append(f"  - signal_observed_sources: {item['signal_observed_sources']}")
            lines.append(f"  - evidence_paths: {item['evidence_paths']}")
            lines.append(f"  - observed_signals: {item['observed_signals']}")
            lines.append(f"  - latest_exit_code: {item['latest_exit_code']}")
            lines.append(f"  - latest_stdout_summary: {item['latest_stdout_summary']}")
            lines.append(f"  - latest_stderr_summary: {item['latest_stderr_summary']}")
    else:
        lines.append("- action_command_results: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
