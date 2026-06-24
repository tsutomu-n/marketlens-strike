from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.doc_paths import recommended_read_order
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports import phase_gate_diagnostics
from sis.reports import phase_gate_review_paths
from sis.reports.phase_gate_remediation import (
    artifact_recovery_commands as _artifact_recovery_commands,
    execution_drift_classifications as _execution_drift_classifications,
    remediation_execute_expected_outputs as _remediation_execute_expected_outputs,
    remediation_order as _remediation_order,
    remediation_postcheck_commands as _remediation_postcheck_commands,
    remediation_postcheck_pass_signals as _remediation_postcheck_pass_signals,
    remediation_preflight_commands as _remediation_preflight_commands,
    remediation_preflight_expected_outputs as _remediation_preflight_expected_outputs,
    remediation_signal_snapshot_before as _remediation_signal_snapshot_before,
    remediation_signal_snapshot_target as _remediation_signal_snapshot_target,
    remediation_success_criteria as _remediation_success_criteria,
)
from sis.reports.phase_gate_review_markdown import render_phase_gate_review_markdown
from sis.reports.summary_normalizers import (
    compare_signal_snapshots,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    latest_execution_lineage_fields_from_summary,
    recommend_remediation_actions,
    signal_observed_sources_by_reason,
    signal_source_confidence,
)
from sis.reports.quote_diagnostics import build_quote_diagnostics
from sis.storage.jsonl_store import write_json
from sis.validation.artifacts import validate_artifacts


PHASE2_ALLOWED_DECISIONS = {
    "GO",
    "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST",
    "READ_ONLY_GO",
    "PAPER_GO",
    "CONDITIONAL_INDEX_ONLY",
}

