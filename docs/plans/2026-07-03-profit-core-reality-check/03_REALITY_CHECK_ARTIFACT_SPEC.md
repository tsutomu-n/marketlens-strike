<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_10:10 JST
-->

# Reality Check Artifact Spec

## 結論

`profit_core_reality_check.v1` は、既存pipelineの詰まりを読むための read-only artifact です。profit proof、paper permission、live readiness、order permissionではない。

## Schema

```text
schema_version = profit_core_reality_check.v1
```

## Top-level fields

```text
artifact_id
created_at
producer
source_refs
input_paths
summary
candidate_generation
bridge_summary
profit_readiness_summary
risk_review_summary
actual_cash_summary
lineage_summary
blocker_summary
next_single_blocker_to_fix
known_gaps
boundary
```

## Boundary

必ずfalseにする。

```text
paper_execution_allowed=false
live_allowed=false
wallet_allowed=false
signing_allowed=false
exchange_write_allowed=false
production_exchange_write_allowed=false
permits_live_order=false
auto_promote=false
```

## `input_paths`

明示pathだけを保存する。自動探索した場合でも、読んだpathは必ず保存する。

```text
candidate_set_path
search_ledger_path
export_manifest_path
authoring_bridge_path
profit_readiness_inventory_path
source_availability_path
risk_review_path
actual_cash_rows_summary_path
actual_cash_report_gate_path
```

## `summary`

```text
overall_status = COMPLETE | BLOCKED | PARTIAL
next_action = FIX_BLOCKER | COLLECT_INPUTS | RUN_EXISTING_PIPELINE | REVIEW_ONLY | NO_ACTION
candidate_count_total
candidate_count_shortlisted
candidate_count_rejected
bridge_blocked_count
bridge_bridged_count
actual_cash_available_count
known_gap_count
```

## `candidate_generation`

```text
candidate_set_present
search_ledger_present
export_manifest_present
candidate_set_id
candidate_count_total
candidate_count_shortlisted
candidate_count_rejected
trial_count_total
candidate_cap
cap_rejection_count
duplicate_rejection_count
validation_peek_count
rerank_count
sealed_test_used_for_selection
success_only_reporting_detected
shortlisted_family_counts
rejected_family_counts
selection_adjusted_metrics_status_counts
```

Hard blockers:

```text
CANDIDATE_SET_MISSING
SEARCH_LEDGER_MISSING
EXPORT_MANIFEST_MISSING
SUCCESS_ONLY_REPORTING_DETECTED
SEALED_TEST_USED_FOR_SELECTION
```

## `bridge_summary`

```text
bridge_manifest_present
bridge_candidate_count
bridge_bridged_count
bridge_blocked_count
bridge_status_counts
blocked_reason_counts
blocked_by_family
blocked_by_side_bias
blocked_by_symbol
technical_bridged_candidate_ids
blocked_candidate_ids
bridge_success_semantics=technical_only
economic_gate_status=NOT_EVALUATED
actual_cash_result_available=false
```

Hard blockers:

```text
AUTHORING_BRIDGE_MISSING
BRIDGE_ALL_BLOCKED
UNSUPPORTED_FAMILY_DOMINATES
UNSUPPORTED_SIDE_BIAS_DOMINATES
NO_SYMBOL_DATA_DOMINATES
```

Important invariant:

```text
BRIDGED must not imply economic pass.
```

## `profit_readiness_summary`

```text
inventory_present
inventory_status
real_event_count
matured_outcome_count
cash_ledger_count
live_measurement_count
source_availability_present
can_compute_cost_adjusted_estimate
can_compute_actual_cash
source_status_counts
```

Hard blockers:

```text
PROFIT_READINESS_INVENTORY_MISSING
BLOCKED_MISSING_EVENT_OR_OUTCOME
ACTUAL_CASH_SOURCE_MISSING
```

## `risk_review_summary`

```text
risk_review_present
risk_review_status
recommended_action
leader_action
after_cost_edge_over_no_trade_usd
stress_edge_over_no_trade_usd
dollars_per_hour
largest_loss_usd
profit_concentration
actual_cash_available
failed_condition_count
condition_statuses
```

Hard blockers:

```text
RISK_REVIEW_MISSING
BLOCKED_BY_VENUE
INCONCLUSIVE_DATA
KILL
NEEDS_ACTUAL_CASH
```

## `actual_cash_summary`

```text
actual_cash_rows_summary_present
actual_cash_row_count
actual_cash_event_count
action_set
actual_cash_report_gate_present
actual_cash_gate_status
report_actual_cash
fields_missing_for_actual_cash_result_usd
```

Hard blockers:

```text
ACTUAL_CASH_ROWS_MISSING
CASH_LEDGER_MISSING
ASSIGNMENT_MISSING
ACTUAL_CASH_REPORT_GATE_MISSING
NON_ACTUAL_ROWS_REJECTED
```

## `lineage_summary`

```text
lineage_status = COMPLETE | PARTIAL | BROKEN | NOT_APPLICABLE
candidate_id_count
candidate_ids_missing_from_ledger
shortlisted_ids_missing_from_export_manifest
exported_ids_missing_from_bridge
risk_review_candidate_link_status
actual_cash_candidate_link_status
lineage_gaps
```

Lineage must be conservative. If the artifact does not contain a candidate id, record `PARTIAL` or `BROKEN`; do not infer silently.

## `blocker_summary`

```text
blocker_counts
blockers_by_stage
blockers_by_family
top_blockers
next_single_blocker_to_fix
```

`next_single_blocker_to_fix` is deterministic. Use the priority in `02_EXISTING_PIPELINE_TRACE.md`.

## Markdown report

`profit_core_reality_check.md` must include:

1. Overall status.
2. Next single blocker to fix.
3. Candidate generation counts.
4. Bridge status counts.
5. Profit-readiness / risk review status.
6. Actual-cash readiness.
7. Lineage status.
8. Known gaps.
9. Explicit boundary: no permission.

## stdout

```text
network_attempted=false
credentials_used=false
exchange_write_used=false
production_exchange_write_used=false
live_order_submitted=false
permits_live_order=false
status=<complete|blocked|partial>
next_single_blocker_to_fix=<reason>
reality_check_path=<path>
report_path=<path>
known_gap_count=<int>
```

## Validation rules

Pydantic validation must reject:

- permission boundary true.
- `BRIDGED` treated as economic pass without explicit future economic gate artifact.
- `success_only_reporting_detected=false` when selected-only inputs are detected.
- `sealed_test_used_for_selection=true` with status complete.
- actual cash availability inferred from preview / estimate / virtual / dogfood.
- missing candidate-set or search-ledger with status complete.

## Acceptance

The first implementation is accepted when:

1. Minimal candidate-set + search-ledger input creates valid JSON and Markdown.
2. Missing optional artifacts are recorded as missing, not generated.
3. Bridge manifest input creates status counts and blocker counts.
4. Risk review input creates risk status summary.
5. Actual cash rows summary input creates actual-cash summary.
6. All permission boundary fields remain false.
