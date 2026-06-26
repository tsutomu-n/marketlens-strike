from __future__ import annotations

import re

from sis.reports import remediation_signal_core
from sis.reports.remediation_signal_observations import (
    coerce_value,
    diagnostics_row_presence,
    observed_counts,
    observed_fields,
)


_IN_SET_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s+in\s+\{(?P<values>.+)\}$")
_EQ_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s*==\s*(?P<value>.+)$")
_EMPTY_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+is\s+empty$")
_NON_NULL_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+are\s+non-null$")
_EXIT_CODE_RE = re.compile(r"^(?P<label>.+)\s+exits\s+(?P<code>-?\d+)$")
_REPORTS_ISSUES_RE = re.compile(r"^(?P<label>.+)\s+reports\s+issues=(?P<issues>-?\d+)$")
_REPORTS_CURRENT_ISSUE_COUNT_RE = re.compile(r"^(?P<label>.+)\s+reports\s+the current issue count$")
_REPORTS_CHECKED_FILES_GTE_RE = re.compile(
    r"^(?P<label>.+)\s+reports\s+checked_files\s+>=\s+(?P<count>\d+)$"
)
_INCLUDES_CHECKED_FILES_RE = re.compile(r"^(?P<label>.+)\s+includes\s+checked_files$")
_PRINTS_FIELD_RE = re.compile(r"^(?P<label>.+)\s+prints\s+(?P<field>[A-Za-z0-9_]+)$")
_PRINTS_PER_SYMBOL_ROWS_RE = re.compile(r"^(?P<label>.+)\s+prints\s+per-symbol diagnostics rows$")

issue_preview_values = remediation_signal_core.issue_preview_values
evaluate_signal = remediation_signal_core.evaluate_signal
action_result = remediation_signal_core.action_result
evaluator_status = remediation_signal_core.evaluator_status

__all__ = [
    "action_result",
    "coerce_value",
    "diagnostics_row_presence",
    "evaluate_signal",
    "evaluate_signal_with_observations",
    "evaluator_status",
    "issue_preview_values",
    "observed_counts",
    "observed_fields",
]


