from __future__ import annotations

import csv
import html
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sis.reports.loaders import safe_read_json_dict, safe_read_json_dict_list
from sis.reports.quote_diagnostics import QuoteDiagnostic, build_quote_diagnostics
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_fields_from_payload,
    latest_execution_payload_and_fields_from_summary,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.validation.artifacts import ValidationSummary, validate_artifacts

RunStatus = str


@dataclass(frozen=True)
class LiveEvidenceArtifacts:
    sidecar_metadata: Path
    sidecar_pricing: Path
    raw_quotes: Path
    normalized_quotes: Path
    cost_matrix: Path
    backtest_metrics: Path
    go_no_go_report: Path
    evidence_card: Path | None


@dataclass(frozen=True)
class LiveEvidenceReportData:
    status: RunStatus
    log_path: Path
    manifest_path: Path | None
    output_path: Path
    started_at_utc: str | None
    finished_at_utc: str | None
    decision: str | None
    venue_decisions: list[dict]
    blockers: list[str]
    next_actions: list[str]
    audit_summary: dict[str, Any]
    phase_gate_summary: dict[str, Any]
    readiness_summary: dict[str, Any]
    timeline_latest_execution_summary: dict[str, Any]
    timeline_latest_execution_comparison_summary: dict[str, Any]
    bundle_history_latest_execution_summary: dict[str, Any]
    bundle_history_latest_execution_comparison_summary: dict[str, Any]
    cycle_history_latest_execution_summary: dict[str, Any]
    cycle_history_latest_execution_comparison_summary: dict[str, Any]
    execution_summary: dict[str, Any]
    execution_comparison_summary: dict[str, Any]
    execution_diagnostics_summary: dict[str, Any]
    execution_gap_history_summary: dict[str, Any]
    execution_state_comparison_summary: dict[str, Any]
    execution_snapshot_drift_summary: dict[str, Any]
    execution_drift_overview_summary: dict[str, Any]
    quote_diagnostics: list[QuoteDiagnostic]
    cost_rows: list[dict[str, str]]
    backtest_metrics: list[dict]
    validation: ValidationSummary
    artifacts: LiveEvidenceArtifacts
    log_tail: list[str]
    row_counts: dict[str, int]


def _latest_execution_lineage_flat_values(
    data: LiveEvidenceReportData,
) -> dict[str, Any]:
    return latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=data.timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(
            data.timeline_latest_execution_comparison_summary
        ),
        bundle_history_latest_execution_summary=(data.bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            data.bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=(data.cycle_history_latest_execution_summary),
        cycle_history_latest_execution_comparison_summary=(
            data.cycle_history_latest_execution_comparison_summary
        ),
    )


def _latest_execution_lineage_markdown_lines(
    latest_execution_flat: Mapping[str, Any],
) -> list[str]:
    return [
        (
            "- timeline_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('timeline_latest_execution_overall_status')}`"
        ),
        (
            "- timeline_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('timeline_latest_execution_venue_count')}`"
        ),
        (
            "- timeline_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('timeline_latest_execution_comparison_all_registries_present')}`"
        ),
        (
            "- bundle_history_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_overall_status')}`"
        ),
        (
            "- bundle_history_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_venue_count')}`"
        ),
        (
            "- bundle_history_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_comparison_all_registries_present')}`"
        ),
        (
            "- cycle_history_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_overall_status')}`"
        ),
        (
            "- cycle_history_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_venue_count')}`"
        ),
        (
            "- cycle_history_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_comparison_all_registries_present')}`"
        ),
    ]


def _latest_execution_lineage_html_metrics(
    latest_execution_flat: Mapping[str, Any],
) -> str:
    metrics = [
        (
            "Timeline Overall Status",
            latest_execution_flat.get("timeline_latest_execution_overall_status"),
        ),
        (
            "Timeline Venue Count",
            latest_execution_flat.get("timeline_latest_execution_venue_count"),
        ),
        (
            "Timeline Comparison",
            latest_execution_flat.get(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
        ),
        (
            "Bundle History Overall Status",
            latest_execution_flat.get("bundle_history_latest_execution_overall_status"),
        ),
        (
            "Bundle History Venue Count",
            latest_execution_flat.get("bundle_history_latest_execution_venue_count"),
        ),
        (
            "Bundle History Comparison",
            latest_execution_flat.get(
                "bundle_history_latest_execution_comparison_all_registries_present"
            ),
        ),
        (
            "Cycle History Overall Status",
            latest_execution_flat.get("cycle_history_latest_execution_overall_status"),
        ),
        (
            "Cycle History Venue Count",
            latest_execution_flat.get("cycle_history_latest_execution_venue_count"),
        ),
        (
            "Cycle History Comparison",
            latest_execution_flat.get(
                "cycle_history_latest_execution_comparison_all_registries_present"
            ),
        ),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
    )


def _remediation_markdown_lines(readiness_summary: Mapping[str, Any]) -> list[str]:
    return [
        (
            "- planner_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_status')}`"
        ),
        (
            "- planner_next_best_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_next_best_command')}`"
        ),
        (
            "- planner_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}`"
        ),
        (
            "- execution_plan_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_status')}`"
        ),
        (
            "- execution_plan_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_next_action_command')}`"
        ),
        (
            "- execution_plan_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}`"
        ),
        (
            "- session_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_status')}`"
        ),
        (
            "- session_next_pending_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_next_pending_command')}`"
        ),
        (
            "- session_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_feedback_priority_reason')}`"
        ),
        (
            "- checkpoint_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_status')}`"
        ),
        (
            "- checkpoint_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_next_action_command')}`"
        ),
        (
            "- checkpoint_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}`"
        ),
        (
            "- scoreboard_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_status')}`"
        ),
        (
            "- scoreboard_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_next_action_command')}`"
        ),
        (
            "- scoreboard_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}`"
        ),
    ]


def _remediation_html_metrics(readiness_summary: Mapping[str, Any]) -> str:
    metrics = [
        ("Planner Status", readiness_summary.get("timeline_latest_remediation_planner_status")),
        (
            "Planner Next Best Command",
            readiness_summary.get("timeline_latest_remediation_planner_next_best_command"),
        ),
        (
            "Planner Feedback Reason",
            readiness_summary.get("timeline_latest_remediation_planner_feedback_priority_reason"),
        ),
        (
            "Execution Plan Status",
            readiness_summary.get("timeline_latest_remediation_execution_plan_status"),
        ),
        (
            "Execution Plan Next Action",
            readiness_summary.get("timeline_latest_remediation_execution_plan_next_action_command"),
        ),
        (
            "Execution Plan Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_execution_plan_feedback_priority_reason"
            ),
        ),
        ("Session Status", readiness_summary.get("timeline_latest_remediation_session_status")),
        (
            "Session Next Pending Command",
            readiness_summary.get("timeline_latest_remediation_session_next_pending_command"),
        ),
        (
            "Session Feedback Reason",
            readiness_summary.get("timeline_latest_remediation_session_feedback_priority_reason"),
        ),
        (
            "Checkpoint Status",
            readiness_summary.get("timeline_latest_remediation_checkpoint_status"),
        ),
        (
            "Checkpoint Next Action",
            readiness_summary.get("timeline_latest_remediation_checkpoint_next_action_command"),
        ),
        (
            "Checkpoint Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_checkpoint_feedback_priority_reason"
            ),
        ),
        (
            "Scoreboard Status",
            readiness_summary.get("timeline_latest_remediation_scoreboard_status"),
        ),
        (
            "Scoreboard Next Action",
            readiness_summary.get("timeline_latest_remediation_scoreboard_next_action_command"),
        ),
        (
            "Scoreboard Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_scoreboard_feedback_priority_reason"
            ),
        ),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
    )


