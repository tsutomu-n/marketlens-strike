<!--
作成日: 2026-06-11_19:06 JST
更新日: 2026-06-11_19:06 JST
-->

# NDX Layer 2.8 Paper Observation Review

Layer 2.8 aggregates the local paper observation ledger after Layer 2.7 operator promotion. It decides whether the observation window has passed, needs more paper fills, or must stop. It does not permit live orders.

## Command

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
```

Default thresholds:

- `--min-fills-for-pass 20`
- `--max-blocked-rate 0.5`
- `--max-consecutive-blocked 3`
- `--paper-notional-usd 1000.0`

For a short local fixture check, lower the fill threshold explicitly:

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --min-fills-for-pass 1
```

## Inputs

- `data/research/ndx/operator_promotion_decision.json`
- `data/research/ndx/paper_observation_gate_decision.json`
- `data/paper/paper_observation_ledger.jsonl`
- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`

## Outputs

- `data/research/ndx/paper_observation_review_decision.json`
- `data/reports/ndx_paper_observation_review_report.md`

Schema:

- `schemas/ndx_paper_observation_review_decision.v1.schema.json`

## Decisions

- `PASS_PAPER_OBSERVATION_REVIEW`: fill threshold met with no review blocker.
- `NEEDS_MORE_PAPER_OBSERVATION`: no blocker, but fill threshold is not met.
- `STOP_PAPER_OBSERVATION`: boundary or operational stop condition was hit.

Stop conditions:

- any ledger entry has `live_order_submitted`, `wallet_used`, or `exchange_write_used` not exactly `false`
- unknown ledger status
- blocked rate is greater than `--max-blocked-rate`
- consecutive blocked entries reach `--max-consecutive-blocked`
- required paper artifacts are missing

## Boundary

Layer 2.8 is paper-only review. It verifies local paper artifacts and records hashes, but it is not alpha proof, robust out-of-sample proof, exchange connectivity proof, account readiness, wallet readiness, or live readiness. A passing Layer 2.8 decision still keeps `permits_live_order=false` and `live_conversion_allowed=false`.
