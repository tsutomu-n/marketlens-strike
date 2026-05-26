from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evidence_report": str(out_path),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evidence_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _flatten_observed_sources(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    return []


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


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _planner_summary_from_checkpoint(checkpoint: dict) -> dict:
    session_path = checkpoint.get("remediation_session_summary_path")
    session = safe_read_json_dict(Path(session_path) if isinstance(session_path, str) else None)
    execution_plan_path = session.get("remediation_execution_plan_summary_path")
    execution_plan = safe_read_json_dict(
        Path(execution_plan_path) if isinstance(execution_plan_path, str) else None
    )
    planner_summary_path = execution_plan.get("remediation_planner_summary_path")
    return safe_read_json_dict(
        Path(planner_summary_path) if isinstance(planner_summary_path, str) else None
    )


def _derived_report_path(source: str, summary_path: Path | None) -> str | None:
    if summary_path is None:
        return None
    data_dir = summary_path.parent.parent
    report_map = {
        "phase_gate_review": data_dir / "reports/phase_gate_review.md",
        "paper_operations_runbook": data_dir / "reports/paper_operations_runbook.md",
    }
    report_path = report_map.get(source)
    return str(report_path) if report_path is not None else None


def _source_contexts(checkpoint: dict) -> dict[str, dict[str, object]]:
    planner = _planner_summary_from_checkpoint(checkpoint)
    source_paths = {
        "phase_gate_review": planner.get("phase_gate_summary_path"),
        "paper_operations_runbook": planner.get("runbook_summary_path"),
    }
    contexts: dict[str, dict[str, object]] = {}
    for source, raw_path in source_paths.items():
        path = Path(raw_path) if isinstance(raw_path, str) else None
        summary = safe_read_json_dict(path)
        explicit_report_path = None
        if source == "phase_gate_review":
            value = summary.get("phase_gate_review_report_path")
            explicit_report_path = value if isinstance(value, str) else None
        report_path = explicit_report_path or _derived_report_path(source, path)
        required_artifact_paths = (
            summary.get("required_artifact_paths")
            if isinstance(summary.get("required_artifact_paths"), dict)
            else {}
        )
        candidate_artifact_paths: list[str] = []
        if isinstance(raw_path, str):
            candidate_artifact_paths.append(raw_path)
        if report_path:
            candidate_artifact_paths.append(report_path)
        for value in required_artifact_paths.values():
            if isinstance(value, str) and value:
                candidate_artifact_paths.append(value)
        contexts[source] = {
            "summary_path": raw_path if isinstance(raw_path, str) else None,
            "report_path": report_path,
            "summary": summary,
            "required_artifact_paths": required_artifact_paths,
            "missing_required_artifact_paths": [
                item
                for item in summary.get("missing_required_artifact_paths", [])
                if isinstance(item, str)
            ],
            "candidate_artifact_paths": list(dict.fromkeys(candidate_artifact_paths)),
        }
    return contexts


def _needs_evidence(action: dict) -> bool:
    result = str(action.get("evaluation_result") or "")
    if result in {"manual_review", "partial"}:
        return True
    evaluations = action.get("signal_evaluations")
    if not isinstance(evaluations, list):
        return False
    return any(
        isinstance(item, dict) and str(item.get("status")) == "unsupported" for item in evaluations
    )


def _evidence_status(entries: list[dict[str, object]]) -> str:
    if not entries:
        return "no_manual_review_needed"
    if any(_as_int(item.get("unsupported_signal_count")) > 0 for item in entries):
        return "manual_review_required"
    return "partial_review_required"


