from __future__ import annotations

from typing import TypedDict, cast

from sis.reports import phase_gate_remediation_metadata

remediation_success_criteria = phase_gate_remediation_metadata.remediation_success_criteria
remediation_preflight_commands = phase_gate_remediation_metadata.remediation_preflight_commands
remediation_postcheck_commands = phase_gate_remediation_metadata.remediation_postcheck_commands
remediation_preflight_expected_outputs = (
    phase_gate_remediation_metadata.remediation_preflight_expected_outputs
)
remediation_execute_expected_outputs = (
    phase_gate_remediation_metadata.remediation_execute_expected_outputs
)
remediation_postcheck_pass_signals = (
    phase_gate_remediation_metadata.remediation_postcheck_pass_signals
)
remediation_signal_snapshot_before = (
    phase_gate_remediation_metadata.remediation_signal_snapshot_before
)
remediation_signal_snapshot_target = (
    phase_gate_remediation_metadata.remediation_signal_snapshot_target
)


class RemediationStep(TypedDict):
    priority: int
    reason: str
    commands: list[str]


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


def execution_drift_classifications(summary: dict[str, object]) -> list[dict[str, object]]:
    snapshot_reason = summary.get("execution_snapshot_reason")
    snapshot_root_source = summary.get("execution_snapshot_root_source")
    snapshot_next_action = summary.get("execution_snapshot_next_action")
    if not isinstance(snapshot_next_action, str) or not snapshot_next_action:
        snapshot_next_action = None
    comparison_reason = summary.get("execution_comparison_reason")
    comparison_root_source = summary.get("execution_comparison_root_source")
    diagnostics_reason = summary.get("execution_diagnostics_reason")
    diagnostics_root_source = summary.get("execution_diagnostics_root_source")
    drift_reason_codes = summary.get("execution_drift_overview_reason_codes")
    if not isinstance(drift_reason_codes, list):
        drift_reason_codes = []

    def lineage_for(signal: str) -> dict[str, object]:
        if signal == "execution_comparison_all_registries_present" and comparison_reason:
            return {
                "root_source": comparison_root_source or snapshot_root_source,
                "derived_from": comparison_reason,
                "recommended_next_action": "explain_or_connect_trade_xyz_execution_snapshot",
            }
        if signal in {"execution_balance_gap_detected", "execution_fills_gap_detected"}:
            return {
                "root_source": diagnostics_root_source or comparison_root_source,
                "derived_from": diagnostics_reason or comparison_reason,
                "recommended_next_action": (
                    snapshot_next_action or "decide_read_only_execution_state_collector_scope"
                ),
            }
        if signal == "execution_drift_overview_status" and drift_reason_codes:
            return {
                "root_source": snapshot_root_source or "execution_snapshot_summary.venues=[]",
                "derived_from": ",".join(str(item) for item in drift_reason_codes),
                "recommended_next_action": "map_root_and_derived_execution_drift_signals",
            }
        if snapshot_reason:
            return {
                "root_source": snapshot_root_source,
                "derived_from": snapshot_reason,
                "recommended_next_action": "preserve_live_readiness_blocker_until_snapshot_connected",
            }
        return {}

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
                **lineage_for(signal),
            }
        )
    return classifications


def artifact_recovery_commands(artifact_names: list[str]) -> dict[str, list[str]]:
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


def remediation_order(
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
        _as_int(cast(dict[str, object], classification_counts).get("P2_BLOCKER"))
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
