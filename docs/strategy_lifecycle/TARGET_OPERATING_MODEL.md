<!--
作成日: 2026-06-11_21:34 JST
更新日: 2026-06-12_01:16 JST
-->

# Target Operating Model

## 結論

Strategy Lifecycle の実務ゴールは、戦略を live に飛ばすことではなく、次の段階へ進めてよいかを artifact で判定することです。

## Standard Flow

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-paper-observation-cycle --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run sis phase-gate-review
uv run sis strategy-lifecycle-review --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

## Decision Ladder

- `REJECT_OR_REVISE`: backtest failed, paper observation stopped, or the strategy should be revised.
- `CONTINUE_RESEARCH`: required research or backtest artifacts are missing.
- `BACKTEST_ACCEPTED`: backtest acceptance passed, but paper observation review is not present yet.
- `CONTINUE_PAPER_OBSERVATION`: paper observation is not sufficient yet.
- `CONTINUE_EXECUTION_READINESS`: paper observation passed, but phase gate or execution-readiness blockers remain.
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN`: backtest, paper observation, and current gate evidence allow a separate live canary plan to be written.
- `BLOCKED_BOUNDARY_VIOLATION`: prohibited live, wallet, credential, or exchange-write side effect appeared in artifacts.

## Source Artifacts

- Strategy Authoring metrics: `data/research/strategy_backtest_metrics.json`
- Backtest acceptance: `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- Paper observation session manifest: `data/paper/observations/<session_id>/paper_observation_session_manifest.json`
- Paper observation session ledger: `data/paper/observations/<session_id>/paper_observation_ledger.jsonl`
- Paper observation review: `data/research/ndx/paper_observation_review_decision.json`
- Phase gate: `data/ops/phase_gate_review_summary.json`

## Boundary

`READ_ONLY_GO` is a read-only / paper gate signal. It is not production live readiness.

`ELIGIBLE_FOR_LIVE_CANARY_PLAN` does not permit live orders. A separate plan must still cover credentials, wallet/signing, venue write probes, operator controls, kill switch, and live risk limits.

`strategy-paper-observation-cycle --smoke` は local verification 用の短縮閾値です。smoke で得た pass は production paper pass ではありません。