def build_remediation_evidence(
    *,
    remediation_session_checkpoint_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    checkpoint = safe_read_json_dict(remediation_session_checkpoint_summary_path)
    evaluator = safe_read_json_dict(remediation_evaluator_summary_path)
    source_contexts = _source_contexts(checkpoint)
    actions = evaluator.get("actions") if isinstance(evaluator.get("actions"), list) else []
    checkpoint_actions = (
        checkpoint.get("actions") if isinstance(checkpoint.get("actions"), list) else []
    )
    checkpoint_actions_by_key = {
        str(item.get("action_key")): item
        for item in checkpoint_actions
        if isinstance(item, dict) and isinstance(item.get("action_key"), str)
    }

    evidence_entries: list[dict[str, object]] = []
    for action in actions:
        if not isinstance(action, dict) or not _needs_evidence(action):
            continue
        checkpoint_action = checkpoint_actions_by_key.get(str(action.get("action_key")), {})
        source = str(action.get("source") or "")
        context = source_contexts.get(source, {})
        signal_evaluations = (
            action.get("signal_evaluations")
            if isinstance(action.get("signal_evaluations"), list)
            else []
        )
        unresolved_signals = [
            item
            for item in signal_evaluations
            if isinstance(item, dict) and str(item.get("status")) != "pass"
        ]
        unsupported_signal_count = sum(
            1
            for item in unresolved_signals
            if isinstance(item, dict) and str(item.get("status")) == "unsupported"
        )
        signal_observed_sources = {
            str(item.get("signal")): item.get("observed_source")
            for item in unresolved_signals
            if isinstance(item, dict) and isinstance(item.get("signal"), str)
        }
        observed_sources: list[str] = []
        for source_name in _flatten_observed_sources(checkpoint_action.get("observed_sources")):
            if source_name not in observed_sources:
                observed_sources.append(source_name)
        for source_name in _flatten_observed_sources(action.get("observed_sources")):
            if source_name not in observed_sources:
                observed_sources.append(source_name)
        for source_name in _flatten_observed_sources(signal_observed_sources):
            if source_name not in observed_sources:
                observed_sources.append(source_name)
        evidence_entries.append(
            {
                "action_key": action.get("action_key"),
                "source": source,
                "reason": action.get("reason"),
                "stage": action.get("stage"),
                "command": action.get("command"),
                "evaluation_result": action.get("evaluation_result"),
                "checkpoint_status": action.get("checkpoint_status"),
                "evidence_status": action.get("evidence_status"),
                "suggested_result": action.get("suggested_result"),
                "operator_notes": action.get("operator_notes")
                if isinstance(action.get("operator_notes"), list)
                else [],
                "verification": action.get("verification")
                if isinstance(action.get("verification"), list)
                else [],
                "observed_sources": observed_sources,
                "signal_observed_sources": signal_observed_sources,
                "source_summary_path": context.get("summary_path"),
                "source_report_path": context.get("report_path"),
                "missing_required_artifact_paths": context.get(
                    "missing_required_artifact_paths", []
                ),
                "candidate_artifact_paths": context.get("candidate_artifact_paths", []),
                "unresolved_signals": unresolved_signals,
                "unsupported_signal_count": unsupported_signal_count,
            }
        )

    manual_review_action_count = sum(
        1 for item in evidence_entries if str(item.get("evaluation_result")) == "manual_review"
    )
    partial_action_count = sum(
        1 for item in evidence_entries if str(item.get("evaluation_result")) == "partial"
    )
    unsupported_signal_count = sum(
        _as_int(item.get("unsupported_signal_count")) for item in evidence_entries
    )
    next_manual_review_action_key = next(
        (
            item.get("action_key")
            for item in evidence_entries
            if str(item.get("evaluation_result")) in {"manual_review", "partial"}
        ),
        None,
    )
    summary = {
        "evidence_status": _evidence_status(evidence_entries),
        "manual_review_action_count": manual_review_action_count,
        "partial_action_count": partial_action_count,
        "unsupported_signal_count": unsupported_signal_count,
        "next_manual_review_action_key": next_manual_review_action_key,
        "observed_source_counts": _observed_source_counts(evidence_entries),
        "remediation_session_checkpoint_summary_path": (
            str(remediation_session_checkpoint_summary_path)
            if remediation_session_checkpoint_summary_path is not None
            else None
        ),
        "remediation_evaluator_summary_path": (
            str(remediation_evaluator_summary_path)
            if remediation_evaluator_summary_path is not None
            else None
        ),
        "entries": evidence_entries,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "remediation_evidence_report_path": str(out_path) if out_path is not None else None,
    }

    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)
    lines = ["# Remediation Evidence", ""]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(
        [
            "## Evidence Summary",
            "",
            f"- evidence_status: {summary['evidence_status']}",
            f"- manual_review_action_count: {summary['manual_review_action_count']}",
            f"- partial_action_count: {summary['partial_action_count']}",
            f"- unsupported_signal_count: {summary['unsupported_signal_count']}",
            f"- next_manual_review_action_key: {summary['next_manual_review_action_key']}",
            f"- remediation_session_checkpoint_summary_path: {summary['remediation_session_checkpoint_summary_path']}",
            f"- remediation_evaluator_summary_path: {summary['remediation_evaluator_summary_path']}",
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
            "## Evidence Candidates",
            "",
        ]
    )
    if evidence_entries:
        for item in evidence_entries:
            lines.append(f"- {item['action_key']}: `{item['command']}`")
            lines.append(f"  - evaluation_result: {item['evaluation_result']}")
            lines.append(f"  - observed_sources: {item['observed_sources']}")
            lines.append(f"  - signal_observed_sources: {item['signal_observed_sources']}")
            lines.append(f"  - source_summary_path: {item['source_summary_path']}")
            lines.append(f"  - source_report_path: {item['source_report_path']}")
            lines.append(
                f"  - missing_required_artifact_paths: {item['missing_required_artifact_paths']}"
            )
            lines.append("  - unresolved_signals:")
            unresolved_signals = (
                item["unresolved_signals"]
                if isinstance(item.get("unresolved_signals"), list)
                else []
            )
            for signal in unresolved_signals:
                if not isinstance(signal, dict):
                    continue
                lines.append(
                    "    - signal={signal} status={status} expected={expected} observed={observed}".format(
                        signal=signal.get("signal"),
                        status=signal.get("status"),
                        expected=signal.get("expected"),
                        observed=signal.get("observed"),
                    )
                )
            lines.append("  - candidate_artifact_paths:")
            candidate_artifact_paths = (
                item["candidate_artifact_paths"]
                if isinstance(item.get("candidate_artifact_paths"), list)
                else []
            )
            for path in candidate_artifact_paths:
                lines.append(f"    - {path}")
    else:
        lines.append("- evidence_candidates: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
