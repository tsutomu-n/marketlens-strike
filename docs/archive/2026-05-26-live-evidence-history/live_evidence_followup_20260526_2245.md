# Live Evidence Follow-up

## Current State

- run_status: `failed_collection`
- decision: `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- markdown_report: `docs/live_evidence_reports/live_evidence_report_20260526_2245.md`
- html_report: `docs/live_evidence_reports/live_evidence_report_20260526_2245.html`
- manifest_path: `logs/live_evidence/manifests/live_evidence_20260526_2245.json`

## Quick Navigation

- live_evidence_followup_report: `docs/live_evidence_reports/live_evidence_followup_20260526_2245.md`
- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_20260526_2245.md`
- current_state_index_report: `docs/live_evidence_reports/current_state_index.md`
- readiness_snapshot_report: `docs/live_evidence_reports/readiness_snapshot.md`
- phase_gate_review_report: `data/reports/phase_gate_review.md`
- remediation_scoreboard_report: `docs/live_evidence_reports/remediation_scoreboard.md`

## Related Reports

- live_evidence_followup_report: `docs/live_evidence_reports/live_evidence_followup_20260526_2245.md`
- live_evidence_report: `docs/live_evidence_reports/live_evidence_report_20260526_2245.md`
- operations_dashboard_report: `docs/live_evidence_reports/operations_dashboard.md`
- ops_review_report: `docs/live_evidence_reports/ops_review.md`
- current_state_index_report: `docs/live_evidence_reports/current_state_index.md`
- readiness_snapshot_report: `docs/live_evidence_reports/readiness_snapshot.md`
- phase_gate_review_report: `data/reports/phase_gate_review.md`
- paper_operations_runbook_report: `docs/live_evidence_reports/paper_operations_runbook.md`
- go_no_go_report: `data/research/go_no_go_report.md`
- paper_vs_backtest_comparison_report: `docs/live_evidence_reports/paper_vs_backtest_comparison.md`

## Audit Summary

- overall_status: `degraded`
- latest_operation: `audit_bundle_snapshot`
- bundle_history_snapshot_count: `2`

## Phase Gate Summary

- decision: `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- phase2_entry_allowed: `False`
- phase_gate_reason: `remain_in_phase1_until_live_evidence_gate_clears`
- strict_validation_passed: `True`
- phase_gate_strict_validation_issue_count: `0`
- phase_gate_checked_files: `14`

## Readiness Summary

- next_phase_candidate: `Stay Phase 1`
- execution_ready: `False`

## Latest Execution Lineage

- timeline_latest_execution_overall_status: `None`
- timeline_latest_execution_venue_count: `None`
- timeline_latest_execution_comparison_all_registries_present: `None`
- bundle_history_latest_execution_overall_status: `None`
- bundle_history_latest_execution_venue_count: `None`
- bundle_history_latest_execution_comparison_all_registries_present: `None`
- cycle_history_latest_execution_overall_status: `None`
- cycle_history_latest_execution_venue_count: `None`
- cycle_history_latest_execution_comparison_all_registries_present: `None`

## Execution Snapshot

- overall_status: `ok`
- venue_count: `2`
- report_path: `data/reports/execution_snapshot.md`

## Execution Venue Comparison

- all_registries_present: `True`
- report_path: `data/reports/execution_venue_comparison.md`

## Execution Venue Diagnostics

- overall_status: `degraded`
- balance_gap_detected: `True`
- fills_gap_detected: `True`
- report_path: `data/reports/execution_venue_diagnostics.md`

## Execution Gap History

- entry_count: `9`
- latest_status: `degraded`
- latest_execution_diagnostics_status: `degraded`
- report_path: `data/reports/execution_gap_history.md`

## Execution State Comparison History

- entry_count: `6`
- latest_status_match: `True`
- mismatching_count: `3`
- report_path: `data/reports/execution_state_comparison_history.md`

## Execution Snapshot Drift History

- entry_count: `6`
- latest_execution_state_comparison_status_match: `False`
- mismatching_snapshot_count: `3`
- report_path: `data/reports/execution_snapshot_drift_history.md`

## Execution Drift Overview

- overall_status: `degraded`
- diagnostics_alignment_match: `True`
- state_comparison_mismatching_count: `3`
- snapshot_drift_mismatching_snapshot_count: `3`

## Immediate Next Work

- inspect the failure point in the log tail and fix the first blocking error before rerunning

## Log Tail

```text

[2026-05-26T13:45:00Z] Scheduled live evidence run starting
error: Script not found "gtrade:collect-window"
error: Script not found "gtrade:collect-window"
error: Script not found "gtrade:collect-window"
```
