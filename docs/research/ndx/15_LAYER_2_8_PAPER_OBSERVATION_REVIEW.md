<!--
作成日: 2026-06-11_19:06 JST
更新日: 2026-06-17_23:19 JST
-->

# NDX Layer 2.8 Paper Observation Review

Layer 2.8 aggregates the local paper observation ledger after Layer 2.7 operator promotion. It decides whether the observation window has passed, needs more paper fills, or must stop. It does not permit live orders.

## Command

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --ledger-path data/paper/observations/<session>.jsonl
```

Session manifest input:

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-manifest data/paper/observations/<session_id>/paper_observation_session_manifest.json
```

Default thresholds:

- `--min-fills-for-pass 20`
- `--min-trading-days-for-pass 10`
- `--max-blocked-rate 0.5`
- `--max-consecutive-blocked 3`
- `--max-open-position-age-hours 0.0`
- `--paper-notional-usd 1000.0`

For a short local fixture check, lower the fill threshold explicitly:

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --min-fills-for-pass 1 \
  --min-trading-days-for-pass 1
```

## Inputs

- `data/research/ndx/operator_promotion_decision.json`
- `data/research/ndx/paper_observation_gate_decision.json`
- `data/paper/paper_observation_ledger.jsonl`
- or an explicit ledger created by `paper-from-intents --observation-ledger-path`
- or a session manifest created by `strategy-paper-observation-cycle`
- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`

## Outputs

- `data/research/ndx/paper_observation_review_decision.json`
- `data/reports/ndx_paper_observation_review_report.md`

Schema:

- `schemas/ndx_paper_observation_review_decision.v1.schema.json`

## Strategy Lifecycle Handoff

Layer 2.8 の decision artifact は Strategy Lifecycle の paper observation input です。Layer 2.8 が pass しても、この文書内で live canary や live order に進めない。

Layer 2.8 後の統合判定:

```bash
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --paper-review-path data/research/ndx/paper_observation_review_decision.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

通常 paper observation が足りているかの読み戻し:

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --canonical-review-path data/research/ndx/paper_observation_review_decision.json \
  --lifecycle-review-path data/research/strategy_lifecycle/strategy_lifecycle_review.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

Strategy Lifecycle の詳細は [docs/strategy_lifecycle/README.md](../../strategy_lifecycle/README.md) を読む。`ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live order 許可ではなく、別計画として live canary plan を書ける候補に限る。

## Decisions

- `PASS_PAPER_OBSERVATION_REVIEW`: fill and trading-day thresholds met with no review blocker and complete timestamps.
- `NEEDS_MORE_PAPER_OBSERVATION`: no blocker, but fill threshold, trading-day threshold, or timestamp completeness is not met.
- `STOP_PAPER_OBSERVATION`: boundary or operational stop condition was hit.

Stop conditions:

- any ledger entry has `live_order_submitted`, `wallet_used`, `venue_write_used`, or `exchange_write_used` not exactly `false`
- unknown ledger status
- blocked rate is greater than `--max-blocked-rate`
- consecutive blocked entries reach `--max-consecutive-blocked`
- required paper artifacts are missing
- open position age is greater than `--max-open-position-age-hours` when that option is greater than zero

## Boundary

Layer 2.8 is paper-only review. It verifies local paper artifacts and records hashes, but it is not alpha proof, robust out-of-sample proof, exchange connectivity proof, account readiness, wallet readiness, or live readiness. A passing Layer 2.8 decision still keeps `permits_live_order=false` and `live_conversion_allowed=false`.

When `--session-manifest` is used, the manifest's ledger path and thresholds are used. The decision artifact records `source_paper_observation_session_manifest_path` and `source_paper_observation_session_manifest_hash`. Manifest / ledger / operator-promotion hash mismatch fails closed.