def _restart_pointer_lines(readiness_summary: Mapping[str, Any]) -> list[str]:
    keys = (
        "readiness_snapshot_report",
        "current_state_index_report",
        "remediation_scoreboard_report",
        "remediation_session_checkpoint_report",
        "remediation_session_report",
        "remediation_execution_plan_report",
        "remediation_planner_report",
        "live_evidence_report",
    )
    return [
        f"- {key}: `{readiness_summary.get(key)}`"
        for key in keys
        if readiness_summary.get(key) is not None
    ]


def _restart_pointer_html_metrics(readiness_summary: Mapping[str, Any]) -> str:
    metrics = [
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "Remediation Session Checkpoint Report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("Remediation Session Report", readiness_summary.get("remediation_session_report")),
        (
            "Remediation Execution Plan Report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("Remediation Planner Report", readiness_summary.get("remediation_planner_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )


def _related_report_lines(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> list[str]:
    items = (
        ("phase_gate_review_report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("readiness_snapshot_report", readiness_summary.get("readiness_snapshot_report")),
        ("current_state_index_report", readiness_summary.get("current_state_index_report")),
        ("remediation_scoreboard_report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "remediation_session_checkpoint_report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("remediation_session_report", readiness_summary.get("remediation_session_report")),
        (
            "remediation_execution_plan_report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("remediation_planner_report", readiness_summary.get("remediation_planner_report")),
        ("live_evidence_report", readiness_summary.get("live_evidence_report")),
    )
    return [f"- {key}: `{value}`" for key, value in items if value is not None]


def _related_report_html_metrics(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> str:
    metrics = [
        ("Phase Gate Review Report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "Remediation Session Checkpoint Report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("Remediation Session Report", readiness_summary.get("remediation_session_report")),
        (
            "Remediation Execution Plan Report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("Remediation Planner Report", readiness_summary.get("remediation_planner_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )


def _quick_navigation_lines(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> list[str]:
    items = (
        ("current_state_index_report", readiness_summary.get("current_state_index_report")),
        ("readiness_snapshot_report", readiness_summary.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("remediation_scoreboard_report", readiness_summary.get("remediation_scoreboard_report")),
        ("live_evidence_report", readiness_summary.get("live_evidence_report")),
    )
    return [f"- {key}: `{value}`" for key, value in items if value is not None]


def _quick_navigation_html_metrics(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> str:
    metrics = [
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Phase Gate Review Report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )


def parse_run_status(log_path: Path) -> RunStatus:
    if not log_path.exists():
        return "running"
    text = log_path.read_text(encoding="utf-8")
    if "Live evidence refresh completed" in text:
        return "completed"
    if "ERROR:" in text or "Traceback" in text or "Missing required" in text:
        return "failed"
    return "running"


def parse_manifest_status(manifest_path: Path | None) -> RunStatus | None:
    payload = safe_read_json_dict(manifest_path)
    status = payload.get("status")
    if isinstance(status, str):
        return status
    return None


def load_manifest_payload(manifest_path: Path | None) -> dict[str, Any]:
    return safe_read_json_dict(manifest_path)


def _summary_from_payload(payload: dict[str, Any], key: str) -> dict[str, Any]:
    summary = payload.get(key)
    return summary if isinstance(summary, dict) else {}


def _summary_from_manifest_or_evidence(
    manifest: dict[str, Any],
    evidence_payload: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    return _summary_from_payload(manifest, key) or _summary_from_payload(evidence_payload, key)


def refresh_process_running() -> bool:
    result = subprocess.run(
        ["ps", "-ef"],
        check=False,
        capture_output=True,
        text=True,
    )
    haystack = result.stdout
    needles = (
        "scripts/refresh_live_evidence.sh",
        "tsx src/collect_window.ts",
        "src/collect_window.ts --duration-minutes",
    )
    return any(needle in haystack for needle in needles)


def wait_for_completion(
    log_path: Path | None,
    *,
    manifest_path: Path | None = None,
    poll_seconds: int = 15,
    timeout_seconds: int = 3 * 60 * 60,
) -> RunStatus:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        manifest_status = parse_manifest_status(manifest_path)
        if manifest_status and manifest_status != "running":
            return manifest_status
        status = parse_run_status(log_path) if log_path is not None else "running"
        if status != "running":
            return status
        if not refresh_process_running() and log_path is not None and log_path.exists():
            return "failed"
        time.sleep(poll_seconds)
    return "failed"


def _extract_timestamp(line: str) -> str | None:
    if line.startswith("[") and "]" in line:
        return line[1 : line.index("]")]
    return None


def _latest_evidence_card(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    return paths[-1] if paths else None


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _load_cost_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_backtest_metrics(path: Path) -> list[dict]:
    return safe_read_json_dict_list(path)


def _started_finished(log_lines: list[str]) -> tuple[str | None, str | None]:
    started = None
    finished = None
    for line in log_lines:
        if "Scheduled live evidence run starting" in line and started is None:
            started = _extract_timestamp(line)
        if "Live evidence refresh completed" in line:
            finished = _extract_timestamp(line)
    return started, finished


def build_live_evidence_report_data(
    *,
    data_dir: Path,
    log_path: Path | None,
    output_path: Path,
    manifest_path: Path | None = None,
    status: RunStatus | None = None,
    audit_summary: dict[str, Any] | None = None,
) -> LiveEvidenceReportData:
    manifest = load_manifest_payload(manifest_path)
    artifact_paths = (
        manifest.get("artifacts", {}) if isinstance(manifest.get("artifacts"), dict) else {}
    )
    today_utc = datetime.now(timezone.utc).date().isoformat()
    evidence_card_path = artifact_paths.get("evidence_card")
    evidence_card = (
        Path(evidence_card_path)
        if isinstance(evidence_card_path, str) and evidence_card_path
        else _latest_evidence_card(data_dir)
    )
    artifacts = LiveEvidenceArtifacts(
        sidecar_metadata=Path(
            artifact_paths.get(
                "sidecar_metadata", data_dir / f"raw/sidecar/gtrade/{today_utc}.jsonl"
            )
        ),
        sidecar_pricing=Path(
            artifact_paths.get(
                "sidecar_pricing", data_dir / f"raw/sidecar/gtrade-pricing/{today_utc}.jsonl"
            )
        ),
        raw_quotes=Path(
            artifact_paths.get("raw_quotes", data_dir / f"raw/quotes/gtrade/{today_utc}.jsonl")
        ),
        normalized_quotes=Path(
            artifact_paths.get("normalized_quotes", data_dir / "normalized/quotes.parquet")
        ),
        cost_matrix=Path(
            artifact_paths.get("cost_matrix", data_dir / "research/venue_cost_matrix.csv")
        ),
        backtest_metrics=Path(
            artifact_paths.get("backtest_metrics", data_dir / "research/backtest_metrics.json")
        ),
        go_no_go_report=Path(
            artifact_paths.get("go_no_go_report", data_dir / "research/go_no_go_report.md")
        ),
        evidence_card=evidence_card,
    )
    manifest_status = parse_manifest_status(manifest_path)
    resolved_status = (
        status
        or manifest_status
        or (parse_run_status(log_path) if log_path is not None else "running")
    )
    evidence_payload = load_manifest_payload(evidence_card)
    venue_decisions = (
        evidence_payload.get("venue_decisions", []) if isinstance(evidence_payload, dict) else []
    )
    blockers = manifest.get("blockers", []) if isinstance(manifest.get("blockers"), list) else []
    next_actions = (
        manifest.get("next_actions", []) if isinstance(manifest.get("next_actions"), list) else []
    )
    phase_gate_summary = _summary_from_manifest_or_evidence(
        manifest, evidence_payload, "phase_gate_summary"
    )
    execution_summary = _summary_from_manifest_or_evidence(
        manifest, evidence_payload, "execution_summary"
    )
    execution_comparison_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_comparison_summary",
    )
    execution_diagnostics_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_diagnostics_summary",
    )
    execution_gap_history_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_gap_history_summary",
    )
    execution_state_comparison_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_state_comparison_summary",
    )
    execution_snapshot_drift_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_snapshot_drift_summary",
    )
    execution_drift_overview_summary = _summary_from_manifest_or_evidence(
        manifest,
        evidence_payload,
        "execution_drift_overview_summary",
    )
    readiness_summary = _summary_from_manifest_or_evidence(
        manifest, evidence_payload, "readiness_summary"
    )
    if not blockers and isinstance(evidence_payload, dict):
        blockers = evidence_payload.get("blockers", [])
    if not next_actions and isinstance(evidence_payload, dict):
        next_actions = evidence_payload.get("next_actions", [])
    decision = manifest.get("decision") if isinstance(manifest.get("decision"), str) else None
    if decision is None and isinstance(evidence_payload, dict):
        decision = evidence_payload.get("decision")
    diagnostics = build_quote_diagnostics(
        data_dir / "raw/quotes",
        venue="gtrade",
        stale_thresholds_ms={"gtrade": 3000, "ostium": 5000},
    )
    if not diagnostics and isinstance(manifest.get("diagnostics"), list):
        diagnostics = []
        for item in manifest["diagnostics"]:
            if not isinstance(item, dict):
                continue
            try:
                diagnostics.append(QuoteDiagnostic(**item))
            except TypeError:
                continue
    cost_rows = _load_cost_rows(artifacts.cost_matrix)
    backtest_metrics = _load_backtest_metrics(artifacts.backtest_metrics)
    validation = validate_artifacts(data_dir, Path("schemas"), strict=False)
    log_lines = (
        log_path.read_text(encoding="utf-8").splitlines()
        if log_path is not None and log_path.exists()
        else []
    )
    started_at_utc, finished_at_utc = _started_finished(log_lines)
    started_at_utc = manifest.get("started_at_utc") or started_at_utc
    finished_at_utc = manifest.get("finished_at_utc") or finished_at_utc
    manifest_row_counts = (
        manifest.get("row_counts", {}) if isinstance(manifest.get("row_counts"), dict) else {}
    )
    row_counts = {
        "sidecar_metadata": int(
            manifest_row_counts.get(
                "sidecar_metadata", _count_jsonl_rows(artifacts.sidecar_metadata)
            )
        ),
        "sidecar_pricing": int(
            manifest_row_counts.get("sidecar_pricing", _count_jsonl_rows(artifacts.sidecar_pricing))
        ),
        "raw_quotes": int(
            manifest_row_counts.get("raw_quotes", _count_jsonl_rows(artifacts.raw_quotes))
        ),
    }
    latest_execution_payload, latest_execution_lineage = (
        latest_execution_payload_and_fields_from_summary(evidence_payload)
    )
    return LiveEvidenceReportData(
        status=resolved_status,
        log_path=log_path or Path(""),
        manifest_path=manifest_path,
        output_path=output_path,
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
        decision=decision,
        venue_decisions=venue_decisions if isinstance(venue_decisions, list) else [],
        blockers=blockers if isinstance(blockers, list) else [],
        next_actions=next_actions if isinstance(next_actions, list) else [],
        audit_summary=audit_summary if isinstance(audit_summary, dict) else {},
        phase_gate_summary=normalize_phase_gate_summary(phase_gate_summary),
        readiness_summary=normalize_readiness_summary(readiness_summary),
        **latest_execution_payload,
        execution_summary=normalize_execution_snapshot_summary(execution_summary),
        execution_comparison_summary=normalize_execution_comparison_summary(
            execution_comparison_summary
        ),
        execution_diagnostics_summary=normalize_execution_diagnostics_summary(
            execution_diagnostics_summary
        ),
        execution_gap_history_summary=normalize_execution_gap_history_summary(
            execution_gap_history_summary
        ),
        execution_state_comparison_summary=normalize_execution_state_comparison_summary(
            execution_state_comparison_summary
        ),
        execution_snapshot_drift_summary=normalize_execution_snapshot_drift_summary(
            execution_snapshot_drift_summary
        ),
        execution_drift_overview_summary=normalize_execution_drift_overview_summary(
            execution_drift_overview_summary
        ),
        quote_diagnostics=diagnostics,
        cost_rows=cost_rows,
        backtest_metrics=backtest_metrics,
        validation=validation,
        artifacts=artifacts,
        log_tail=log_lines[-40:],
        row_counts=row_counts,
    )


def render_live_evidence_report(data: LiveEvidenceReportData) -> str:
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = _latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)
    lines: list[str] = []
    lines.append("# Live Evidence Detailed Report")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append(f"- run_status: `{data.status}`")
    lines.append(f"- started_at_utc: `{data.started_at_utc}`")
    lines.append(f"- finished_at_utc: `{data.finished_at_utc}`")
    lines.append(f"- decision: `{data.decision}`")
    lines.append(f"- log_path: `{data.log_path}`")
    lines.append(f"- manifest_path: `{data.manifest_path}`")
    lines.append("")
    if data.audit_summary:
        lines.append("## Audit Summary")
        lines.append("")
        lines.append(f"- overall_status: `{audit_summary_flat.get('overall_status')}`")
        lines.append(f"- latest_operation: `{audit_summary_flat.get('latest_operation')}`")
        lines.append(
            "- bundle_history_snapshot_count: "
            f"`{audit_summary_flat.get('bundle_history_snapshot_count')}`"
        )
        lines.append("")
    if data.phase_gate_summary:
        lines.append("## Phase Gate Summary")
        lines.append("")
        lines.append(f"- decision: `{phase_gate_flat.get('phase_gate_decision')}`")
        lines.append(f"- phase2_entry_allowed: `{phase_gate_flat.get('phase2_entry_allowed')}`")
        lines.append(f"- phase_gate_reason: `{phase_gate_flat.get('phase_gate_reason')}`")
        lines.append(
            f"- strict_validation_passed: `{phase_gate_flat.get('strict_validation_passed')}`"
        )
        lines.append(
            "- phase_gate_strict_validation_issue_count: "
            f"`{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}`"
        )
        lines.append(
            f"- phase_gate_checked_files: `{phase_gate_flat.get('phase_gate_checked_files')}`"
        )
        lines.append("")
    if data.readiness_summary:
        lines.append("## Readiness Summary")
        lines.append("")
        lines.append(
            f"- next_phase_candidate: `{readiness_flat.get('readiness_next_phase_candidate')}`"
        )
        lines.append(f"- execution_ready: `{readiness_flat.get('readiness_execution_ready')}`")
        lines.append("")
        if data.readiness_summary.get("timeline_latest_remediation_planner_status") is not None:
            lines.append("## Current Remediation Queue")
            lines.append("")
            lines.extend(_remediation_markdown_lines(data.readiness_summary))
            lines.append("")
        restart_pointer_lines = _restart_pointer_lines(data.readiness_summary)
        if restart_pointer_lines:
            lines.append("## Restart Pointers")
            lines.append("")
            lines.extend(restart_pointer_lines)
            lines.append("")
        quick_navigation_lines = _quick_navigation_lines(
            data.readiness_summary,
            data.phase_gate_summary,
        )
        if quick_navigation_lines:
            lines.append("## Quick Navigation")
            lines.append("")
            lines.extend(quick_navigation_lines)
            lines.append("")
        related_report_lines = _related_report_lines(
            data.readiness_summary,
            data.phase_gate_summary,
        )
        if related_report_lines:
            lines.append("## Related Reports")
            lines.append("")
            lines.extend(related_report_lines)
            lines.append("")
    if any(
        (
            data.timeline_latest_execution_summary,
            data.bundle_history_latest_execution_summary,
            data.cycle_history_latest_execution_summary,
        )
    ):
        lines.append("## Latest Execution Lineage")
        lines.append("")
        lines.extend(_latest_execution_lineage_markdown_lines(latest_execution_flat))
        lines.append("")
    if data.execution_summary:
        lines.append("## Execution Snapshot")
        lines.append("")
        lines.append(
            f"- overall_status: `{execution_summary_flat.get('execution_overall_status')}`"
        )
        lines.append(f"- venue_count: `{execution_summary_flat.get('execution_venue_count')}`")
        lines.append(f"- report_path: `{execution_summary_flat.get('execution_report_path')}`")
        lines.append("")
    if data.execution_comparison_summary:
        lines.append("## Execution Venue Comparison")
        lines.append("")
        lines.append(
            "- all_registries_present: "
            f"`{execution_comparison_flat.get('execution_comparison_all_registries_present')}`"
        )
        lines.append(
            f"- report_path: `{execution_comparison_flat.get('execution_comparison_report_path')}`"
        )
        lines.append("")
    if data.execution_diagnostics_summary:
        lines.append("## Execution Venue Diagnostics")
        lines.append("")
        lines.append(
            f"- overall_status: `{execution_diagnostics_flat.get('execution_diagnostics_status')}`"
        )
        lines.append(
            f"- balance_gap_detected: `{execution_diagnostics_flat.get('execution_balance_gap_detected')}`"
        )
        lines.append(
            f"- fills_gap_detected: `{execution_diagnostics_flat.get('execution_fills_gap_detected')}`"
        )
        lines.append(
            f"- report_path: `{execution_diagnostics_flat.get('execution_diagnostics_report_path')}`"
        )
        lines.append("")
    if data.execution_gap_history_summary:
        lines.append("## Execution Gap History")
        lines.append("")
        lines.append(
            f"- entry_count: `{execution_gap_history_flat.get('execution_gap_history_entry_count')}`"
        )
        lines.append(
            f"- latest_status: `{execution_gap_history_flat.get('execution_gap_history_latest_status')}`"
        )
        lines.append(
            "- latest_execution_diagnostics_status: "
            f"`{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status')}`"
        )
        lines.append(
            f"- report_path: `{execution_gap_history_flat.get('execution_gap_history_report_path')}`"
        )
        lines.append("")
    if data.execution_state_comparison_summary:
        lines.append("## Execution State Comparison History")
        lines.append("")
        lines.append(
            f"- entry_count: `{execution_state_comparison_flat.get('execution_state_comparison_entry_count')}`"
        )
        lines.append(
            "- latest_status_match: "
            f"`{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}`"
        )
        lines.append(
            "- mismatching_count: "
            f"`{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}`"
        )
        lines.append(
            f"- report_path: `{execution_state_comparison_flat.get('execution_state_comparison_report_path')}`"
        )
        lines.append("")
    if data.execution_snapshot_drift_summary:
        lines.append("## Execution Snapshot Drift History")
        lines.append("")
        lines.append(
            f"- entry_count: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}`"
        )
        lines.append(
            "- latest_execution_state_comparison_status_match: "
            f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}`"
        )
        lines.append(
            "- mismatching_snapshot_count: "
            f"`{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}`"
        )
        lines.append(
            f"- report_path: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path')}`"
        )
        lines.append("")
    if data.execution_drift_overview_summary:
        lines.append("## Execution Drift Overview")
        lines.append("")
        lines.append(
            f"- overall_status: `{execution_drift_flat.get('execution_drift_overview_status')}`"
        )
        lines.append(
            f"- diagnostics_alignment_match: `{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}`"
        )
        lines.append(
            f"- state_comparison_mismatching_count: `{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}`"
        )
        lines.append(
            f"- snapshot_drift_mismatching_snapshot_count: `{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}`"
        )
        lines.append("")
    lines.append("## Artifact Summary")
    lines.append("")
    lines.append(f"- sidecar_metadata_rows: `{data.row_counts['sidecar_metadata']}`")
    lines.append(f"- sidecar_pricing_rows: `{data.row_counts['sidecar_pricing']}`")
    lines.append(f"- raw_quote_rows: `{data.row_counts['raw_quotes']}`")
    lines.append(f"- normalized_quotes: `{data.artifacts.normalized_quotes}`")
    lines.append(f"- cost_matrix: `{data.artifacts.cost_matrix}`")
    lines.append(f"- backtest_metrics: `{data.artifacts.backtest_metrics}`")
    lines.append(f"- go_no_go_report: `{data.artifacts.go_no_go_report}`")
    lines.append(f"- evidence_card: `{data.artifacts.evidence_card}`")
    lines.append("")
    lines.append("## Venue Decisions")
    lines.append("")
    lines.append("| Venue | Decision | Main Blocker |")
    lines.append("|---|---|---|")
    for item in data.venue_decisions:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {item.get('venue', '')} | {item.get('decision', '')} | {item.get('main_blocker', '') or ''} |"
        )
    lines.append("")
    lines.append("## GTrade Diagnostics")
    lines.append("")
    lines.append(
        "| Symbol | Rows | Open Rows | Tradable Rate | Stale Rate | Missing Mark | Missing Index | Oracle p90 ms | Spread p90 bps |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for item in data.quote_diagnostics:
        lines.append(
            f"| {item.symbol} | {item.rows} | {item.market_open_rows} | {item.tradable_rate:.4f} | {item.stale_rate:.4f} | "
            f"{item.missing_mark_price_rate:.4f} | {item.missing_index_price_rate:.4f} | {item.oracle_age_p90_ms} | {item.spread_p90_bps} |"
        )
    lines.append("")
    lines.append("## Cost Matrix Snapshot")
    lines.append("")
    lines.append(
        "| Venue | Symbol | Stale Rate | Tradable Rate | Spread p90 bps | Holding 4h bps | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in data.cost_rows:
        lines.append(
            f"| {row.get('venue', '')} | {row.get('symbol', '')} | {row.get('stale_rate', '')} | "
            f"{row.get('tradable_rate', '')} | {row.get('spread_p90_bps', '')} | {row.get('holding_cost_4h_bps', '')} | {row.get('notes', '')} |"
        )
    lines.append("")
    lines.append("## Backtest Snapshot")
    lines.append("")
    lines.append(
        "| Venue | Symbol | Trade Count | Avg Trade Return | Cost Drag bps | Stale Rejected | Halt Rejected |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in data.backtest_metrics:
        lines.append(
            f"| {row.get('venue', '')} | {row.get('canonical_symbol', '')} | {row.get('trade_count', '')} | "
            f"{row.get('avg_trade_return', '')} | {row.get('cost_drag_bps', '')} | {row.get('stale_rejected_count', '')} | "
            f"{row.get('halt_rejected_count', '')} |"
        )
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append(f"- checked_files: `{data.validation.checked_files}`")
    lines.append(f"- issue_count: `{len(data.validation.issues)}`")
    for issue in data.validation.issues:
        lines.append(f"- {issue.path}: {issue.message}")
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if data.blockers:
        lines.extend(f"- {item}" for item in data.blockers)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    if data.next_actions:
        lines.extend(f"- {item}" for item in data.next_actions)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Log Tail")
    lines.append("")
    lines.append("```text")
    lines.extend(data.log_tail)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_live_evidence_html(data: LiveEvidenceReportData) -> str:
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = _latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    remediation_metrics = _remediation_html_metrics(data.readiness_summary)
    restart_pointer_metrics = _restart_pointer_html_metrics(data.readiness_summary)
    quick_navigation_metrics = _quick_navigation_html_metrics(
        data.readiness_summary,
        data.phase_gate_summary,
    )
    related_report_metrics = _related_report_html_metrics(
        data.readiness_summary,
        data.phase_gate_summary,
    )

    def esc(value: object) -> str:
        return html.escape("" if value is None else str(value))

    venue_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(item.get('venue'))}</td>"
            f"<td>{esc(item.get('decision'))}</td>"
            f"<td>{esc(item.get('main_blocker'))}</td>"
            "</tr>"
        )
        for item in data.venue_decisions
        if isinstance(item, dict)
    )
    diag_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(item.symbol)}</td>"
            f"<td>{item.rows}</td>"
            f"<td>{item.market_open_rows}</td>"
            f"<td>{item.tradable_rate:.4f}</td>"
            f"<td>{item.stale_rate:.4f}</td>"
            f"<td>{item.missing_mark_price_rate:.4f}</td>"
            f"<td>{item.missing_index_price_rate:.4f}</td>"
            f"<td>{esc(item.oracle_age_p90_ms)}</td>"
            f"<td>{esc(item.spread_p90_bps)}</td>"
            "</tr>"
        )
        for item in data.quote_diagnostics
    )
    cost_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(row.get('venue'))}</td>"
            f"<td>{esc(row.get('symbol'))}</td>"
            f"<td>{esc(row.get('stale_rate'))}</td>"
            f"<td>{esc(row.get('tradable_rate'))}</td>"
            f"<td>{esc(row.get('spread_p90_bps'))}</td>"
            f"<td>{esc(row.get('holding_cost_4h_bps'))}</td>"
            f"<td>{esc(row.get('notes'))}</td>"
            "</tr>"
        )
        for row in data.cost_rows
    )
    backtest_rows = "\n".join(
        (
            "<tr>"
            f"<td>{esc(row.get('venue'))}</td>"
            f"<td>{esc(row.get('canonical_symbol'))}</td>"
            f"<td>{esc(row.get('trade_count'))}</td>"
            f"<td>{esc(row.get('avg_trade_return'))}</td>"
            f"<td>{esc(row.get('cost_drag_bps'))}</td>"
            f"<td>{esc(row.get('stale_rejected_count'))}</td>"
            f"<td>{esc(row.get('halt_rejected_count'))}</td>"
            "</tr>"
        )
        for row in data.backtest_metrics
    )
    blocker_items = "".join(f"<li>{esc(item)}</li>" for item in data.blockers) or "<li>none</li>"
    next_action_items = (
        "".join(f"<li>{esc(item)}</li>" for item in data.next_actions) or "<li>none</li>"
    )
    validation_items = (
        "".join(
            f"<li>{esc(issue.path)}: {esc(issue.message)}</li>" for issue in data.validation.issues
        )
        or "<li>none</li>"
    )
    log_tail = html.escape("\n".join(data.log_tail))
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Live Evidence Detailed Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1e8;
      --surface: #fffdfa;
      --ink: #1e1b16;
      --muted: #6b6258;
      --line: #d8d0c3;
      --accent: #14532d;
      --warn: #9a3412;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--ink); }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 64px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    section {{ margin-top: 24px; background: var(--surface); border: 1px solid var(--line); padding: 20px; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid var(--line); padding: 12px; background: #fff; }}
    .metric .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric .value {{ margin-top: 6px; font-size: 18px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f9f6ef; }}
    pre {{ margin: 0; overflow: auto; background: #171411; color: #f7f2ea; padding: 16px; }}
    .ok {{ color: var(--accent); }}
    .warn {{ color: var(--warn); }}
    ul {{ margin: 0; padding-left: 20px; }}
  </style>
</head>
<body>
  <main>
    <h1>Live Evidence Detailed Report</h1>
    <section>
      <h2>Status</h2>
      <div class="meta">
        <div class="metric"><div class="label">Run Status</div><div class="value">{esc(data.status)}</div></div>
        <div class="metric"><div class="label">Decision</div><div class="value">{esc(data.decision)}</div></div>
        <div class="metric"><div class="label">Started At UTC</div><div class="value">{esc(data.started_at_utc)}</div></div>
        <div class="metric"><div class="label">Finished At UTC</div><div class="value">{esc(data.finished_at_utc)}</div></div>
      </div>
    </section>
    <section>
      <h2>Audit Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(audit_summary_flat.get("overall_status"))}</div></div>
        <div class="metric"><div class="label">Latest Operation</div><div class="value">{esc(audit_summary_flat.get("latest_operation"))}</div></div>
        <div class="metric"><div class="label">Bundle History Snapshot Count</div><div class="value">{esc(audit_summary_flat.get("bundle_history_snapshot_count"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Phase Gate Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Decision</div><div class="value">{esc(phase_gate_flat.get("phase_gate_decision"))}</div></div>
        <div class="metric"><div class="label">Phase 2 Entry Allowed</div><div class="value">{esc(phase_gate_flat.get("phase2_entry_allowed"))}</div></div>
        <div class="metric"><div class="label">Reason</div><div class="value">{esc(phase_gate_flat.get("phase_gate_reason"))}</div></div>
        <div class="metric"><div class="label">Strict Validation</div><div class="value">{esc(phase_gate_flat.get("strict_validation_passed"))}</div></div>
        <div class="metric"><div class="label">Strict Validation Issues</div><div class="value">{esc(phase_gate_flat.get("phase_gate_strict_validation_issue_count"))}</div></div>
        <div class="metric"><div class="label">Checked Files</div><div class="value">{esc(phase_gate_flat.get("phase_gate_checked_files"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Readiness Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Next Phase Candidate</div><div class="value">{esc(readiness_flat.get("readiness_next_phase_candidate"))}</div></div>
        <div class="metric"><div class="label">Execution Ready</div><div class="value">{esc(readiness_flat.get("readiness_execution_ready"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Current Remediation Queue</h2>
      <div class="meta">
{remediation_metrics}
      </div>
    </section>
    <section>
      <h2>Restart Pointers</h2>
      <div class="meta">
{restart_pointer_metrics}
      </div>
    </section>
    <section>
      <h2>Quick Navigation</h2>
      <div class="meta">
{quick_navigation_metrics}
      </div>
    </section>
    <section>
      <h2>Related Reports</h2>
      <div class="meta">
{related_report_metrics}
      </div>
    </section>
    <section>
      <h2>Latest Execution Lineage</h2>
      <div class="meta">
{_latest_execution_lineage_html_metrics(latest_execution_flat)}
      </div>
    </section>
    <section>
      <h2>Execution Snapshot</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_summary_flat.get("execution_overall_status"))}</div></div>
        <div class="metric"><div class="label">Venue Count</div><div class="value">{esc(execution_summary_flat.get("execution_venue_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_summary_flat.get("execution_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Comparison</h2>
      <div class="meta">
        <div class="metric"><div class="label">All Registries Present</div><div class="value">{esc(execution_comparison_flat.get("execution_comparison_all_registries_present"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_comparison_flat.get("execution_comparison_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Diagnostics</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_diagnostics_flat.get("execution_diagnostics_status"))}</div></div>
        <div class="metric"><div class="label">Balance Gap</div><div class="value">{esc(execution_diagnostics_flat.get("execution_balance_gap_detected"))}</div></div>
        <div class="metric"><div class="label">Fills Gap</div><div class="value">{esc(execution_diagnostics_flat.get("execution_fills_gap_detected"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_diagnostics_flat.get("execution_diagnostics_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Gap History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest Status</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_latest_status"))}</div></div>
        <div class="metric"><div class="label">Latest Diagnostics Status</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_latest_diagnostics_status"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_gap_history_flat.get("execution_gap_history_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution State Comparison History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest Status Match</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_latest_status_match"))}</div></div>
        <div class="metric"><div class="label">Mismatching Count</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_mismatching_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_state_comparison_flat.get("execution_state_comparison_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Snapshot Drift History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_entry_count"))}</div></div>
        <div class="metric"><div class="label">Latest State Match</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_latest_status_match"))}</div></div>
        <div class="metric"><div class="label">Mismatching Snapshot Count</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_mismatching_snapshot_count"))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_snapshot_drift_flat.get("execution_snapshot_drift_report_path"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Drift Overview</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_status"))}</div></div>
        <div class="metric"><div class="label">Diagnostics Alignment</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_diagnostics_alignment_match"))}</div></div>
        <div class="metric"><div class="label">State Comparison Mismatch Count</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_state_comparison_mismatching_count"))}</div></div>
        <div class="metric"><div class="label">Snapshot Drift Mismatch Count</div><div class="value">{esc(execution_drift_flat.get("execution_drift_overview_snapshot_drift_mismatching_snapshot_count"))}</div></div>
      </div>
    </section>
    <section>
      <h2>Artifacts</h2>
      <div class="meta">
        <div class="metric"><div class="label">Sidecar Metadata Rows</div><div class="value">{data.row_counts["sidecar_metadata"]}</div></div>
        <div class="metric"><div class="label">Sidecar Pricing Rows</div><div class="value">{data.row_counts["sidecar_pricing"]}</div></div>
        <div class="metric"><div class="label">Raw Quote Rows</div><div class="value">{data.row_counts["raw_quotes"]}</div></div>
        <div class="metric"><div class="label">Evidence Card</div><div class="value">{esc(data.artifacts.evidence_card)}</div></div>
      </div>
    </section>
    <section>
      <h2>Venue Decisions</h2>
      <table>
        <thead><tr><th>Venue</th><th>Decision</th><th>Main Blocker</th></tr></thead>
        <tbody>{venue_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>GTrade Diagnostics</h2>
      <table>
        <thead><tr><th>Symbol</th><th>Rows</th><th>Open Rows</th><th>Tradable Rate</th><th>Stale Rate</th><th>Missing Mark</th><th>Missing Index</th><th>Oracle p90 ms</th><th>Spread p90 bps</th></tr></thead>
        <tbody>{diag_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Cost Matrix Snapshot</h2>
      <table>
        <thead><tr><th>Venue</th><th>Symbol</th><th>Stale Rate</th><th>Tradable Rate</th><th>Spread p90 bps</th><th>Holding 4h bps</th><th>Notes</th></tr></thead>
        <tbody>{cost_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Backtest Snapshot</h2>
      <table>
        <thead><tr><th>Venue</th><th>Symbol</th><th>Trade Count</th><th>Avg Trade Return</th><th>Cost Drag bps</th><th>Stale Rejected</th><th>Halt Rejected</th></tr></thead>
        <tbody>{backtest_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Validation</h2>
      <p>checked_files={data.validation.checked_files}, issue_count={len(data.validation.issues)}</p>
      <ul>{validation_items}</ul>
    </section>
    <section>
      <h2>Blockers</h2>
      <ul>{blocker_items}</ul>
    </section>
    <section>
      <h2>Next Actions</h2>
      <ul>{next_action_items}</ul>
    </section>
    <section>
      <h2>Log Tail</h2>
      <pre>{log_tail}</pre>
    </section>
  </main>
</body>
</html>
"""


def render_live_evidence_followup(data: LiveEvidenceReportData) -> str:
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = _latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    path_source = (
        data.log_path
        if str(data.log_path) not in {"", "."}
        else (data.manifest_path or data.log_path)
    )
    reports_dir = (
        data.output_path.parent if data.output_path.parent != Path(".") else Path("data/reports")
    )
    quick_navigation = [
        f"- live_evidence_followup_report: `{default_followup_output_path(path_source)}`",
        f"- live_evidence_report: `{data.output_path}`",
        f"- current_state_index_report: `{reports_dir / 'current_state_index.md'}`",
        f"- readiness_snapshot_report: `{reports_dir / 'readiness_snapshot.md'}`",
        f"- phase_gate_review_report: `{phase_gate_flat.get('phase_gate_review_report_path') or (reports_dir / 'phase_gate_review.md')}`",
        f"- remediation_scoreboard_report: `{reports_dir / 'remediation_scoreboard.md'}`",
    ]
    related_reports = [
        f"- live_evidence_followup_report: `{default_followup_output_path(path_source)}`",
        f"- live_evidence_report: `{data.output_path}`",
        f"- operations_dashboard_report: `{reports_dir / 'operations_dashboard.md'}`",
        f"- ops_review_report: `{reports_dir / 'ops_review.md'}`",
        f"- current_state_index_report: `{reports_dir / 'current_state_index.md'}`",
        f"- readiness_snapshot_report: `{reports_dir / 'readiness_snapshot.md'}`",
        f"- phase_gate_review_report: `{phase_gate_flat.get('phase_gate_review_report_path') or (reports_dir / 'phase_gate_review.md')}`",
        f"- paper_operations_runbook_report: `{reports_dir / 'paper_operations_runbook.md'}`",
        "- go_no_go_report: `data/research/go_no_go_report.md`",
        f"- paper_vs_backtest_comparison_report: `{reports_dir / 'paper_vs_backtest_comparison.md'}`",
    ]
    lines = [
        "# Live Evidence Follow-up",
        "",
        "## Current State",
        "",
        f"- run_status: `{data.status}`",
        f"- decision: `{data.decision}`",
        f"- markdown_report: `{data.output_path}`",
        f"- html_report: `{default_html_output_path(path_source)}`",
        f"- manifest_path: `{data.manifest_path}`",
        "",
        "## Quick Navigation",
        "",
        *quick_navigation,
        "",
        "## Related Reports",
        "",
        *related_reports,
        "",
        "## Audit Summary",
        "",
        f"- overall_status: `{audit_summary_flat.get('overall_status')}`",
        f"- latest_operation: `{audit_summary_flat.get('latest_operation')}`",
        (
            "- bundle_history_snapshot_count: "
            f"`{audit_summary_flat.get('bundle_history_snapshot_count')}`"
        ),
        "",
        "## Phase Gate Summary",
        "",
        f"- decision: `{phase_gate_flat.get('phase_gate_decision')}`",
        f"- phase2_entry_allowed: `{phase_gate_flat.get('phase2_entry_allowed')}`",
        f"- phase_gate_reason: `{phase_gate_flat.get('phase_gate_reason')}`",
        f"- strict_validation_passed: `{phase_gate_flat.get('strict_validation_passed')}`",
        (
            "- phase_gate_strict_validation_issue_count: "
            f"`{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}`"
        ),
        f"- phase_gate_checked_files: `{phase_gate_flat.get('phase_gate_checked_files')}`",
        "",
        "## Readiness Summary",
        "",
        f"- next_phase_candidate: `{readiness_flat.get('readiness_next_phase_candidate')}`",
        f"- execution_ready: `{readiness_flat.get('readiness_execution_ready')}`",
        "",
        "## Latest Execution Lineage",
        "",
        *_latest_execution_lineage_markdown_lines(latest_execution_flat),
        "",
        "## Execution Snapshot",
        "",
        f"- overall_status: `{execution_summary_flat.get('execution_overall_status')}`",
        f"- venue_count: `{execution_summary_flat.get('execution_venue_count')}`",
        f"- report_path: `{execution_summary_flat.get('execution_report_path')}`",
        "",
        "## Execution Venue Comparison",
        "",
        f"- all_registries_present: `{execution_comparison_flat.get('execution_comparison_all_registries_present')}`",
        f"- report_path: `{execution_comparison_flat.get('execution_comparison_report_path')}`",
        "",
        "## Execution Venue Diagnostics",
        "",
        f"- overall_status: `{execution_diagnostics_flat.get('execution_diagnostics_status')}`",
        f"- balance_gap_detected: `{execution_diagnostics_flat.get('execution_balance_gap_detected')}`",
        f"- fills_gap_detected: `{execution_diagnostics_flat.get('execution_fills_gap_detected')}`",
        f"- report_path: `{execution_diagnostics_flat.get('execution_diagnostics_report_path')}`",
        "",
        "## Execution Gap History",
        "",
        f"- entry_count: `{execution_gap_history_flat.get('execution_gap_history_entry_count')}`",
        f"- latest_status: `{execution_gap_history_flat.get('execution_gap_history_latest_status')}`",
        f"- latest_execution_diagnostics_status: `{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status')}`",
        f"- report_path: `{execution_gap_history_flat.get('execution_gap_history_report_path')}`",
        "",
        "## Execution State Comparison History",
        "",
        f"- entry_count: `{execution_state_comparison_flat.get('execution_state_comparison_entry_count')}`",
        f"- latest_status_match: `{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}`",
        f"- mismatching_count: `{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}`",
        f"- report_path: `{execution_state_comparison_flat.get('execution_state_comparison_report_path')}`",
        "",
        "## Execution Snapshot Drift History",
        "",
        f"- entry_count: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}`",
        f"- latest_execution_state_comparison_status_match: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}`",
        f"- mismatching_snapshot_count: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}`",
        f"- report_path: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path')}`",
        "",
        "## Execution Drift Overview",
        "",
        f"- overall_status: `{execution_drift_flat.get('execution_drift_overview_status')}`",
        f"- diagnostics_alignment_match: `{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}`",
        f"- state_comparison_mismatching_count: `{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}`",
        f"- snapshot_drift_mismatching_snapshot_count: `{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}`",
        "",
        "## Immediate Next Work",
        "",
    ]
    if data.status == "running":
        lines.append(
            "- collection is still running; wait for terminal status before touching downstream artifacts"
        )
    elif data.status in {"failed", "failed_preflight", "failed_collection"}:
        lines.append(
            "- inspect the failure point in the log tail and fix the first blocking error before rerunning"
        )
    elif data.status == "partial_failed":
        lines.append(
            "- inspect the failed step and rerun after fixing the recorded blocker; raw data and diagnostics are already available"
        )
    elif data.status == "completed_with_retries":
        lines.append(
            "- review the retried steps and remove the underlying instability before the next live run"
        )
    elif data.next_actions:
        lines.extend(f"- {item}" for item in data.next_actions)
    else:
        lines.append("- no blocking follow-up was emitted by the report")
    lines.extend(
        [
            "",
            "## Log Tail",
            "",
            "```text",
            *data.log_tail,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def default_markdown_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.md"


def default_html_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.html"


def default_followup_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_followup_{stem}.md"
