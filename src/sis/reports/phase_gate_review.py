from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from sis.reports.doc_paths import CODE_STATUS_DOC, recommended_read_order
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    compare_signal_snapshots,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_lineage_flat_lines,
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


class RemediationStep(TypedDict):
    priority: int
    reason: str
    commands: list[str]


def _reports_dir(data_dir: Path) -> Path:
    return data_dir / "reports"


def _quick_navigation(summary: dict[str, object], data_dir: Path) -> dict[str, str]:
    reports_dir = _reports_dir(data_dir)
    items = (
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("remediation_scoreboard_report", str(reports_dir / "remediation_scoreboard.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(summary: dict[str, object], data_dir: Path) -> dict[str, str]:
    reports_dir = _reports_dir(data_dir)
    items = (
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("remediation_scoreboard_report", str(reports_dir / "remediation_scoreboard.md")),
        ("go_no_go_report", str(data_dir / "research" / "go_no_go_report.md")),
        (
            "paper_vs_backtest_comparison_report",
            str(reports_dir / "paper_vs_backtest_comparison.md"),
        ),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _latest_path(pattern_root: Path, glob_pattern: str) -> Path | None:
    paths = sorted(pattern_root.glob(glob_pattern))
    return paths[-1] if paths else None


def _read_only_collector_gate(data_dir: Path) -> dict[str, object]:
    trade_registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    trade_summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    trade_quote_path = _latest_path(data_dir / "raw/quotes/trade_xyz", "*.jsonl")
    blockers: list[str] = []
    if not trade_registry_path.exists():
        blockers.append("missing_trade_xyz_registry")
    if not trade_quote_path:
        blockers.append("missing_trade_xyz_quote_window")
    if not trade_summary_path.exists():
        blockers.append("missing_trade_xyz_quote_collection_summary")
    return {
        "read_only_collector_gate_passed": not blockers,
        "read_only_collector_blockers": blockers,
        "latest_trade_xyz_registry_path": str(trade_registry_path)
        if trade_registry_path.exists()
        else None,
        "latest_trade_xyz_quote_path": str(trade_quote_path) if trade_quote_path else None,
        "latest_trade_xyz_summary_path": str(trade_summary_path)
        if trade_summary_path.exists()
        else None,
        "latest_gtrade_backend_manifest_path": None,
        "latest_gtrade_backend_status": None,
        "latest_gtrade_backend_event_count": None,
        "latest_gtrade_backend_reconnect_count": None,
        "latest_gtrade_backend_deep_reorg_detected": None,
        "latest_ostium_constraint_path": None,
        "latest_ostium_constraint_status": None,
        "latest_ostium_constraint_failures": [],
        "latest_ostium_python_sdk_status": None,
        "latest_ostium_builder_prices_artifact_path": None,
    }


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
        "trade_xyz": int(stale_policy.get("trade_xyz_max_age_ms", 5000)),
    }


def _load_spread_thresholds() -> dict[str, float]:
    try:
        from sis.risk.halt_policy import load_halt_policy

        policy = load_halt_policy()
        spread_policy = (
            policy.get("halt_policy", policy).get("spread", {}).get("max_spread_bps", {})
        )
    except FileNotFoundError:
        spread_policy = {}
    if not isinstance(spread_policy, dict):
        spread_policy = {}
    return {
        str(key): float(value)
        for key, value in spread_policy.items()
        if isinstance(value, (int, float))
    }


def _spread_threshold_for_symbol(symbol: str, thresholds: dict[str, float]) -> float:
    if symbol in thresholds:
        return thresholds[symbol]
    if symbol in {"SP500", "XYZ100", "SPY", "QQQ"}:
        return thresholds.get("default_index", 12.0)
    return thresholds.get("default_equity", 25.0)


def _trade_xyz_diagnostic_healthy(
    entry: dict, symbol: str, spread_thresholds: dict[str, float]
) -> bool:
    spread_p90 = entry.get("spread_p90_bps")
    return (
        entry.get("missing_mark_price_rate") == 0
        and entry.get("missing_oracle_price_rate") == 0
        and entry.get("missing_funding_rate") == 0
        and entry.get("missing_open_interest_rate") == 0
        and entry.get("stale_rate") == 0
        and entry.get("l2_only_rate") == 0
        and entry.get("fee_mode_unknown_rate") == 0
        and isinstance(spread_p90, (int, float))
        and spread_p90 <= _spread_threshold_for_symbol(symbol, spread_thresholds)
    )


def _trade_xyz_diagnostic_blockers(
    diagnostics: list[dict], spread_thresholds: dict[str, float]
) -> list[str]:
    blockers: list[str] = []
    for item in diagnostics:
        symbol = str(item.get("symbol") or "")
        entries = item.get("items")
        if not item.get("available") or not isinstance(entries, list) or not entries:
            blockers.append(f"{symbol}:diagnostics_unavailable")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                blockers.append(f"{symbol}:diagnostics_malformed")
                continue
            spread_p90 = entry.get("spread_p90_bps")
            spread_limit = _spread_threshold_for_symbol(symbol, spread_thresholds)
            checks = {
                "missing_mark_price_rate": entry.get("missing_mark_price_rate"),
                "missing_oracle_price_rate": entry.get("missing_oracle_price_rate"),
                "missing_funding_rate": entry.get("missing_funding_rate"),
                "missing_open_interest_rate": entry.get("missing_open_interest_rate"),
                "stale_rate": entry.get("stale_rate"),
                "l2_only_rate": entry.get("l2_only_rate"),
                "fee_mode_unknown_rate": entry.get("fee_mode_unknown_rate"),
            }
            for name, value in checks.items():
                if value != 0:
                    blockers.append(f"{symbol}:{name}={value}")
            if not isinstance(spread_p90, (int, float)):
                blockers.append(f"{symbol}:spread_p90_bps_missing")
            elif spread_p90 > spread_limit:
                blockers.append(f"{symbol}:spread_p90_bps={spread_p90}>limit={spread_limit}")
    return blockers


def _required_artifact_paths(summary: dict[str, object]) -> dict[str, str | None]:
    artifact_keys = (
        "latest_trade_xyz_registry_path",
        "latest_trade_xyz_quote_path",
        "latest_trade_xyz_summary_path",
    )
    paths: dict[str, str | None] = {}
    for key in artifact_keys:
        value = summary.get(key)
        paths[key] = value if isinstance(value, str) else None
    return paths


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _execution_drift_classifications(summary: dict[str, object]) -> list[dict[str, object]]:
    checks = [
        (
            "execution_drift_overview_status",
            summary.get("execution_drift_overview_status"),
            "ok",
            "LIVE_READINESS_BLOCKER",
            "execution drift must be clean before live execution readiness",
        ),
        (
            "execution_balance_gap_detected",
            summary.get("execution_balance_gap_detected"),
            False,
            "LIVE_READINESS_BLOCKER",
            "balance gaps affect execution readiness, not read-only quote research",
        ),
        (
            "execution_fills_gap_detected",
            summary.get("execution_fills_gap_detected"),
            False,
            "LIVE_READINESS_BLOCKER",
            "fills gaps affect execution readiness, not read-only quote research",
        ),
        (
            "execution_comparison_all_registries_present",
            summary.get("execution_comparison_all_registries_present"),
            True,
            "LIVE_READINESS_BLOCKER",
            "execution venue comparison coverage is required before live execution",
        ),
        (
            "execution_state_comparison_mismatching_count",
            summary.get("execution_state_comparison_mismatching_count"),
            0,
            "LIVE_READINESS_BLOCKER",
            "execution state mismatches are live-readiness drift",
        ),
        (
            "execution_snapshot_drift_mismatching_snapshot_count",
            summary.get("execution_snapshot_drift_mismatching_snapshot_count"),
            0,
            "LIVE_READINESS_BLOCKER",
            "execution snapshot drift is live-readiness drift",
        ),
    ]
    classifications: list[dict[str, object]] = []
    for signal, observed, expected, classification, reason in checks:
        if observed == expected or observed is None:
            continue
        classifications.append(
            {
                "signal": signal,
                "observed": observed,
                "expected": expected,
                "classification": classification,
                "reason": reason,
            }
        )
    return classifications


def _artifact_recovery_commands(artifact_names: list[str]) -> dict[str, list[str]]:
    command_map = {
        "latest_manifest_path": ["uv run sis phase-gate-review"],
        "latest_evidence_card_path": [
            "uv run sis check-go-no-go",
            "uv run sis build-evidence-card",
        ],
        "latest_execution_snapshot_summary_path": ["uv run sis refresh-operations-artifacts"],
        "latest_execution_venue_comparison_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "latest_execution_venue_diagnostics_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "latest_execution_gap_history_summary_path": ["uv run sis refresh-operations-artifacts"],
        "latest_execution_state_comparison_history_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "latest_execution_snapshot_drift_history_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "latest_execution_drift_overview_summary_path": ["uv run sis refresh-operations-artifacts"],
        "latest_trade_xyz_registry_path": ["uv run sis probe trade-xyz"],
        "latest_trade_xyz_quote_path": ["uv run sis collect-trade-xyz-quotes --no-normalize"],
        "latest_trade_xyz_summary_path": [
            "uv run sis collect-trade-xyz-quotes --write-summary --write-report"
        ],
    }
    return {
        name: command_map.get(name, ["uv run sis refresh-operations-artifacts"])
        for name in artifact_names
    }


def _remediation_order(
    summary: dict[str, object],
    missing_required_artifact_paths: list[str],
    artifact_recovery_commands: dict[str, list[str]],
) -> list[RemediationStep]:
    steps: list[RemediationStep] = []
    if missing_required_artifact_paths:
        commands: list[str] = []
        for name in missing_required_artifact_paths:
            commands.extend(artifact_recovery_commands.get(name, []))
        steps.append(
            {
                "priority": 1,
                "reason": "missing_required_artifacts",
                "commands": list(dict.fromkeys(commands)),
            }
        )
    strict_validation_issue_count = _as_int(summary.get("strict_validation_issue_count")) or 0
    if strict_validation_issue_count > 0:
        steps.append(
            {
                "priority": 2,
                "reason": "strict_validation_failed",
                "commands": ["uv run sis validate-artifacts --strict"],
            }
        )
    if summary.get("diagnostics_all_available") is not True:
        steps.append(
            {
                "priority": 3,
                "reason": "diagnostics_unavailable",
                "commands": ["uv run sis diagnose-quotes"],
            }
        )
    classification_counts = summary.get("execution_drift_classification_counts")
    p2_blocker_count = (
        _as_int(classification_counts.get("P2_BLOCKER"))
        if isinstance(classification_counts, dict)
        else 0
    ) or 0
    phase2_entry_allowed = summary.get("phase2_entry_allowed") is True
    execution_drift_is_live_readiness_only = phase2_entry_allowed and p2_blocker_count == 0
    if (
        summary.get("execution_drift_overview_status") != "ok"
        and not execution_drift_is_live_readiness_only
    ):
        steps.append(
            {
                "priority": 4,
                "reason": "execution_drift_unresolved",
                "commands": ["uv run sis refresh-operations-artifacts"],
            }
        )
    if summary.get("phase2_entry_allowed") is not True:
        steps.append(
            {
                "priority": 5,
                "reason": "phase_gate_not_cleared",
                "commands": ["uv run sis check-go-no-go", "uv run sis build-evidence-card"],
            }
        )
    return steps


def _remediation_success_criteria(reason: str) -> list[str]:
    criteria_map = {
        "missing_required_artifacts": [
            "missing_required_artifact_paths is empty",
            "required artifact paths are non-null",
        ],
        "strict_validation_failed": [
            "strict_validation_issue_count == 0",
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "diagnostics_unavailable": [
            "diagnostics_all_available == True",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_drift_overview_diagnostics_alignment_match == True",
        ],
        "phase_gate_not_cleared": [
            "phase2_entry_allowed == True",
            "decision in {GO, CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST}",
        ],
    }
    return criteria_map.get(reason, [])


def _remediation_preflight_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis implementation-status"],
        "strict_validation_failed": ["uv run sis validate-artifacts --strict"],
        "diagnostics_unavailable": ["uv run sis diagnose-quotes"],
        "execution_drift_unresolved": ["uv run sis refresh-operations-artifacts"],
        "phase_gate_not_cleared": ["uv run sis check-go-no-go"],
    }
    return command_map.get(reason, [])


def _remediation_postcheck_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis phase-gate-review"],
        "strict_validation_failed": ["uv run sis phase-gate-review"],
        "diagnostics_unavailable": ["uv run sis phase-gate-review"],
        "execution_drift_unresolved": ["uv run sis phase-gate-review"],
        "phase_gate_not_cleared": [
            "uv run sis build-evidence-card",
            "uv run sis phase-gate-review",
        ],
    }
    return command_map.get(reason, [])


def _remediation_preflight_expected_outputs(reason: str) -> list[str]:
    output_map = {
        "missing_required_artifacts": [
            "implementation-status exits 0",
            f"{CODE_STATUS_DOC} is regenerated",
        ],
        "strict_validation_failed": [
            "validate-artifacts --strict reports the current issue count",
            "strict validation output includes checked_files",
            "strict validation preview lists current issues",
        ],
        "diagnostics_unavailable": [
            "diagnose-quotes prints per-symbol diagnostics rows",
            "required symbols show quote diagnostics coverage",
        ],
        "execution_drift_unresolved": [
            "refresh-operations-artifacts regenerates execution summaries",
            "execution drift overview summary is rewritten",
        ],
        "phase_gate_not_cleared": [
            "check-go-no-go prints the current decision and blockers",
            "current gate decision is visible before regeneration",
            "phase gate summary lists blockers",
            "phase gate summary lists next actions",
        ],
    }
    return output_map.get(reason, [])


def _remediation_execute_expected_outputs(reason: str) -> list[str]:
    output_map = {
        "missing_required_artifacts": [
            "mapped recovery commands exit 0",
            "missing required artifact paths shrink or become empty",
        ],
        "strict_validation_failed": [
            "strict validation output reports issues=0",
            "strict validation output reports checked_files >= 1",
        ],
        "diagnostics_unavailable": [
            "diagnostics report is regenerated",
            "required quote diagnostics artifacts are available",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_summary.json is regenerated",
            "drift status is re-evaluated from fresh artifacts",
        ],
        "phase_gate_not_cleared": [
            "evidence card is regenerated",
            "go/no-go decision artifacts are refreshed",
        ],
    }
    return output_map.get(reason, [])


def _remediation_postcheck_pass_signals(reason: str) -> list[str]:
    signal_map = {
        "missing_required_artifacts": [
            "missing_required_artifact_paths is empty",
            "required artifact paths are non-null",
        ],
        "strict_validation_failed": [
            "strict_validation_issue_count == 0",
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "diagnostics_unavailable": [
            "diagnostics_all_available == True",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_drift_overview_diagnostics_alignment_match == True",
        ],
        "phase_gate_not_cleared": [
            "phase2_entry_allowed == True",
            "decision in {GO, CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST}",
        ],
    }
    return signal_map.get(reason, [])


def _remediation_signal_snapshot_before(
    reason: str, summary: dict[str, object]
) -> dict[str, object]:
    snapshot_map = {
        "missing_required_artifacts": {
            "missing_required_artifact_paths": summary.get("missing_required_artifact_paths"),
            "latest_manifest_path": summary.get("latest_manifest_path"),
            "latest_evidence_card_path": summary.get("latest_evidence_card_path"),
        },
        "strict_validation_failed": {
            "strict_validation_issue_count": summary.get("strict_validation_issue_count"),
            "phase_gate_strict_validation_issue_count": summary.get(
                "phase_gate_strict_validation_issue_count"
            ),
        },
        "diagnostics_unavailable": {
            "diagnostics_all_available": summary.get("diagnostics_all_available"),
            "diagnostics_symbols": summary.get("diagnostics_symbols"),
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": summary.get("execution_drift_overview_status"),
            "execution_drift_overview_diagnostics_alignment_match": summary.get(
                "execution_drift_overview_diagnostics_alignment_match"
            ),
        },
        "phase_gate_not_cleared": {
            "phase2_entry_allowed": summary.get("phase2_entry_allowed"),
            "decision": summary.get("decision"),
        },
    }
    return snapshot_map.get(reason, {})


def _remediation_signal_snapshot_target(reason: str) -> dict[str, object]:
    snapshot_map: dict[str, dict[str, object]] = {
        "missing_required_artifacts": {
            "missing_required_artifact_paths": [],
            "required_artifact_paths_non_null": True,
        },
        "strict_validation_failed": {
            "strict_validation_issue_count": 0,
            "phase_gate_strict_validation_issue_count": 0,
        },
        "diagnostics_unavailable": {
            "diagnostics_all_available": True,
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": "ok",
            "execution_drift_overview_diagnostics_alignment_match": True,
        },
        "phase_gate_not_cleared": {
            "phase2_entry_allowed": True,
            "decision": ["GO", "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"],
        },
    }
    return snapshot_map.get(reason, {})


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
    previous_signal_snapshots = (
        prior_summary.get("remediation_signal_snapshots_before")
        if isinstance(prior_summary.get("remediation_signal_snapshots_before"), dict)
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
    previous_recommendations = (
        prior_summary.get("remediation_recommendations")
        if isinstance(prior_summary.get("remediation_recommendations"), dict)
        else {}
    )
    current_planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    current_evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    current_provenance_hints = {
        str(item.get("reason")): item
        for item in current_planner_summary.get("entries", [])
        if isinstance(item, dict)
        and item.get("source") == "phase_gate_review"
        and item.get("reason")
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
    venue_decisions = _as_dict_list(summary.get("venue_decisions"))
    next_actions = _as_str_list(summary.get("next_actions"))
    recommended_read_order_items = _as_str_list(summary.get("recommended_read_order"))

    lines = [
        "# Phase Gate Review",
        "",
        "## Executive Summary",
        "",
        f"- current_phase: {summary['current_phase']}",
        f"- decision: {summary['decision']}",
        f"- individual_stock_decision: {summary['individual_stock_decision']}",
        f"- index_only_decision: {summary['index_only_decision']}",
        f"- strict_validation_passed: {summary['strict_validation_passed']}",
        f"- strict_validation_issue_count: {summary['strict_validation_issue_count']}",
        f"- latest_manifest_status: {summary['latest_manifest_status']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase2_entry_reason: {summary['phase2_entry_reason']}",
        f"- read_only_collector_gate_passed: {summary['read_only_collector_gate_passed']}",
        f"- read_only_collector_blockers: {summary['read_only_collector_blockers'] or 'none'}",
        f"- latest_gtrade_backend_manifest_path: {summary['latest_gtrade_backend_manifest_path']}",
        f"- latest_ostium_constraint_path: {summary['latest_ostium_constraint_path']}",
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
        (
            "- execution_drift_p2_blocker_count: "
            f"{summary['execution_drift_classification_counts']['P2_BLOCKER']}"
        ),
        (
            "- execution_drift_live_readiness_blocker_count: "
            f"{summary['execution_drift_classification_counts']['LIVE_READINESS_BLOCKER']}"
        ),
        *latest_execution_lineage_flat_lines(summary),
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in quick_navigation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Related Reports", ""])
    for key, value in related_reports.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
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
            "## Required Artifacts",
            "",
            "",
            "## Strict Validation",
            "",
            f"- checked_files: {summary['checked_files']}",
        ]
    )
    lines.extend(f"- {name}: {value}" for name, value in required_artifact_paths.items())
    if missing_required_artifact_paths:
        lines.append("- missing_required_artifact_paths:")
        lines.extend(f"  - {name}" for name in missing_required_artifact_paths)
    else:
        lines.append("- missing_required_artifact_paths: none")
    lines.extend(["", "## Recovery Commands", ""])
    if artifact_recovery_commands:
        for name, commands in artifact_recovery_commands.items():
            lines.append(f"- {name}:")
            lines.extend(f"  - `{command}`" for command in commands)
    else:
        lines.append("- recovery_commands: none")
    lines.extend(["", "## Remediation Order", ""])
    if remediation_order:
        for item in remediation_order:
            lines.append(f"- priority_{item['priority']}: {item['reason']}")
            lines.extend(f"  - `{command}`" for command in item["commands"])
    else:
        lines.append("- remediation_order: none")
    lines.extend(["", "## Remediation Success Criteria", ""])
    if remediation_success_criteria:
        for reason, criteria in remediation_success_criteria.items():
            lines.append(f"- {reason}:")
            lines.extend(f"  - {criterion}" for criterion in criteria)
    else:
        lines.append("- remediation_success_criteria: none")
    lines.extend(["", "## Remediation Command Flow", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight:")
            for command in remediation_preflight_commands.get(reason, []):
                lines.append(f"    - `{command}`")
            lines.append("  - execute:")
            for command in item["commands"]:
                lines.append(f"    - `{command}`")
            lines.append("  - post_check:")
            for command in remediation_postcheck_commands.get(reason, []):
                lines.append(f"    - `{command}`")
    else:
        lines.append("- remediation_command_flow: none")
    lines.extend(["", "## Remediation Verification Signals", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight_expected_output:")
            for value in remediation_preflight_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - execute_expected_output:")
            for value in remediation_execute_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - postcheck_pass_signal:")
            for value in remediation_postcheck_pass_signals.get(reason, []):
                lines.append(f"    - {value}")
    else:
        lines.append("- remediation_verification_signals: none")
    lines.extend(["", "## Remediation Signal Snapshots", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - before:")
            for key, value in remediation_signal_snapshots_before.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
            lines.append("  - target:")
            for key, value in remediation_signal_snapshots_target.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
    else:
        lines.append("- remediation_signal_snapshots: none")
    lines.extend(["", "## Remediation Signal Diffs", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            for key, diff in remediation_signal_snapshot_diffs.get(reason, {}).items():
                lines.append(
                    "  - {key}: previous={previous} current={current} target={target} trend={trend} target_matched={target_matched}".format(
                        key=key,
                        previous=diff.get("previous"),
                        current=diff.get("current"),
                        target=diff.get("target"),
                        trend=diff.get("trend"),
                        target_matched=diff.get("target_matched"),
                    )
                )
    else:
        lines.append("- remediation_signal_diffs: none")
    lines.extend(["", "## Remediation Recommendations", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            recommendation = remediation_recommendations.get(reason, {})
            lines.append(f"- {reason}:")
            lines.append(f"  - status: {recommendation.get('status')}")
            lines.append(f"  - why: {recommendation.get('why')}")
            for command in recommendation.get("commands", []):
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- remediation_recommendations: none")
    if validation.issues:
        lines.append("")
        lines.append("| path | message |")
        lines.append("| --- | --- |")
        for issue in validation.issues:
            lines.append(f"| {issue.path} | {issue.message.replace('|', '/')} |")
    else:
        lines.extend(["", "- issues: none"])

    lines.extend(["", "## Diagnostics", ""])
    lines.append(
        "| symbol | available | rows | tradable_rate | stale_rate | l2_only_rate | fee_mode_unknown_rate | missing_mark_price_rate | missing_index_price_rate | spread_p90_bps |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in diagnostics:
        diagnostic = item["items"][0] if item["items"] else {}
        lines.append(
            "| {symbol} | {available} | {rows} | {tradable_rate} | {stale_rate} | {l2_only} | {fee_unknown} | {missing_mark} | {missing_index} | {spread_p90} |".format(
                symbol=item["symbol"],
                available=item["available"],
                rows=diagnostic.get("rows", ""),
                tradable_rate=diagnostic.get("tradable_rate", ""),
                stale_rate=diagnostic.get("stale_rate", ""),
                l2_only=diagnostic.get("l2_only_rate", ""),
                fee_unknown=diagnostic.get("fee_mode_unknown_rate", ""),
                missing_mark=diagnostic.get("missing_mark_price_rate", ""),
                missing_index=diagnostic.get("missing_index_price_rate", ""),
                spread_p90=diagnostic.get("spread_p90_bps", ""),
            )
        )

    lines.extend(["", "## Venue Decisions", ""])
    if venue_decisions:
        lines.append("| venue | decision | main_blocker |")
        lines.append("| --- | --- | --- |")
        for item in venue_decisions:
            lines.append(
                f"| {item.get('venue', '')} | {item.get('decision', '')} | {item.get('main_blocker', '') or ''} |"
            )
    else:
        lines.append("- venue_decisions: unavailable")

    lines.extend(["", "## Execution Snapshot", ""])
    lines.append(f"- execution_overall_status: {summary['execution_overall_status']}")
    lines.append(f"- execution_venue_count: {summary['execution_venue_count']}")
    lines.append(
        f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}"
    )
    lines.append(f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}")
    lines.append(f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}")
    lines.append(f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}")
    lines.append(
        f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}"
    )
    lines.append(
        f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}"
    )
    lines.append(
        f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}"
    )
    lines.append(
        f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}"
    )
    lines.append(
        f"- execution_state_comparison_latest_status_match: {summary['execution_state_comparison_latest_status_match']}"
    )
    lines.append(
        f"- execution_state_comparison_mismatching_count: {summary['execution_state_comparison_mismatching_count']}"
    )
    lines.append(
        f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}"
    )
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
    lines.append(
        f"- latest_execution_snapshot_summary_path: {summary['latest_execution_snapshot_summary_path']}"
    )
    lines.append(
        f"- latest_execution_venue_comparison_summary_path: {summary['latest_execution_venue_comparison_summary_path']}"
    )
    lines.append(
        f"- latest_execution_venue_diagnostics_summary_path: {summary['latest_execution_venue_diagnostics_summary_path']}"
    )
    lines.append(
        f"- latest_execution_gap_history_summary_path: {summary['latest_execution_gap_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_state_comparison_history_summary_path: {summary['latest_execution_state_comparison_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_snapshot_drift_history_summary_path: {summary['latest_execution_snapshot_drift_history_summary_path']}"
    )
    lines.append(
        f"- latest_execution_drift_overview_summary_path: {summary['latest_execution_drift_overview_summary_path']}"
    )

    lines.extend(["", "## Execution Drift Classification", ""])
    classifications = _as_dict_list(summary.get("execution_drift_classifications"))
    if classifications:
        lines.append("| signal | observed | expected | classification | reason |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in classifications:
            lines.append(
                "| {signal} | {observed} | {expected} | {classification} | {reason} |".format(
                    signal=item.get("signal", ""),
                    observed=item.get("observed", ""),
                    expected=item.get("expected", ""),
                    classification=item.get("classification", ""),
                    reason=str(item.get("reason", "")).replace("|", "/"),
                )
            )
    else:
        lines.append("- execution_drift_classifications: none")

    lines.extend(["", "## Next Actions", ""])
    if next_actions:
        lines.extend(f"- {item}" for item in next_actions)
    else:
        lines.extend(
            [
                "- recollect live evidence during the recommended window",
                "- rerun diagnose-quotes for SP500 / XYZ100 / NVDA / AAPL / MSFT",
                "- rerun validate-artifacts --strict",
                "- rerun check-go-no-go and build-evidence-card",
            ]
        )
    if remediation_order:
        lines.extend(
            [
                "- execute the commands in `Remediation Order` from lower priority number to higher",
            ]
        )

    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(
        [
            "- If `missing_required_artifact_paths` is not empty, stop and regenerate the missing manifest or execution artifacts before continuing.",
            "- If `strict_validation_issue_count` is not `0`, stop and clear strict validation issues before considering Phase 2.",
            "- If `diagnostics_all_available` is not `True`, stop and recollect quote diagnostics for SP500 / XYZ100 / NVDA / AAPL / MSFT.",
            "- If `execution_drift_p2_blocker_count` is greater than `0`, stop before considering Phase 2.",
            "- If `execution_drift_live_readiness_blocker_count` is greater than `0`, stop before live execution readiness; do not treat it as a read-only Phase 2 blocker.",
            "- If `read_only_collector_gate_passed` is not `True`, stop and refresh Trade[XYZ] read-only artifacts with `collect-trade-xyz-quotes --write-summary --write-report` before considering Bot preview work.",
        ]
    )

    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in recommended_read_order_items)
    text = "\n".join(lines) + "\n"

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
