<!--
作成日: 2026-06-11_21:34 JST
更新日: 2026-06-15_18:42 JST
-->

# Strategy Lifecycle

## 結論

Strategy Lifecycle は、Strategy Authoring backtest、paper observation、phase gate を local artifact でつなぎ、次の実務判断を出すための control plane です。

これは live trading 実装ではありません。`ELIGIBLE_FOR_LIVE_CANARY_PLAN` は、別計画として live canary plan を書いてよい候補という意味だけで、live order、wallet、signing、exchange write を許可しません。

## Commands

```bash
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-paper-observation-cycle --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run sis strategy-lifecycle-review --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

## Artifacts

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_acceptance_report.md`
- `data/paper/observations/<session_id>/paper_observation_session_manifest.json`
- `data/paper/observations/<session_id>/paper_observation_ledger.jsonl`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/reports/strategy_lifecycle_review.md`

## Read Order

1. `TARGET_OPERATING_MODEL.md`
2. `PAPER_OBSERVATION_CYCLE.md`
3. `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md`
4. `LIVE_CANARY_PLAN_GATE.md`
5. `docs/backtest/README.md`
6. `docs/research/ndx/README.md`
7. `docs/OPERATIONS_RUNBOOK.md`

## Boundary

`strategy-lifecycle-review` は既存の `lifecycle-report` とは別物です。`lifecycle-report` は operations / recovery report で、Strategy Lifecycle の promotion 判定ではありません。

どの decision でも `permits_live_order=false`, `live_conversion_allowed=false`, `wallet_used=false`, `venue_write_used=false`, `exchange_write_used=false` を維持します。
