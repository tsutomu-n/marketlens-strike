<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_13:26 JST
-->

# Existing Pipeline Trace

## 結論

`profit_core_reality_check` は既存artifactを読むだけのsummaryです。新しい探索、外部通信、注文、runtime artifact生成はしない。

## 現行chain

```text
source root
-> input contract validation
-> strategy-idea-candidates-build
-> candidate set / search ledger / export manifest
-> strategy-idea-candidates-authoring-bridge
-> bridge manifest / bridge blockers
-> optional Crypto Perp review artifacts
```

## 読むartifact

### Candidate generation

```text
strategy_idea_candidate_set.json
search_ledger.jsonl
selection_metrics.json
perp_cost_estimates.json
split_materialization.json
strategy_idea_candidate_export_manifest.json
```

集計field:

```text
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
shortlisted_family_counts
rejected_family_counts
```

blocker:

```text
CANDIDATE_SET_MISSING
SEARCH_LEDGER_MISSING
EXPORT_MANIFEST_MISSING
SUCCESS_ONLY_REPORTING_DETECTED
SEALED_TEST_USED_FOR_SELECTION
NO_SHORTLISTED_CANDIDATES
```

### Authoring bridge

```text
strategy_idea_candidate_authoring_bridge_manifest.json
```

集計field:

```text
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
```

blocker:

```text
AUTHORING_BRIDGE_MISSING
BRIDGE_ALL_BLOCKED
BRIDGED_TECHNICAL_ONLY
UNSUPPORTED_FAMILY_DOMINATES
UNSUPPORTED_SIDE_BIAS_DOMINATES
NO_SYMBOL_DATA_DOMINATES
```

`BRIDGED` はtechnical bridgeだけを意味する。economic passではない。

### Profit-readiness and review artifacts

任意入力として次を読む。

```text
profit_readiness_inventory.json
source_availability.json
risk_taker_review.json
actual_cash_rows_summary.json
actual_cash_report_gate manifest
```

集計field:

```text
inventory_status
real_event_count
matured_outcome_count
review_status
recommended_action
leader_action
actual_cash_available
actual_cash_row_count
gate_status
known_gap_count
```

blocker:

```text
BLOCKED_MISSING_EVENT_OR_OUTCOME
SOURCE_AVAILABILITY_MISSING
ACTUAL_CASH_SOURCE_MISSING
RISK_REVIEW_MISSING
NEEDS_ACTUAL_CASH
ACTUAL_CASH_ROWS_MISSING
ACTUAL_CASH_REPORT_GATE_MISSING
```

## Lineage Trace

最低限追跡するkey:

```text
candidate_id
candidate_set_id
candidate_set_sha256
search_ledger_sha256
export_manifest_sha256
bridge_manifest_sha256
bridge_candidate_status
risk_review_id
row_set_id
actual_cash_rows_summary_id
actual_cash_gate_id
```

lineage status:

```text
COMPLETE
PARTIAL
BROKEN
NOT_APPLICABLE
```

## Next blocker priority

`next_single_blocker_to_fix` は次の優先順で1つ選ぶ。

```text
SEARCH_LEDGER_MISSING
SUCCESS_ONLY_REPORTING_DETECTED
SEALED_TEST_USED_FOR_SELECTION
AUTHORING_BRIDGE_MISSING
UNSUPPORTED_FAMILY_DOMINATES
UNSUPPORTED_SIDE_BIAS_DOMINATES
NO_SYMBOL_DATA_DOMINATES
MISSING_SOURCE_COLUMNS_DOMINATES
PROFIT_READINESS_INVENTORY_MISSING
BLOCKED_MISSING_EVENT_OR_OUTCOME
ACTUAL_CASH_SOURCE_MISSING
BRIDGED_TECHNICAL_ONLY
RISK_REVIEW_MISSING
NEEDS_ACTUAL_CASH
ACTUAL_CASH_ROWS_MISSING
ACTUAL_CASH_REPORT_GATE_MISSING
NO_BLOCKER_IDENTIFIED
```

## 実装注意

初期実装はmissing artifactを作らない。明示pathで渡されたartifactを読み、集計して止める。