_load_stale_thresholds = phase_gate_diagnostics.load_stale_thresholds
_load_spread_thresholds = phase_gate_diagnostics.load_spread_thresholds
_spread_threshold_for_symbol = phase_gate_diagnostics.spread_threshold_for_symbol
_trade_xyz_diagnostic_healthy = phase_gate_diagnostics.trade_xyz_diagnostic_healthy
_trade_xyz_diagnostic_blockers = phase_gate_diagnostics.trade_xyz_diagnostic_blockers
_reports_dir = phase_gate_review_paths.reports_dir
_quick_navigation = phase_gate_review_paths.quick_navigation
_related_reports = phase_gate_review_paths.related_reports
_latest_path = phase_gate_review_paths.latest_path
_read_only_collector_gate = phase_gate_review_paths.read_only_collector_gate
_required_artifact_paths = phase_gate_review_paths.required_artifact_paths


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def build_phase_gate_review(
    data_dir: Path,
    *,
    schema_root: Path,
    diagnostics_symbols: tuple[str, ...] = ("SP500", "XYZ100", "NVDA", "AAPL", "MSFT"),
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    remediation_planner_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    validation = validate_artifacts(data_dir, schema_root, strict=True)
    stale_thresholds = _load_stale_thresholds()
    spread_thresholds = _load_spread_thresholds()
    prior_summary = safe_read_json_dict(summary_path)
    has_trade_xyz_artifacts = (
        (data_dir / "registry/trade_xyz_instrument_registry.json").exists()
        or (data_dir / "ops/trade_xyz_quote_collection_summary.json").exists()
        or _latest_path(data_dir / "raw/quotes/trade_xyz", "*.jsonl") is not None
    )
    diagnostics: list[dict] = []
    for symbol in diagnostics_symbols:
        items = build_quote_diagnostics(
            data_dir / "raw/quotes",
            venue="trade_xyz",
            symbol=symbol,
            stale_thresholds_ms=stale_thresholds,
            latest_only=True,
        )
        diagnostics.append(
            {
                "symbol": symbol,
                "available": bool(items),
                "items": [item.__dict__.copy() for item in items],
            }
        )

    manifest_path = _latest_path(Path("logs/live_evidence/manifests"), "live_evidence_*.json")
    manifest_payload = safe_read_json_dict(manifest_path)
    evidence_card_path = _latest_path(data_dir / "evidence", "evidence_card_*.json")
    evidence_payload = safe_read_json_dict(evidence_card_path)
    execution_summary = safe_read_json_dict(execution_snapshot_summary_path)
    execution_comparison = safe_read_json_dict(execution_venue_comparison_summary_path)
    execution_diagnostics = safe_read_json_dict(execution_venue_diagnostics_summary_path)
    execution_gap_history = safe_read_json_dict(execution_gap_history_summary_path)
    execution_state_comparison = safe_read_json_dict(
        execution_state_comparison_history_summary_path
    )
    execution_snapshot_drift = safe_read_json_dict(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(evidence_payload)
    collector_gate = _read_only_collector_gate(data_dir)

    decision = evidence_payload.get("decision") or manifest_payload.get("decision")
    venue_decisions = evidence_payload.get("venue_decisions")
    blockers = evidence_payload.get("blockers")
    next_actions = evidence_payload.get("next_actions")

    strict_validation_passed = len(validation.issues) == 0
    diagnostics_all_available = all(item["available"] for item in diagnostics)
    if has_trade_xyz_artifacts:
        healthy_symbols = {
            str(item["symbol"])
            for item in diagnostics
            if item["available"]
            and item["items"]
            and all(
                _trade_xyz_diagnostic_healthy(
                    entry,
                    str(item["symbol"]),
                    spread_thresholds,
                )
                for entry in item["items"]
            )
        }
        index_healthy = {"SP500", "XYZ100"}.issubset(healthy_symbols)
        individual_healthy = {"NVDA", "AAPL", "MSFT"}.issubset(healthy_symbols)
        if strict_validation_passed and diagnostics_all_available and individual_healthy:
            decision = "READ_ONLY_GO"
            individual_stock_decision = "paper_only"
            index_only_decision = "not_required"
        elif strict_validation_passed and index_healthy:
            decision = "CONDITIONAL_INDEX_ONLY"
            individual_stock_decision = "disabled_index_only"
            index_only_decision = "enabled"
        else:
            decision = "NO_GO"
            individual_stock_decision = "disabled_index_only"
            index_only_decision = "blocked"
        trade_xyz_blockers = _trade_xyz_diagnostic_blockers(diagnostics, spread_thresholds)
        venue_decisions = [
            {
                "venue": "trade_xyz",
                "decision": decision,
                "main_blocker": None
                if decision != "NO_GO"
                else (
                    trade_xyz_blockers[0] if trade_xyz_blockers else "trade_xyz_evidence_incomplete"
                ),
            }
        ]
        blockers = [] if decision != "NO_GO" else trade_xyz_blockers
        pr12_summary = safe_read_json_dict(data_dir / "ops/pr12_fresh_read_only_smoke_summary.json")
        pr12_observed_window = pr12_summary.get("observed_window_seconds")
        pr12_observed_window_ok = (
            isinstance(pr12_observed_window, int | float)
            and not isinstance(pr12_observed_window, bool)
            and pr12_observed_window >= 3600
        )
        pr12_completed = (
            pr12_summary.get("final_decision") == "READ_ONLY_GO"
            and pr12_observed_window_ok
            and pr12_summary.get("next_action") == "none"
        )
        next_actions = [] if pr12_completed else ["run_pr12_fresh_read_only_smoke"]
    else:
        decision = "NO_GO"
        venue_decisions = [
            {
                "venue": "trade_xyz",
                "decision": "NO_GO",
                "main_blocker": "missing_trade_xyz_evidence",
            }
        ]
        blockers = _as_str_list(collector_gate.get("read_only_collector_blockers"))
        next_actions = ["collect_trade_xyz_read_only_evidence"]
        individual_stock_decision = "unknown"
        index_only_decision = "unknown"
    phase2_entry_allowed = bool(
        strict_validation_passed
        and diagnostics_all_available
        and collector_gate["read_only_collector_gate_passed"] is True
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
        "latest_evidence_card_path": str(evidence_card_path)
        if evidence_card_path is not None
        else None,
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
            str(execution_gap_history_summary_path)
            if execution_gap_history_summary_path is not None
            else None
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
        "individual_stock_decision": individual_stock_decision,
        "index_only_decision": index_only_decision,
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
        **latest_execution_lineage,
        **collector_gate,
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
        "recommended_read_order": recommended_read_order(
            [
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
            ]
        ),
    }
    execution_drift_classifications = _execution_drift_classifications(summary)
    summary["execution_drift_classifications"] = execution_drift_classifications
    summary["execution_drift_classification_counts"] = {
        "P2_BLOCKER": sum(
            1
            for item in execution_drift_classifications
            if item.get("classification") == "P2_BLOCKER"
        ),
        "LIVE_READINESS_BLOCKER": sum(
            1
            for item in execution_drift_classifications
            if item.get("classification") == "LIVE_READINESS_BLOCKER"
        ),
    }
    required_artifact_paths = _required_artifact_paths(summary)
    missing_required_artifact_paths = [
        key for key, value in required_artifact_paths.items() if not value
    ]
    artifact_recovery_commands = _artifact_recovery_commands(missing_required_artifact_paths)
    remediation_order = _remediation_order(
        summary,
        missing_required_artifact_paths,
        artifact_recovery_commands,
    )
    remediation_success_criteria = {
        item["reason"]: _remediation_success_criteria(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_commands = {
        item["reason"]: _remediation_preflight_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_commands = {
        item["reason"]: _remediation_postcheck_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_expected_outputs = {
        item["reason"]: _remediation_preflight_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_execute_expected_outputs = {
        item["reason"]: _remediation_execute_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_pass_signals = {
        item["reason"]: _remediation_postcheck_pass_signals(str(item["reason"]))
        for item in remediation_order
    }
    remediation_signal_snapshots_before = {
        item["reason"]: _remediation_signal_snapshot_before(str(item["reason"]), summary)
        for item in remediation_order
    }
    remediation_signal_snapshots_target = {
        item["reason"]: _remediation_signal_snapshot_target(str(item["reason"]))
        for item in remediation_order
    }
    previous_signal_snapshots_value = prior_summary.get("remediation_signal_snapshots_before")
    previous_signal_snapshots = (
        cast(dict[str, Any], previous_signal_snapshots_value)
        if isinstance(previous_signal_snapshots_value, dict)
        else {}
    )
    remediation_signal_snapshot_diffs = {
        item["reason"]: compare_signal_snapshots(
            previous_signal_snapshots.get(str(item["reason"])),
            remediation_signal_snapshots_before.get(str(item["reason"])),
            remediation_signal_snapshots_target.get(str(item["reason"])),
        )
        for item in remediation_order
    }
    previous_recommendations_value = prior_summary.get("remediation_recommendations")
    previous_recommendations = (
        cast(dict[str, Any], previous_recommendations_value)
        if isinstance(previous_recommendations_value, dict)
        else {}
    )
    current_planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    current_evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    current_planner_entries_value = current_planner_summary.get("entries")
    current_planner_entries = (
        cast(list[object], current_planner_entries_value)
        if isinstance(current_planner_entries_value, list)
        else []
    )
    current_provenance_hints = {
        str(cast(dict[str, Any], item).get("reason")): cast(dict[str, Any], item)
        for item in current_planner_entries
        if isinstance(item, dict)
        and cast(dict[str, Any], item).get("source") == "phase_gate_review"
        and cast(dict[str, Any], item).get("reason")
    }
    current_signal_provenance_hints = signal_observed_sources_by_reason(
        current_evaluator_summary,
        source="phase_gate_review",
    )
    remediation_recommendations = {
        str(item["reason"]): recommend_remediation_actions(
            remediation_signal_snapshot_diffs.get(str(item["reason"])),
            preflight_commands=remediation_preflight_commands.get(str(item["reason"]), []),
            execute_commands=item["commands"],
            postcheck_commands=remediation_postcheck_commands.get(str(item["reason"]), []),
            source_confidence=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_confidence")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_confidence")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            source_policy=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_policy")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_policy")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            execute_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_execute_expected_outputs.get(str(item["reason"]), []),
            ),
            postcheck_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_postcheck_pass_signals.get(str(item["reason"]), []),
            ),
        )
        for item in remediation_order
    }
    summary["remediation_planner_summary_path"] = (
        str(remediation_planner_summary_path)
        if remediation_planner_summary_path is not None
        else None
    )
    summary["remediation_evaluator_summary_path"] = (
        str(remediation_evaluator_summary_path)
        if remediation_evaluator_summary_path is not None
        else None
    )
    summary["required_artifact_paths"] = required_artifact_paths
    summary["missing_required_artifact_paths"] = missing_required_artifact_paths
    summary["artifact_recovery_commands"] = artifact_recovery_commands
    summary["remediation_order"] = remediation_order
    summary["remediation_success_criteria"] = remediation_success_criteria
    summary["remediation_preflight_commands"] = remediation_preflight_commands
    summary["remediation_postcheck_commands"] = remediation_postcheck_commands
    summary["remediation_preflight_expected_outputs"] = remediation_preflight_expected_outputs
    summary["remediation_execute_expected_outputs"] = remediation_execute_expected_outputs
    summary["remediation_postcheck_pass_signals"] = remediation_postcheck_pass_signals
    summary["remediation_signal_snapshots_before"] = remediation_signal_snapshots_before
    summary["remediation_signal_snapshots_target"] = remediation_signal_snapshots_target
    summary["remediation_signal_snapshots_previous"] = previous_signal_snapshots
    summary["remediation_signal_snapshot_diffs"] = remediation_signal_snapshot_diffs
    summary["remediation_recommendations"] = remediation_recommendations
    quick_navigation = _quick_navigation(summary, data_dir)
    related_reports = _related_reports(summary, data_dir)
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports
    text = render_phase_gate_review_markdown(summary)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
