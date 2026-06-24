from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.reports import live_evidence_html as _live_evidence_html
from sis.reports import live_evidence_followup as _live_evidence_followup
from sis.reports import live_evidence_markdown_sections as _live_evidence_markdown_sections
from sis.reports import live_evidence_report_inputs as _live_evidence_inputs
from sis.reports import live_evidence_report_tables as _live_evidence_report_tables
from sis.reports.quote_diagnostics import QuoteDiagnostic, build_quote_diagnostics
from sis.reports.summary_normalizers import (
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
)
from sis.validation.artifacts import ValidationSummary, validate_artifacts

RunStatus = _live_evidence_inputs.RunStatus

default_followup_output_path = _live_evidence_followup.default_followup_output_path
default_html_output_path = _live_evidence_followup.default_html_output_path
render_live_evidence_followup = _live_evidence_followup.render_live_evidence_followup
render_live_evidence_html = _live_evidence_html.render_live_evidence_html
summary_markdown_lines = _live_evidence_markdown_sections.summary_markdown_lines
detail_markdown_lines = _live_evidence_report_tables.detail_markdown_lines
parse_run_status = _live_evidence_inputs.parse_run_status
parse_manifest_status = _live_evidence_inputs.parse_manifest_status
load_manifest_payload = _live_evidence_inputs.load_manifest_payload
_summary_from_payload = _live_evidence_inputs.summary_from_payload
_summary_from_manifest_or_evidence = _live_evidence_inputs.summary_from_manifest_or_evidence
_extract_timestamp = _live_evidence_inputs.extract_timestamp
_latest_evidence_card = _live_evidence_inputs.latest_evidence_card
_count_jsonl_rows = _live_evidence_inputs.count_jsonl_rows
_load_cost_rows = _live_evidence_inputs.load_cost_rows
_load_backtest_metrics = _live_evidence_inputs.load_backtest_metrics
_started_finished = _live_evidence_inputs.started_finished
default_markdown_output_path = _live_evidence_inputs.default_markdown_output_path


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
    lines = summary_markdown_lines(data)
    lines.extend(detail_markdown_lines(data))
    return "\n".join(lines)
