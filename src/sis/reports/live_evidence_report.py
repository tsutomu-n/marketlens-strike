from __future__ import annotations

import csv
import html
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.reports.quote_diagnostics import QuoteDiagnostic, build_quote_diagnostics
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    phase_gate_flat_fields,
)
from sis.storage.jsonl_store import read_json
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
    if manifest_path is None or not manifest_path.exists():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = payload.get("status")
    if isinstance(status, str):
        return status
    return None


def load_manifest_payload(manifest_path: Path | None) -> dict[str, Any]:
    if manifest_path is None or not manifest_path.exists():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


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
    if not path.exists():
        return []
    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


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
    artifact_paths = manifest.get("artifacts", {}) if isinstance(manifest.get("artifacts"), dict) else {}
    today_utc = datetime.now(timezone.utc).date().isoformat()
    evidence_card_path = artifact_paths.get("evidence_card")
    evidence_card = Path(evidence_card_path) if isinstance(evidence_card_path, str) and evidence_card_path else _latest_evidence_card(data_dir)
    artifacts = LiveEvidenceArtifacts(
        sidecar_metadata=Path(artifact_paths.get("sidecar_metadata", data_dir / f"raw/sidecar/gtrade/{today_utc}.jsonl")),
        sidecar_pricing=Path(artifact_paths.get("sidecar_pricing", data_dir / f"raw/sidecar/gtrade-pricing/{today_utc}.jsonl")),
        raw_quotes=Path(artifact_paths.get("raw_quotes", data_dir / f"raw/quotes/gtrade/{today_utc}.jsonl")),
        normalized_quotes=Path(artifact_paths.get("normalized_quotes", data_dir / "normalized/quotes.parquet")),
        cost_matrix=Path(artifact_paths.get("cost_matrix", data_dir / "research/venue_cost_matrix.csv")),
        backtest_metrics=Path(artifact_paths.get("backtest_metrics", data_dir / "research/backtest_metrics.json")),
        go_no_go_report=Path(artifact_paths.get("go_no_go_report", data_dir / "research/go_no_go_report.md")),
        evidence_card=evidence_card,
    )
    manifest_status = parse_manifest_status(manifest_path)
    resolved_status = status or manifest_status or (parse_run_status(log_path) if log_path is not None else "running")
    evidence_payload = read_json(evidence_card) if evidence_card and evidence_card.exists() else {}
    venue_decisions = evidence_payload.get("venue_decisions", []) if isinstance(evidence_payload, dict) else []
    blockers = manifest.get("blockers", []) if isinstance(manifest.get("blockers"), list) else []
    next_actions = manifest.get("next_actions", []) if isinstance(manifest.get("next_actions"), list) else []
    phase_gate_summary = manifest.get("phase_gate_summary", {}) if isinstance(manifest.get("phase_gate_summary"), dict) else {}
    execution_summary = manifest.get("execution_summary", {}) if isinstance(manifest.get("execution_summary"), dict) else {}
    execution_comparison_summary = (
        manifest.get("execution_comparison_summary", {})
        if isinstance(manifest.get("execution_comparison_summary"), dict)
        else {}
    )
    execution_diagnostics_summary = (
        manifest.get("execution_diagnostics_summary", {})
        if isinstance(manifest.get("execution_diagnostics_summary"), dict)
        else {}
    )
    execution_gap_history_summary = (
        manifest.get("execution_gap_history_summary", {})
        if isinstance(manifest.get("execution_gap_history_summary"), dict)
        else {}
    )
    execution_state_comparison_summary = (
        manifest.get("execution_state_comparison_summary", {})
        if isinstance(manifest.get("execution_state_comparison_summary"), dict)
        else {}
    )
    execution_snapshot_drift_summary = (
        manifest.get("execution_snapshot_drift_summary", {})
        if isinstance(manifest.get("execution_snapshot_drift_summary"), dict)
        else {}
    )
    execution_drift_overview_summary = (
        manifest.get("execution_drift_overview_summary", {})
        if isinstance(manifest.get("execution_drift_overview_summary"), dict)
        else {}
    )
    if not blockers and isinstance(evidence_payload, dict):
        blockers = evidence_payload.get("blockers", [])
    if not next_actions and isinstance(evidence_payload, dict):
        next_actions = evidence_payload.get("next_actions", [])
    if not phase_gate_summary and isinstance(evidence_payload, dict):
        payload_phase_gate = evidence_payload.get("phase_gate_summary")
        if isinstance(payload_phase_gate, dict):
            phase_gate_summary = payload_phase_gate
    if not execution_summary and isinstance(evidence_payload, dict):
        payload_execution = evidence_payload.get("execution_summary")
        if isinstance(payload_execution, dict):
            execution_summary = payload_execution
    if not execution_comparison_summary and isinstance(evidence_payload, dict):
        payload_execution_comparison = evidence_payload.get("execution_comparison_summary")
        if isinstance(payload_execution_comparison, dict):
            execution_comparison_summary = payload_execution_comparison
    if not execution_diagnostics_summary and isinstance(evidence_payload, dict):
        payload_execution_diagnostics = evidence_payload.get("execution_diagnostics_summary")
        if isinstance(payload_execution_diagnostics, dict):
            execution_diagnostics_summary = payload_execution_diagnostics
    if not execution_gap_history_summary and isinstance(evidence_payload, dict):
        payload_execution_gap_history = evidence_payload.get("execution_gap_history_summary")
        if isinstance(payload_execution_gap_history, dict):
            execution_gap_history_summary = payload_execution_gap_history
    if not execution_state_comparison_summary and isinstance(evidence_payload, dict):
        payload_execution_state_comparison = evidence_payload.get("execution_state_comparison_summary")
        if isinstance(payload_execution_state_comparison, dict):
            execution_state_comparison_summary = payload_execution_state_comparison
    if not execution_snapshot_drift_summary and isinstance(evidence_payload, dict):
        payload_execution_snapshot_drift = evidence_payload.get("execution_snapshot_drift_summary")
        if isinstance(payload_execution_snapshot_drift, dict):
            execution_snapshot_drift_summary = payload_execution_snapshot_drift
    if not execution_drift_overview_summary and isinstance(evidence_payload, dict):
        payload_execution_drift_overview = evidence_payload.get("execution_drift_overview_summary")
        if isinstance(payload_execution_drift_overview, dict):
            execution_drift_overview_summary = payload_execution_drift_overview
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
    log_lines = log_path.read_text(encoding="utf-8").splitlines() if log_path is not None and log_path.exists() else []
    started_at_utc, finished_at_utc = _started_finished(log_lines)
    started_at_utc = manifest.get("started_at_utc") or started_at_utc
    finished_at_utc = manifest.get("finished_at_utc") or finished_at_utc
    manifest_row_counts = manifest.get("row_counts", {}) if isinstance(manifest.get("row_counts"), dict) else {}
    row_counts = {
        "sidecar_metadata": int(manifest_row_counts.get("sidecar_metadata", _count_jsonl_rows(artifacts.sidecar_metadata))),
        "sidecar_pricing": int(manifest_row_counts.get("sidecar_pricing", _count_jsonl_rows(artifacts.sidecar_pricing))),
        "raw_quotes": int(manifest_row_counts.get("raw_quotes", _count_jsonl_rows(artifacts.raw_quotes))),
    }
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
        execution_summary=execution_summary if isinstance(execution_summary, dict) else {},
        execution_comparison_summary=(
            execution_comparison_summary if isinstance(execution_comparison_summary, dict) else {}
        ),
        execution_diagnostics_summary=(
            execution_diagnostics_summary if isinstance(execution_diagnostics_summary, dict) else {}
        ),
        execution_gap_history_summary=(
            execution_gap_history_summary if isinstance(execution_gap_history_summary, dict) else {}
        ),
        execution_state_comparison_summary=(
            execution_state_comparison_summary if isinstance(execution_state_comparison_summary, dict) else {}
        ),
        execution_snapshot_drift_summary=(
            execution_snapshot_drift_summary if isinstance(execution_snapshot_drift_summary, dict) else {}
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
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(data.execution_diagnostics_summary)
    execution_gap_history_flat = execution_gap_history_flat_fields(data.execution_gap_history_summary)
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(data.execution_drift_overview_summary)
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
        lines.append(f"- strict_validation_passed: `{phase_gate_flat.get('strict_validation_passed')}`")
        lines.append(
            "- phase_gate_strict_validation_issue_count: "
            f"`{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}`"
        )
        lines.append(
            f"- phase_gate_checked_files: `{phase_gate_flat.get('phase_gate_checked_files')}`"
        )
        lines.append("")
    if data.execution_summary:
        lines.append("## Execution Snapshot")
        lines.append("")
        lines.append(f"- overall_status: `{execution_summary_flat.get('execution_overall_status')}`")
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
        lines.append(f"- overall_status: `{execution_diagnostics_flat.get('execution_diagnostics_status')}`")
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
        lines.append(f"- overall_status: `{execution_drift_flat.get('execution_drift_overview_status')}`")
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
    lines.append("| Venue | Symbol | Stale Rate | Tradable Rate | Spread p90 bps | Holding 4h bps | Notes |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in data.cost_rows:
        lines.append(
            f"| {row.get('venue', '')} | {row.get('symbol', '')} | {row.get('stale_rate', '')} | "
            f"{row.get('tradable_rate', '')} | {row.get('spread_p90_bps', '')} | {row.get('holding_cost_4h_bps', '')} | {row.get('notes', '')} |"
        )
    lines.append("")
    lines.append("## Backtest Snapshot")
    lines.append("")
    lines.append("| Venue | Symbol | Trade Count | Avg Trade Return | Cost Drag bps | Stale Rejected | Halt Rejected |")
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
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(data.execution_diagnostics_summary)
    execution_gap_history_flat = execution_gap_history_flat_fields(data.execution_gap_history_summary)
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(data.execution_drift_overview_summary)
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
    next_action_items = "".join(f"<li>{esc(item)}</li>" for item in data.next_actions) or "<li>none</li>"
    validation_items = "".join(
        f"<li>{esc(issue.path)}: {esc(issue.message)}</li>" for issue in data.validation.issues
    ) or "<li>none</li>"
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
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(audit_summary_flat.get('overall_status'))}</div></div>
        <div class="metric"><div class="label">Latest Operation</div><div class="value">{esc(audit_summary_flat.get('latest_operation'))}</div></div>
        <div class="metric"><div class="label">Bundle History Snapshot Count</div><div class="value">{esc(audit_summary_flat.get('bundle_history_snapshot_count'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Phase Gate Summary</h2>
      <div class="meta">
        <div class="metric"><div class="label">Decision</div><div class="value">{esc(phase_gate_flat.get('phase_gate_decision'))}</div></div>
        <div class="metric"><div class="label">Phase 2 Entry Allowed</div><div class="value">{esc(phase_gate_flat.get('phase2_entry_allowed'))}</div></div>
        <div class="metric"><div class="label">Reason</div><div class="value">{esc(phase_gate_flat.get('phase_gate_reason'))}</div></div>
        <div class="metric"><div class="label">Strict Validation</div><div class="value">{esc(phase_gate_flat.get('strict_validation_passed'))}</div></div>
        <div class="metric"><div class="label">Strict Validation Issues</div><div class="value">{esc(phase_gate_flat.get('phase_gate_strict_validation_issue_count'))}</div></div>
        <div class="metric"><div class="label">Checked Files</div><div class="value">{esc(phase_gate_flat.get('phase_gate_checked_files'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Snapshot</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_summary_flat.get('execution_overall_status'))}</div></div>
        <div class="metric"><div class="label">Venue Count</div><div class="value">{esc(execution_summary_flat.get('execution_venue_count'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_summary_flat.get('execution_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Comparison</h2>
      <div class="meta">
        <div class="metric"><div class="label">All Registries Present</div><div class="value">{esc(execution_comparison_flat.get('execution_comparison_all_registries_present'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_comparison_flat.get('execution_comparison_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Venue Diagnostics</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_diagnostics_flat.get('execution_diagnostics_status'))}</div></div>
        <div class="metric"><div class="label">Balance Gap</div><div class="value">{esc(execution_diagnostics_flat.get('execution_balance_gap_detected'))}</div></div>
        <div class="metric"><div class="label">Fills Gap</div><div class="value">{esc(execution_diagnostics_flat.get('execution_fills_gap_detected'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_diagnostics_flat.get('execution_diagnostics_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Gap History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_gap_history_flat.get('execution_gap_history_entry_count'))}</div></div>
        <div class="metric"><div class="label">Latest Status</div><div class="value">{esc(execution_gap_history_flat.get('execution_gap_history_latest_status'))}</div></div>
        <div class="metric"><div class="label">Latest Diagnostics Status</div><div class="value">{esc(execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_gap_history_flat.get('execution_gap_history_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution State Comparison History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_state_comparison_flat.get('execution_state_comparison_entry_count'))}</div></div>
        <div class="metric"><div class="label">Latest Status Match</div><div class="value">{esc(execution_state_comparison_flat.get('execution_state_comparison_latest_status_match'))}</div></div>
        <div class="metric"><div class="label">Mismatching Count</div><div class="value">{esc(execution_state_comparison_flat.get('execution_state_comparison_mismatching_count'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_state_comparison_flat.get('execution_state_comparison_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Snapshot Drift History</h2>
      <div class="meta">
        <div class="metric"><div class="label">Entry Count</div><div class="value">{esc(execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count'))}</div></div>
        <div class="metric"><div class="label">Latest State Match</div><div class="value">{esc(execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match'))}</div></div>
        <div class="metric"><div class="label">Mismatching Snapshot Count</div><div class="value">{esc(execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count'))}</div></div>
        <div class="metric"><div class="label">Report Path</div><div class="value">{esc(execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Execution Drift Overview</h2>
      <div class="meta">
        <div class="metric"><div class="label">Overall Status</div><div class="value">{esc(execution_drift_flat.get('execution_drift_overview_status'))}</div></div>
        <div class="metric"><div class="label">Diagnostics Alignment</div><div class="value">{esc(execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match'))}</div></div>
        <div class="metric"><div class="label">State Comparison Mismatch Count</div><div class="value">{esc(execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count'))}</div></div>
        <div class="metric"><div class="label">Snapshot Drift Mismatch Count</div><div class="value">{esc(execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count'))}</div></div>
      </div>
    </section>
    <section>
      <h2>Artifacts</h2>
      <div class="meta">
        <div class="metric"><div class="label">Sidecar Metadata Rows</div><div class="value">{data.row_counts['sidecar_metadata']}</div></div>
        <div class="metric"><div class="label">Sidecar Pricing Rows</div><div class="value">{data.row_counts['sidecar_pricing']}</div></div>
        <div class="metric"><div class="label">Raw Quote Rows</div><div class="value">{data.row_counts['raw_quotes']}</div></div>
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
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(data.execution_diagnostics_summary)
    execution_gap_history_flat = execution_gap_history_flat_fields(data.execution_gap_history_summary)
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(data.execution_drift_overview_summary)
    path_source = data.log_path if str(data.log_path) not in {"", "."} else (data.manifest_path or data.log_path)
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
        lines.append("- collection is still running; wait for terminal status before touching downstream artifacts")
    elif data.status in {"failed", "failed_preflight", "failed_collection"}:
        lines.append("- inspect the failure point in the log tail and fix the first blocking error before rerunning")
    elif data.status == "partial_failed":
        lines.append("- inspect the failed step and rerun after fixing the recorded blocker; raw data and diagnostics are already available")
    elif data.status == "completed_with_retries":
        lines.append("- review the retried steps and remove the underlying instability before the next live run")
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
