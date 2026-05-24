from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
)
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.storage.jsonl_store import read_json, write_json
from sis.validation.artifacts import validate_artifacts


PHASE2_ALLOWED_DECISIONS = {"GO", "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"}


def _latest_path(pattern_root: Path, glob_pattern: str) -> Path | None:
    paths = sorted(pattern_root.glob(glob_pattern))
    return paths[-1] if paths else None


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_stale_thresholds() -> dict[str, int]:
    try:
        from sis.risk.halt_policy import load_halt_policy

        policy = load_halt_policy()
        stale_policy = policy.get("halt_policy", policy).get("stale_price", {})
    except FileNotFoundError:
        stale_policy = {}
    return {
        "gtrade": int(stale_policy.get("gtrade_max_age_ms", 3000)),
        "ostium": int(stale_policy.get("ostium_max_age_ms", 5000)),
    }


def build_phase_gate_review(
    data_dir: Path,
    *,
    schema_root: Path,
    diagnostics_symbols: tuple[str, ...] = ("QQQ", "SPY", "XAU"),
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    validation = validate_artifacts(data_dir, schema_root, strict=True)
    stale_thresholds = _load_stale_thresholds()

    diagnostics: list[dict] = []
    for symbol in diagnostics_symbols:
        items = build_quote_diagnostics(
            data_dir / "raw/quotes",
            venue="gtrade",
            symbol=symbol,
            stale_thresholds_ms=stale_thresholds,
        )
        diagnostics.append(
            {
                "symbol": symbol,
                "available": bool(items),
                "items": [item.__dict__.copy() for item in items],
            }
        )

    manifest_path = _latest_path(Path("logs/live_evidence/manifests"), "live_evidence_*.json")
    manifest_payload = _safe_read_json(manifest_path)
    evidence_card_path = _latest_path(data_dir / "evidence", "evidence_card_*.json")
    evidence_payload = _safe_read_json(evidence_card_path)
    execution_summary = _safe_read_json(execution_snapshot_summary_path)
    execution_comparison = _safe_read_json(execution_venue_comparison_summary_path)
    execution_diagnostics = _safe_read_json(execution_venue_diagnostics_summary_path)
    execution_gap_history = _safe_read_json(execution_gap_history_summary_path)
    execution_state_comparison = _safe_read_json(execution_state_comparison_history_summary_path)
    execution_snapshot_drift = _safe_read_json(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = normalize_execution_drift_overview_summary(
        _safe_read_json(execution_drift_overview_summary_path)
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)

    decision = evidence_payload.get("decision") or manifest_payload.get("decision")
    venue_decisions = evidence_payload.get("venue_decisions")
    blockers = evidence_payload.get("blockers")
    next_actions = evidence_payload.get("next_actions")

    strict_validation_passed = len(validation.issues) == 0
    diagnostics_all_available = all(item["available"] for item in diagnostics)
    phase2_entry_allowed = bool(
        strict_validation_passed
        and diagnostics_all_available
        and isinstance(decision, str)
        and decision in PHASE2_ALLOWED_DECISIONS
    )

    summary = {
        "current_phase": "Phase 1",
        "strict_validation_passed": strict_validation_passed,
        "strict_validation_issue_count": len(validation.issues),
        "phase_gate_strict_validation_issue_count": len(validation.issues),
        "checked_files": validation.checked_files,
        "phase_gate_checked_files": validation.checked_files,
        "strict_validation_issues": [
            {"path": issue.path, "message": issue.message} for issue in validation.issues
        ],
        "phase_gate_strict_validation_issues": [
            {"path": issue.path, "message": issue.message} for issue in validation.issues
        ],
        "phase_gate_review_report_path": str(out_path) if out_path is not None else None,
        "latest_manifest_path": str(manifest_path) if manifest_path is not None else None,
        "latest_manifest_status": manifest_payload.get("status"),
        "latest_manifest_decision": manifest_payload.get("decision"),
        "latest_evidence_card_path": str(evidence_card_path) if evidence_card_path is not None else None,
        "latest_execution_snapshot_summary_path": (
            str(execution_snapshot_summary_path)
            if execution_snapshot_summary_path is not None
            else None
        ),
        "latest_execution_venue_comparison_summary_path": (
            str(execution_venue_comparison_summary_path)
            if execution_venue_comparison_summary_path is not None
            else None
        ),
        "latest_execution_venue_diagnostics_summary_path": (
            str(execution_venue_diagnostics_summary_path)
            if execution_venue_diagnostics_summary_path is not None
            else None
        ),
        "latest_execution_gap_history_summary_path": (
            str(execution_gap_history_summary_path) if execution_gap_history_summary_path is not None else None
        ),
        "latest_execution_state_comparison_history_summary_path": (
            str(execution_state_comparison_history_summary_path)
            if execution_state_comparison_history_summary_path is not None
            else None
        ),
        "latest_execution_snapshot_drift_history_summary_path": (
            str(execution_snapshot_drift_history_summary_path)
            if execution_snapshot_drift_history_summary_path is not None
            else None
        ),
        "latest_execution_drift_overview_summary_path": (
            str(execution_drift_overview_summary_path)
            if execution_drift_overview_summary_path is not None
            else None
        ),
        "decision": decision,
        "phase_gate_decision": decision,
        "venue_decisions": venue_decisions if isinstance(venue_decisions, list) else [],
        "blockers": blockers if isinstance(blockers, list) else [],
        "next_actions": next_actions if isinstance(next_actions, list) else [],
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        "diagnostics_symbols": list(diagnostics_symbols),
        "diagnostics_all_available": diagnostics_all_available,
        "diagnostics": diagnostics,
        "phase2_entry_allowed": phase2_entry_allowed,
        "phase2_entry_reason": (
            "decision_cleared_and_phase1_gate_complete"
            if phase2_entry_allowed
            else "remain_in_phase1_until_live_evidence_gate_clears"
        ),
        "phase_gate_reason": (
            "decision_cleared_and_phase1_gate_complete"
            if phase2_entry_allowed
            else "remain_in_phase1_until_live_evidence_gate_clears"
        ),
        "phase_gate_strict_validation_passed": strict_validation_passed,
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/phase_gate_review_summary.json",
            "data/reports/phase_gate_review.md",
            "data/research/go_no_go_report.md",
            "data/evidence/evidence_card_*.json",
        ],
    }

    lines = [
        "# Phase Gate Review",
        "",
        "## Executive Summary",
        "",
        f"- current_phase: {summary['current_phase']}",
        f"- decision: {summary['decision']}",
        f"- strict_validation_passed: {summary['strict_validation_passed']}",
        f"- strict_validation_issue_count: {summary['strict_validation_issue_count']}",
        f"- latest_manifest_status: {summary['latest_manifest_status']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase2_entry_reason: {summary['phase2_entry_reason']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}",
        f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
        f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
        f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
        f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}",
        f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}",
        (
            "- execution_state_comparison_latest_status_match: "
            f"{summary['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{summary['execution_state_comparison_mismatching_count']}"
        ),
        f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}",
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{summary['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}",
        (
            "- execution_drift_overview_diagnostics_alignment_match: "
            f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- execution_drift_overview_state_comparison_mismatching_count: "
            f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        "",
        "## Latest Artifacts",
        "",
        f"- latest_manifest_path: {summary['latest_manifest_path']}",
        f"- latest_evidence_card_path: {summary['latest_evidence_card_path']}",
        f"- latest_execution_snapshot_summary_path: {summary['latest_execution_snapshot_summary_path']}",
        f"- latest_execution_venue_comparison_summary_path: {summary['latest_execution_venue_comparison_summary_path']}",
        f"- latest_execution_venue_diagnostics_summary_path: {summary['latest_execution_venue_diagnostics_summary_path']}",
        f"- latest_execution_gap_history_summary_path: {summary['latest_execution_gap_history_summary_path']}",
        f"- latest_execution_state_comparison_history_summary_path: {summary['latest_execution_state_comparison_history_summary_path']}",
        f"- latest_execution_snapshot_drift_history_summary_path: {summary['latest_execution_snapshot_drift_history_summary_path']}",
        f"- latest_execution_drift_overview_summary_path: {summary['latest_execution_drift_overview_summary_path']}",
        "",
        "## Strict Validation",
        "",
        f"- checked_files: {summary['checked_files']}",
    ]
    if validation.issues:
        lines.append("")
        lines.append("| path | message |")
        lines.append("| --- | --- |")
        for issue in validation.issues:
            lines.append(f"| {issue.path} | {issue.message.replace('|', '/')} |")
    else:
        lines.extend(["", "- issues: none"])

    lines.extend(["", "## Diagnostics", ""])
    lines.append("| symbol | available | rows | tradable_rate | stale_rate | missing_mark_price_rate | missing_index_price_rate | spread_p90_bps |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in diagnostics:
        diagnostic = item["items"][0] if item["items"] else {}
        lines.append(
            "| {symbol} | {available} | {rows} | {tradable_rate} | {stale_rate} | {missing_mark} | {missing_index} | {spread_p90} |".format(
                symbol=item["symbol"],
                available=item["available"],
                rows=diagnostic.get("rows", ""),
                tradable_rate=diagnostic.get("tradable_rate", ""),
                stale_rate=diagnostic.get("stale_rate", ""),
                missing_mark=diagnostic.get("missing_mark_price_rate", ""),
                missing_index=diagnostic.get("missing_index_price_rate", ""),
                spread_p90=diagnostic.get("spread_p90_bps", ""),
            )
        )

    lines.extend(["", "## Venue Decisions", ""])
    if summary["venue_decisions"]:
        lines.append("| venue | decision | main_blocker |")
        lines.append("| --- | --- | --- |")
        for item in summary["venue_decisions"]:
            lines.append(
                f"| {item.get('venue', '')} | {item.get('decision', '')} | {item.get('main_blocker', '') or ''} |"
            )
    else:
        lines.append("- venue_decisions: unavailable")

    lines.extend(["", "## Execution Snapshot", ""])
    lines.append(f"- execution_overall_status: {summary['execution_overall_status']}")
    lines.append(f"- execution_venue_count: {summary['execution_venue_count']}")
    lines.append(f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}")
    lines.append(f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}")
    lines.append(f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}")
    lines.append(f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}")
    lines.append(f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}")
    lines.append(f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}")
    lines.append(
        f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}"
    )
    lines.append(f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}")
    lines.append(
        f"- execution_state_comparison_latest_status_match: {summary['execution_state_comparison_latest_status_match']}"
    )
    lines.append(
        f"- execution_state_comparison_mismatching_count: {summary['execution_state_comparison_mismatching_count']}"
    )
    lines.append(f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}")
    lines.append(
        f"- execution_snapshot_drift_latest_status_match: {summary['execution_snapshot_drift_latest_status_match']}"
    )
    lines.append(
        f"- execution_snapshot_drift_mismatching_snapshot_count: {summary['execution_snapshot_drift_mismatching_snapshot_count']}"
    )
    lines.append(f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}")
    lines.append(
        f"- execution_drift_overview_diagnostics_alignment_match: {summary['execution_drift_overview_diagnostics_alignment_match']}"
    )
    lines.append(
        f"- execution_drift_overview_state_comparison_mismatching_count: {summary['execution_drift_overview_state_comparison_mismatching_count']}"
    )
    lines.append(
        f"- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: {summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
    )
    lines.append(f"- latest_execution_snapshot_summary_path: {summary['latest_execution_snapshot_summary_path']}")
    lines.append(f"- latest_execution_venue_comparison_summary_path: {summary['latest_execution_venue_comparison_summary_path']}")
    lines.append(f"- latest_execution_venue_diagnostics_summary_path: {summary['latest_execution_venue_diagnostics_summary_path']}")
    lines.append(f"- latest_execution_gap_history_summary_path: {summary['latest_execution_gap_history_summary_path']}")
    lines.append(
        f"- latest_execution_state_comparison_history_summary_path: {summary['latest_execution_state_comparison_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_snapshot_drift_history_summary_path: {summary['latest_execution_snapshot_drift_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_drift_overview_summary_path: {summary['latest_execution_drift_overview_summary_path']}"
    )

    lines.extend(["", "## Next Actions", ""])
    if summary["next_actions"]:
        lines.extend(f"- {item}" for item in summary["next_actions"])
    else:
        lines.extend(
            [
                "- recollect live evidence during the recommended window",
                "- rerun diagnose-quotes for QQQ / SPY / XAU",
                "- rerun validate-artifacts --strict",
                "- rerun check-go-no-go and build-evidence-card",
            ]
        )

    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    text = "\n".join(lines) + "\n"

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
