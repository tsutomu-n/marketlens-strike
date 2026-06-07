from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.reports.loaders import safe_read_json_dict_list
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_sections,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json

MAX_STALE_RATE = 0.05
MIN_TRADABLE_RATE = 0.95
MAX_SPREAD_P90_BPS = 25.0


def latest_positions_sidecar(root: Path) -> Path | None:
    return None


def positions_have_liquidation_reference(path: Path | None) -> bool:
    return False


def _reports_dir(out_path: Path) -> Path:
    base = out_path.parent.parent if out_path.parent.name == "research" else out_path.parent
    return base / "reports"


def _quick_navigation(
    out_path: Path,
    phase_gate_summary: dict | None,
    readiness_summary: dict | None,
) -> dict[str, str]:
    reports_dir = _reports_dir(out_path)
    phase_gate_flat = phase_gate_flat_fields(phase_gate_summary or {})
    readiness_flat = readiness_flat_fields(readiness_summary or {})
    items = (
        ("go_no_go_report", str(out_path)),
        (
            "phase_gate_review_report",
            phase_gate_flat.get("phase_gate_review_report_path"),
        ),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("live_evidence_report", readiness_flat.get("live_evidence_report_path")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(
    out_path: Path,
    phase_gate_summary: dict | None,
    readiness_summary: dict | None,
    execution_summary: dict | None,
    execution_comparison_summary: dict | None,
    execution_diagnostics_summary: dict | None,
    execution_gap_history_summary: dict | None,
    execution_state_comparison_summary: dict | None,
    execution_snapshot_drift_summary: dict | None,
    execution_drift_overview_summary: dict | None,
) -> dict[str, str]:
    reports_dir = _reports_dir(out_path)
    phase_gate_flat = phase_gate_flat_fields(phase_gate_summary or {})
    readiness_flat = readiness_flat_fields(readiness_summary or {})
    execution_summary_flat = execution_snapshot_flat_fields(execution_summary or {})
    execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary or {})
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        execution_diagnostics_summary or {}
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        execution_gap_history_summary or {}
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        execution_state_comparison_summary or {}
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_summary or {}
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        execution_drift_overview_summary or {}
    )
    items = (
        ("go_no_go_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_flat.get("phase_gate_review_report_path")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("live_evidence_report", readiness_flat.get("live_evidence_report_path")),
        ("execution_snapshot_report", execution_summary_flat.get("execution_report_path")),
        (
            "execution_venue_comparison_report",
            execution_comparison_flat.get("execution_comparison_report_path"),
        ),
        (
            "execution_venue_diagnostics_report",
            execution_diagnostics_flat.get("execution_diagnostics_report_path"),
        ),
        (
            "execution_gap_history_report",
            execution_gap_history_flat.get("execution_gap_history_report_path"),
        ),
        (
            "execution_state_comparison_report",
            execution_state_comparison_flat.get("execution_state_comparison_report_path"),
        ),
        (
            "execution_snapshot_drift_report",
            execution_snapshot_drift_flat.get("execution_snapshot_drift_report_path"),
        ),
        (
            "execution_drift_overview_report",
            execution_drift_flat.get("execution_drift_overview_report_path"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _ostium_registry_resolved(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    return all(
        isinstance(item, dict)
        and cast(dict[str, Any], item).get("active") is True
        and cast(dict[str, Any], item).get("venue_symbol") != "requires_probe"
        for item in data
    )


def _ostium_fees_oi_complete(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    target_rows = [
        cast(dict[str, Any], item)
        for item in data
        if isinstance(item, dict) and cast(dict[str, Any], item).get("venue") == "ostium"
    ]
    return bool(target_rows) and all(
        item.get("opening_fee_bps") is not None
        and item.get("max_open_interest") is not None
        and item.get("rollover_fee_per_block") is not None
        and item.get("max_leverage") is not None
        for item in target_rows
    )


def _load_backtest_metrics(path: Path) -> list[dict]:
    return safe_read_json_dict_list(path)


def _backtest_expected_value_result(path: Path) -> str:
    metrics = _load_backtest_metrics(path)
    if not metrics:
        return "MISSING"
    traded = [item for item in metrics if int(item.get("trade_count") or 0) > 0]
    if not traded:
        return "NO_GO"
    if any(float(item.get("avg_trade_return") or 0.0) > 0.0 for item in traded):
        return "PASS"
    return "NO_GO"


def _cost_matrix_rows(path: Path) -> list[dict[str, str | None]]:
    if not path.exists():
        return []
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _threshold_result(
    rows: list[dict[str, str | None]],
    column: str,
    *,
    maximum: float | None = None,
    minimum: float | None = None,
) -> str:
    values: list[float] = []
    for row in rows:
        value = row.get(column)
        if value in {None, ""}:
            return "MISSING"
        if value is None:
            return "MISSING"
        values.append(float(value))
    if not values:
        return "MISSING"
    if maximum is not None and any(value > maximum for value in values):
        return "NO_GO"
    if minimum is not None and any(value < minimum for value in values):
        return "NO_GO"
    return "PASS"


def _holding_cost_result(rows: list[dict[str, str | None]]) -> str:
    if not rows:
        return "MISSING"
    required = ("holding_cost_4h_bps", "holding_cost_24h_bps", "holding_cost_72h_bps")
    completed = [all(row.get(column) not in {None, ""} for column in required) for row in rows]
    if all(completed):
        return "PASS"
    if any(completed):
        return "PARTIAL"
    return "MISSING"


def _first_blocker(checks: list[GoNoGoCriterion]) -> str | None:
    for item in checks:
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}:
            return item.criterion
    return None


def _venue_cost_rows(rows: list[dict[str, str | None]], venue: str) -> list[dict[str, str | None]]:
    return [row for row in rows if row.get("venue") == venue]


def _has_trade_xyz_artifacts(data_dir: Path) -> bool:
    return (
        (data_dir / "registry/trade_xyz_instrument_registry.json").exists()
        or any((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
        or (data_dir / "ops/trade_xyz_quote_collection_summary.json").exists()
    )


def _latest_trade_xyz_quote(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
    return paths[-1] if paths else None


def _trade_xyz_summary_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    payload = read_json(path)
    if not isinstance(payload, dict):
        return 0
    payload = cast(dict[str, Any], payload)
    try:
        return int(payload.get("row_count") or 0)
    except (TypeError, ValueError):
        return 0


def _build_trade_xyz_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    quote_path = _latest_trade_xyz_quote(data_dir)
    summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    normalized_quotes = data_dir / "normalized/quotes.parquet"
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    row_count = _trade_xyz_summary_row_count(summary_path)
    criteria = [
        GoNoGoCriterion(
            criterion="Trade[XYZ] registry generated",
            result="PASS" if registry.exists() else "MISSING",
            evidence=str(registry),
        ),
        GoNoGoCriterion(
            criterion="Trade[XYZ] quote window collected",
            result="PASS" if quote_path is not None else "MISSING",
            evidence=str(quote_path) if quote_path else str(data_dir / "raw/quotes/trade_xyz"),
        ),
        GoNoGoCriterion(
            criterion="Trade[XYZ] quote collection summary",
            result="PASS"
            if row_count > 0
            else ("MISSING" if not summary_path.exists() else "NO_GO"),
            evidence=str(summary_path),
        ),
        GoNoGoCriterion(
            criterion="Normalized quote data",
            result="PASS" if normalized_quotes.exists() else "MISSING",
            evidence=str(normalized_quotes),
        ),
        GoNoGoCriterion(
            criterion="Phase gate review summary",
            result="PASS" if phase_gate_summary.exists() else "MISSING",
            evidence=str(phase_gate_summary),
        ),
    ]
    blockers = [
        item.criterion
        for item in criteria
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    ]
    next_actions: list[str] = []
    if not registry.exists():
        next_actions.append("Run `uv run sis probe trade-xyz`.")
    if quote_path is None or row_count <= 0:
        next_actions.append(
            "Run `uv run sis collect-trade-xyz-quotes --write-summary --write-report`."
        )
    if not normalized_quotes.exists():
        next_actions.append("Collect Trade[XYZ] quotes with normalization enabled.")
    if not phase_gate_summary.exists():
        next_actions.append("Run `uv run sis phase-gate-review`.")
    decision = Decision.GO if not blockers else Decision.NO_GO
    return GoNoGoReport(
        decision=decision,
        summary=(
            "Trade[XYZ] supplemental Go/No-Go report. Bot readiness is gated by "
            "`phase-gate-review`; this report only summarizes local artifacts."
        ),
        criteria=criteria,
        venue_decisions=[
            VenueDecision(
                venue="trade_xyz",
                decision=decision,
                main_blocker=blockers[0] if blockers else None,
            )
        ],
        blockers=blockers,
        next_actions=next_actions,
    )


def _venue_decision_from_checks(venue: str, checks: list[GoNoGoCriterion]) -> VenueDecision:
    blocker = _first_blocker(checks)
    if blocker is None:
        return VenueDecision(venue=venue, decision=Decision.GO, main_blocker=None)
    blocking_names = {
        item.criterion
        for item in checks
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    }
    data_readiness_blockers = {
        "Ostium symbol resolved",
        "Ostium fees/OI/rollover metadata complete",
        "Liquidation reference complete",
        "Venue cost matrix",
        "Holding/rollover cost reproduced for target horizons",
    }
    if venue == "ostium" and blocking_names and blocking_names.issubset(data_readiness_blockers):
        return VenueDecision(
            venue=venue, decision=Decision.CONDITIONAL_GO_DATA_READY, main_blocker=blocker
        )
    if blocker in {"stale_rate at or below threshold", "tradable_rate at or above threshold"}:
        return VenueDecision(
            venue=venue, decision=Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW, main_blocker=blocker
        )
    if blocker == "spread_p90 at or below threshold":
        return VenueDecision(venue=venue, decision=Decision.NO_GO_COST, main_blocker=blocker)
    return VenueDecision(venue=venue, decision=Decision.NO_GO, main_blocker=blocker)


def _next_actions(blockers: list[str], signals_exists: bool) -> list[str]:
    actions: list[str] = []
    if "stale_rate at or below threshold" in blockers:
        actions.append(
            "Collect quote rows with fresh venue timestamps so stale_rate is at or below threshold"
        )
    if "tradable_rate at or above threshold" in blockers:
        actions.append(
            "Collect a sufficient legacy gTrade/Ostium quote window only if the legacy archive is intentionally restored"
        )
    if not signals_exists:
        actions.append(
            "Provide data/research/signals.csv to run signal-driven backtests instead of quote-only fallback"
        )
    return actions


def _decision_for_state(
    *,
    core_ready: bool,
    blockers: list[str],
    signals_exists: bool,
) -> Decision:
    if not core_ready:
        return Decision.NO_GO
    if not blockers:
        if not signals_exists:
            return Decision.CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST
        return Decision.GO
    blocker_set = set(blockers)
    live_window_blockers = {
        "stale_rate at or below threshold",
        "tradable_rate at or above threshold",
    }
    if blocker_set.issubset(live_window_blockers):
        return Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW
    if (
        "4h-3d after-cost backtest" in blocker_set
        or "Holding/rollover cost reproduced for target horizons" in blocker_set
    ):
        return Decision.NO_GO_COST
    if "stale_rate at or below threshold" in blocker_set:
        return Decision.NO_GO_STALE
    if "tradable_rate at or above threshold" in blocker_set:
        return Decision.NO_GO_SESSION
    return Decision.CONDITIONAL_GO_DATA_READY


def build_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    if _has_trade_xyz_artifacts(data_dir):
        return _build_trade_xyz_go_no_go_report(data_dir)

    gtrade_registry = data_dir / "registry/gtrade_instrument_registry.json"
    ostium_registry = data_dir / "registry/ostium_instrument_registry.json"
    quotes = data_dir / "normalized/quotes.parquet"
    cost_matrix = data_dir / "research/venue_cost_matrix.csv"
    backtest_report = data_dir / "research/backtest_report.md"
    backtest_metrics = data_dir / "research/backtest_metrics.json"
    signals = data_dir / "research/signals.csv"
    ostium_positions = latest_positions_sidecar(data_dir / "raw/sidecar/ostium")
    ostium_resolved = _ostium_registry_resolved(ostium_registry)
    ostium_fees_oi_complete = _ostium_fees_oi_complete(ostium_registry)
    cost_rows = _cost_matrix_rows(cost_matrix)
    gtrade_cost_rows = _venue_cost_rows(cost_rows, "gtrade")
    ostium_cost_rows = _venue_cost_rows(cost_rows, "ostium")

    criteria = [
        GoNoGoCriterion(
            criterion="gTrade registry generated",
            result="PASS" if gtrade_registry.exists() else "MISSING",
            evidence=str(gtrade_registry),
        ),
        GoNoGoCriterion(
            criterion="Ostium symbol resolved",
            result="PASS"
            if ostium_resolved
            else ("REQUIRES_PROBE" if ostium_registry.exists() else "MISSING"),
            evidence=str(ostium_registry),
        ),
        GoNoGoCriterion(
            criterion="Normalized quote data",
            result="PASS" if quotes.exists() else "MISSING",
            evidence=str(quotes),
        ),
        GoNoGoCriterion(
            criterion="Venue cost matrix",
            result="PASS" if cost_matrix.exists() else "MISSING",
            evidence=str(cost_matrix),
        ),
        GoNoGoCriterion(
            criterion="Scalping not required",
            result="PASS",
            evidence="configs/scalping_policy.yaml",
        ),
        GoNoGoCriterion(
            criterion="Ostium fees/OI/rollover metadata complete",
            result="PASS" if ostium_fees_oi_complete else "MISSING",
            evidence=str(ostium_registry),
        ),
        GoNoGoCriterion(
            criterion="Liquidation reference complete",
            result="PASS" if positions_have_liquidation_reference(ostium_positions) else "NOT_DONE",
            evidence=str(ostium_positions)
            if ostium_positions
            else "Legacy Ostium liquidationPx requires restored open-position sidecar data",
        ),
        GoNoGoCriterion(
            criterion="4h-3d after-cost backtest",
            result=_backtest_expected_value_result(backtest_metrics),
            evidence=str(backtest_metrics),
        ),
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS),
            evidence=f"{cost_matrix}; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(cost_rows),
            evidence=str(cost_matrix),
        ),
        GoNoGoCriterion(
            criterion="Research signal CSV connected",
            result="PASS" if signals.exists() else "OPTIONAL_FALLBACK",
            evidence=str(signals),
        ),
    ]

    blockers = [
        item.criterion
        for item in criteria
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    ]
    core_ready = (
        quotes.exists() and cost_matrix.exists() and backtest_report.exists() and ostium_resolved
    )
    decision = _decision_for_state(
        core_ready=core_ready,
        blockers=blockers,
        signals_exists=signals.exists(),
    )
    gtrade_checks = [
        criteria[0],
        criteria[2],
        criteria[3],
        criteria[7],
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(gtrade_cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; venue=gtrade; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(gtrade_cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; venue=gtrade; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(
                gtrade_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS
            ),
            evidence=f"{cost_matrix}; venue=gtrade; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(gtrade_cost_rows),
            evidence=str(cost_matrix),
        ),
    ]
    ostium_checks = [
        criteria[1],
        criteria[2],
        criteria[3],
        criteria[5],
        criteria[6],
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(ostium_cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; venue=ostium; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(ostium_cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; venue=ostium; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(
                ostium_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS
            ),
            evidence=f"{cost_matrix}; venue=ostium; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(ostium_cost_rows),
            evidence=str(cost_matrix),
        ),
    ]

    return GoNoGoReport(
        decision=decision,
        summary="Implementation status report. This evaluates collected evidence and does not authorize live trading.",
        criteria=criteria,
        venue_decisions=[
            _venue_decision_from_checks("gtrade", gtrade_checks),
            _venue_decision_from_checks("ostium", ostium_checks),
        ],
        blockers=blockers,
        next_actions=_next_actions(blockers, signals.exists()),
    )


def write_go_no_go_markdown(
    report: GoNoGoReport,
    out_path: Path,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    readiness_summary = normalize_readiness_summary(readiness_summary)
    execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    rows = "\n".join(
        f"| {item.criterion} | {item.result} | {item.evidence or ''} |" for item in report.criteria
    )
    blockers = "\n".join(f"- {item}" for item in report.blockers) or "- none"
    next_actions = "\n".join(f"- {item}" for item in report.next_actions) or "- none"
    venue_decision_rows = (
        "\n".join(
            f"| {item.venue} | {item.decision.value} | {item.main_blocker or ''} |"
            for item in report.venue_decisions
        )
        or "| none |  |  |"
    )
    quick_navigation = _quick_navigation(out_path, phase_gate_summary, readiness_summary)
    related_reports = _related_reports(
        out_path,
        phase_gate_summary,
        readiness_summary,
        execution_summary,
        execution_comparison_summary,
        execution_diagnostics_summary,
        execution_gap_history_summary,
        execution_state_comparison_summary,
        execution_snapshot_drift_summary,
        execution_drift_overview_summary,
    )
    lines = [
        "# Go/No-Go Report",
        "",
        "## Decision",
        "",
        f"`{report.decision.value}`",
        "",
        "## Summary",
        "",
        report.summary,
        "",
    ]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        audit_summary_flat = audit_summary_fields(audit_summary, audit_summary)
        lines.extend(
            [
                "## Audit Summary",
                "",
                f"- overall_status: {audit_summary_flat.get('overall_status') or ''}",
                f"- latest_operation: {audit_summary_flat.get('latest_operation') or ''}",
                f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count') or ''}",
                "",
            ]
        )
    if isinstance(phase_gate_summary, dict) and any(phase_gate_summary.values()):
        phase_gate_flat = phase_gate_flat_fields(phase_gate_summary)
        lines.extend(
            [
                "## Phase Gate Summary",
                "",
                f"- decision: {phase_gate_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason') or ''}",
                f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                (
                    "- phase_gate_strict_validation_issue_count: "
                    f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                ),
                f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                "",
            ]
        )
    if isinstance(readiness_summary, dict) and any(readiness_summary.values()):
        readiness_flat = readiness_flat_fields(readiness_summary)
        lines.extend(
            [
                "## Readiness Summary",
                "",
                f"- next_phase_candidate: {readiness_flat.get('readiness_next_phase_candidate') or ''}",
                f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                f"- phase_gate_decision: {readiness_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {readiness_flat.get('phase2_entry_allowed')}",
                "",
            ]
        )
    if isinstance(execution_summary, dict) and any(execution_summary.values()):
        execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
        lines.extend(
            [
                "## Execution Snapshot",
                "",
                f"- overall_status: {execution_summary_flat.get('execution_overall_status') or ''}",
                f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                f"- report_path: {execution_summary_flat.get('execution_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_comparison_summary, dict) and any(
        execution_comparison_summary.values()
    ):
        execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary)
        lines.extend(
            [
                "## Execution Venue Comparison",
                "",
                (
                    "- all_registries_present: "
                    f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                ),
                f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_diagnostics_summary, dict) and any(
        execution_diagnostics_summary.values()
    ):
        execution_diagnostics_flat = execution_diagnostics_flat_fields(
            execution_diagnostics_summary
        )
        lines.extend(
            [
                "## Execution Venue Diagnostics",
                "",
                f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status') or ''}",
                f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_gap_history_summary, dict) and any(
        execution_gap_history_summary.values()
    ):
        execution_gap_history_flat = execution_gap_history_flat_fields(
            execution_gap_history_summary
        )
        lines.extend(
            [
                "## Execution Gap History",
                "",
                f"- entry_count: {execution_gap_history_flat.get('execution_gap_history_entry_count')}",
                f"- latest_status: {execution_gap_history_flat.get('execution_gap_history_latest_status') or ''}",
                (
                    "- latest_execution_diagnostics_status: "
                    f"{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status') or ''}"
                ),
                f"- report_path: {execution_gap_history_flat.get('execution_gap_history_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_state_comparison_summary, dict) and any(
        execution_state_comparison_summary.values()
    ):
        execution_state_comparison_flat = execution_state_comparison_flat_fields(
            execution_state_comparison_summary
        )
        lines.extend(
            [
                "## Execution State Comparison History",
                "",
                f"- entry_count: {execution_state_comparison_flat.get('execution_state_comparison_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}"
                ),
                (
                    "- mismatching_count: "
                    f"{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}"
                ),
                f"- report_path: {execution_state_comparison_flat.get('execution_state_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_snapshot_drift_summary, dict) and any(
        execution_snapshot_drift_summary.values()
    ):
        execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
            execution_snapshot_drift_summary
        )
        lines.extend(
            [
                "## Execution Snapshot Drift History",
                "",
                f"- entry_count: {execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}",
                (
                    "- latest_status_match: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}"
                ),
                (
                    "- mismatching_snapshot_count: "
                    f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_drift_overview_summary, dict) and any(
        execution_drift_overview_summary.values()
    ):
        execution_drift_flat = execution_drift_overview_flat_fields(
            execution_drift_overview_summary
        )
        lines.extend(
            [
                "## Execution Drift Overview",
                "",
                f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status') or ''}",
                (
                    "- diagnostics_alignment_match: "
                    f"{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}"
                ),
                (
                    "- state_comparison_mismatching_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}"
                ),
                (
                    "- snapshot_drift_mismatching_snapshot_count: "
                    f"{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
                ),
                f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path') or ''}",
                "",
            ]
        )
    lines.extend(
        latest_execution_sections(
            [
                (
                    "## Audit Timeline Latest Execution",
                    timeline_latest_execution_summary,
                    timeline_latest_execution_comparison_summary,
                ),
                (
                    "## Audit Bundle History Latest Execution",
                    bundle_history_latest_execution_summary,
                    bundle_history_latest_execution_comparison_summary,
                ),
                (
                    "## Cycle History Latest Execution",
                    cycle_history_latest_execution_summary,
                    cycle_history_latest_execution_comparison_summary,
                ),
            ]
        )
    )
    lines.extend(
        [
            "## Criteria",
            "",
            "| Criterion | Result | Evidence |",
            "|---|---|---|",
            rows,
            "",
            "## Venue Decisions",
            "",
            "| Venue | Decision | Main Blocker |",
            "|---|---|---|",
            venue_decision_rows,
            "",
            "## Blockers",
            "",
            blockers,
            "",
            "## Next Actions",
            "",
            next_actions,
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
