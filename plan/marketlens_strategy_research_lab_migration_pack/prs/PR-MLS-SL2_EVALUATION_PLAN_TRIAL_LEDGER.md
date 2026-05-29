# PR-MLS-SL2 EvaluationPlan + TrialLedger

## Goal

戦略試行を全て記録し、過剰最適化・best-only採用を防ぐ。

## Files To Add

```text
src/sis/research/strategy_lab/evaluation_plan.py
src/sis/research/strategy_lab/trial_ledger.py
src/sis/research/strategy_lab/evaluation_runner.py
```

## Required Fields

TrialRecord must include:

```text
trial_id
trial_group_id
trial_index
strategy_id
strategy_family
strategy_version
evaluation_plan_id
data_snapshot_id
feature_snapshot_id
parameter_hash
parameter_count
parameter_space_hash
random_seed
git_sha
signal_count
candidate_count
paper_candidate_count
executed_count
blocked_count
no_signal_count
blocked_reason_counts
metrics
baseline_strategy_id
baseline_delta_metrics
selected_for_next_stage
rejection_reasons
profitability_claimed=false
paper_ready_claimed=false
tiny_live_ready_claimed=false
live_ready_claimed=false
```

## Artifacts

```text
data/research/trial_ledger.jsonl
data/reports/strategy_trial_report.md
```

## Tests

```text
- every trial appends ledger row
- parameter_hash stable
- selected trial still records non-selected trials
- live_ready_claimed cannot be true
- missing data_snapshot_id fails
```

## Done

```text
uv run sis evaluate-strategy-lab --spec ... --evaluation-plan ...
```