def evaluate_signal_with_observations(
    signal: str,
    summary: dict,
    observed_signals: list[str],
    latest_exit_code: int | None,
    stdout_summary: str | None,
    stderr_summary: str | None,
    manifest_fields: dict[str, object],
    manifest_counts: dict[str, int],
    fallback_field_sources: dict[str, str],
    fallback_count_sources: dict[str, str],
) -> dict[str, object]:
    if signal in observed_signals:
        return {
            "signal": signal,
            "status": "pass",
            "field": None,
            "expected": "manually_observed",
            "observed": signal,
            "observed_source": "observed_signals",
        }
    match = _EXIT_CODE_RE.match(signal.strip())
    if match and latest_exit_code is not None:
        expected_code = int(match.group("code"))
        return {
            "signal": signal,
            "status": "pass" if latest_exit_code == expected_code else "fail",
            "field": "exit_code",
            "expected": expected_code,
            "observed": latest_exit_code,
            "observed_source": "exit_code",
        }
    observed_counts_value = {**manifest_counts, **observed_counts(stdout_summary, stderr_summary)}
    match = _REPORTS_ISSUES_RE.match(signal.strip())
    if match:
        expected_issues = int(match.group("issues"))
        observed_issues = observed_counts_value.get("issues")
        observed_source = (
            "stdout_stderr"
            if "issues" in observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("issues")
        )
        return {
            "signal": signal,
            "status": "pass" if observed_issues == expected_issues else "fail",
            "field": "issues",
            "expected": expected_issues,
            "observed": observed_issues,
            "observed_source": observed_source,
        }
    if _REPORTS_CURRENT_ISSUE_COUNT_RE.match(signal.strip()):
        observed_issues = observed_counts_value.get("issues")
        observed_source = (
            "stdout_stderr"
            if "issues" in observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("issues")
        )
        return {
            "signal": signal,
            "status": "pass" if observed_issues is not None else "fail",
            "field": "issues",
            "expected": "present",
            "observed": observed_issues,
            "observed_source": observed_source,
        }
    match = _REPORTS_CHECKED_FILES_GTE_RE.match(signal.strip())
    if match:
        minimum = int(match.group("count"))
        observed_checked_files = observed_counts_value.get("checked_files")
        observed_source = (
            "stdout_stderr"
            if "checked_files" in observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("checked_files")
        )
        return {
            "signal": signal,
            "status": (
                "pass"
                if observed_checked_files is not None and observed_checked_files >= minimum
                else "fail"
            ),
            "field": "checked_files",
            "expected": f">={minimum}",
            "observed": observed_checked_files,
            "observed_source": observed_source,
        }
    if _INCLUDES_CHECKED_FILES_RE.match(signal.strip()):
        observed_checked_files = observed_counts_value.get("checked_files")
        observed_source = (
            "stdout_stderr"
            if "checked_files" in observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("checked_files")
        )
        return {
            "signal": signal,
            "status": "pass" if observed_checked_files is not None else "fail",
            "field": "checked_files",
            "expected": "present",
            "observed": observed_checked_files,
            "observed_source": observed_source,
        }
    stdout_stderr_fields = observed_fields(stdout_summary, stderr_summary)
    observed_fields_value = {**manifest_fields, **stdout_stderr_fields}
    diagnostics_presence = diagnostics_row_presence(stdout_summary, stderr_summary)
    match = _PRINTS_FIELD_RE.match(signal.strip())
    if match:
        field = match.group("field")
        observed_value = observed_fields_value.get(field)
        return {
            "signal": signal,
            "status": "pass" if field in observed_fields_value else "fail",
            "field": field,
            "expected": "present",
            "observed": observed_value,
            "observed_source": (
                "stdout_stderr"
                if field in stdout_stderr_fields
                else fallback_field_sources.get(field)
            ),
        }
    if _PRINTS_PER_SYMBOL_ROWS_RE.match(signal.strip()):
        return {
            "signal": signal,
            "status": (
                "pass"
                if diagnostics_presence["venue_present"]
                and diagnostics_presence["symbol_present"]
                and diagnostics_presence["rows_present"]
                else "fail"
            ),
            "field": "venue,symbol,rows",
            "expected": "present",
            "observed": diagnostics_presence,
            "observed_source": "stdout_stderr",
        }
    normalized_signal = signal.strip()
    if normalized_signal == "required symbols show quote diagnostics coverage":
        return {
            "signal": signal,
            "status": (
                "pass"
                if diagnostics_presence["tradable_rate_present"]
                and diagnostics_presence["stale_rate_present"]
                else "fail"
            ),
            "field": "tradable_rate,stale_rate",
            "expected": "present",
            "observed": diagnostics_presence,
            "observed_source": "stdout_stderr",
        }
    if normalized_signal == "strict validation preview lists current issues":
        issue_previews = issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
        fallback_previews = observed_fields_value.get("phase_gate_issue_previews")
        if not issue_previews and isinstance(fallback_previews, list):
            issue_previews = [str(item) for item in fallback_previews if isinstance(item, str)]
        return {
            "signal": signal,
            "status": "pass" if issue_previews else "fail",
            "field": "phase_gate_issue_previews",
            "expected": "non-empty",
            "observed": issue_previews,
            "observed_source": fallback_field_sources.get("phase_gate_issue_previews"),
        }
    if normalized_signal == "phase gate summary lists blockers":
        blockers = summary.get("blockers")
        normalized_blockers = blockers if isinstance(blockers, list) else []
        if not normalized_blockers:
            fallback_blockers = observed_fields_value.get("blockers")
            if isinstance(fallback_blockers, list):
                normalized_blockers = [str(item) for item in fallback_blockers]
        return {
            "signal": signal,
            "status": "pass" if normalized_blockers else "fail",
            "field": "blockers",
            "expected": "non-empty",
            "observed": normalized_blockers,
            "observed_source": fallback_field_sources.get("blockers"),
        }
    if normalized_signal == "phase gate summary lists next actions":
        next_actions = summary.get("next_actions")
        normalized_next_actions = next_actions if isinstance(next_actions, list) else []
        if not normalized_next_actions:
            fallback_next_actions = observed_fields_value.get("next_actions")
            if isinstance(fallback_next_actions, list):
                normalized_next_actions = [str(item) for item in fallback_next_actions]
        return {
            "signal": signal,
            "status": "pass" if normalized_next_actions else "fail",
            "field": "next_actions",
            "expected": "non-empty",
            "observed": normalized_next_actions,
            "observed_source": fallback_field_sources.get("next_actions"),
        }
    if normalized_signal == "monitoring output shows current balance/fills gap flags":
        balance = observed_fields_value.get("execution_balance_gap_detected")
        fills = observed_fields_value.get("execution_fills_gap_detected")
        return {
            "signal": signal,
            "status": "pass"
            if "execution_balance_gap_detected" in observed_fields_value
            and "execution_fills_gap_detected" in observed_fields_value
            else "fail",
            "field": "execution_balance_gap_detected,execution_fills_gap_detected",
            "expected": "present",
            "observed": {
                "execution_balance_gap_detected": balance,
                "execution_fills_gap_detected": fills,
            },
            "observed_source": {
                "execution_balance_gap_detected": fallback_field_sources.get(
                    "execution_balance_gap_detected"
                ),
                "execution_fills_gap_detected": fallback_field_sources.get(
                    "execution_fills_gap_detected"
                ),
            },
        }
    if normalized_signal == "monitoring output shows current mismatch counts":
        state_count = observed_fields_value.get(
            "execution_drift_overview_state_comparison_mismatching_count"
        )
        snapshot_count = observed_fields_value.get(
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        )
        return {
            "signal": signal,
            "status": (
                "pass"
                if "execution_drift_overview_state_comparison_mismatching_count"
                in observed_fields_value
                and "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
                in observed_fields_value
                else "fail"
            ),
            "field": (
                "execution_drift_overview_state_comparison_mismatching_count,"
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
            ),
            "expected": "present",
            "observed": {
                "execution_drift_overview_state_comparison_mismatching_count": state_count,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": snapshot_count,
            },
            "observed_source": {
                "execution_drift_overview_state_comparison_mismatching_count": fallback_field_sources.get(
                    "execution_drift_overview_state_comparison_mismatching_count"
                ),
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": fallback_field_sources.get(
                    "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
                ),
            },
        }
    if normalized_signal == "phase gate output shows current readiness blockers":
        reason = observed_fields_value.get("phase_gate_reason")
        decision = observed_fields_value.get("phase_gate_decision")
        return {
            "signal": signal,
            "status": "pass"
            if "phase_gate_reason" in observed_fields_value
            or "phase_gate_decision" in observed_fields_value
            else "fail",
            "field": "phase_gate_reason,phase_gate_decision",
            "expected": "present",
            "observed": {
                "phase_gate_reason": reason,
                "phase_gate_decision": decision,
            },
            "observed_source": {
                "phase_gate_reason": fallback_field_sources.get("phase_gate_reason"),
                "phase_gate_decision": fallback_field_sources.get("phase_gate_decision"),
            },
        }
    if normalized_signal == "check-go-no-go prints the current decision and blockers":
        decision = observed_fields_value.get("phase_gate_decision") or observed_fields_value.get(
            "decision"
        )
        reason = observed_fields_value.get("phase_gate_reason") or observed_fields_value.get(
            "phase2_entry_reason"
        )
        blockers = observed_fields_value.get("blockers") or observed_fields_value.get(
            "blocker_count"
        )
        return {
            "signal": signal,
            "status": "pass"
            if decision is not None and (reason is not None or blockers is not None)
            else "fail",
            "field": "decision,reason,blockers",
            "expected": "present",
            "observed": {"decision": decision, "reason": reason, "blockers": blockers},
            "observed_source": {
                "decision": fallback_field_sources.get("phase_gate_decision")
                or fallback_field_sources.get("decision"),
                "reason": fallback_field_sources.get("phase_gate_reason")
                or fallback_field_sources.get("phase2_entry_reason"),
                "blockers": fallback_field_sources.get("blockers")
                or fallback_field_sources.get("blocker_count"),
            },
        }
    if normalized_signal == "current gate decision is visible before regeneration":
        decision = observed_fields_value.get("phase_gate_decision") or observed_fields_value.get(
            "decision"
        )
        return {
            "signal": signal,
            "status": "pass" if decision is not None else "fail",
            "field": "decision",
            "expected": "present",
            "observed": decision,
            "observed_source": fallback_field_sources.get("phase_gate_decision")
            or fallback_field_sources.get("decision"),
        }
    result = evaluate_signal(signal, summary)
    field = result.get("field")
    if isinstance(field, str):
        result["observed_source"] = fallback_field_sources.get(field) or fallback_count_sources.get(
            field
        )
    return result
