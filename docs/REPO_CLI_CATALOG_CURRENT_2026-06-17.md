<!--
作成日: 2026-06-17_22:40 JST
更新日: 2026-06-28_09:45 JST
-->

# Repo CLI Catalog Current

この文書は、`sis` の public CLI command catalog です。`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` から command list を分離し、capability overview と CLI catalog の更新単位を分けます。

正本は `src/sis/cli.py` と各 `src/sis/commands/` registration です。この文書の command bullet は `uv run python scripts/check_cli_catalog.py` で Typer 登録 command と照合します。

## 検証方法

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
```

固定の command count は current truth ではありません。確認時は上の command を再実行してください。

## Public CLI Command Catalog

### Research / NDX

- `research-dag-validate`
- `research-dag-export`
- `research-layer22-validate`
- `research-layer22-export`
- `research-layer22-review-pack`
- `research-layer22-review-import`
- `research-layer22-exit-gate`
- `research-ndx-source-resolve`
- `research-ndx-feature-panel`
- `research-ndx-residual`
- `research-ndx-diagnostics`
- `research-ndx-residual-validate`
- `research-ndx-strategy-lab-export`
- `research-ndx-paper-observation-gate`
- `research-ndx-operator-promotion`
- `research-ndx-paper-observation-review`

### Strategy Lab / Strategy Authoring / Lifecycle

- `strategy-preview`
- `strategy-experiment-run`
- `evaluate-strategy-lab`
- `build-paper-candidate-pack`
- `promotion-decision`
- `build-paper-intent-preview`
- `check-research-quality`
- `strategy-author-init`
- `strategy-author-validate`
- `strategy-author-explain`
- `strategy-author-run`
- `strategy-author-bundle-run`
- `strategy-author-train-model`
- `strategy-input-contract-validate`
- `strategy-input-feedback-proposal-build`
- `strategy-input-feedback-proposal-review`
- `strategy-intake-validate`
- `strategy-stage-policy-validate`
- `strategy-stage-decision`
- `strategy-paper-smoke-plan`
- `strategy-runtime-observation-ingest`
- `strategy-drift-review`
- `strategy-learning-ledger-update`
- `strategy-revision-request-build`
- `strategy-revision-request-review`
- `strategy-authoring-update-handoff`
- `strategy-case-lite-update`
- `strategy-case-index-build`
- `strategy-daily-brief`
- `strategy-ai-review-packet-build`
- `strategy-ai-review-note-record`
- `strategy-ai-review-findings-structure`
- `strategy-idea-candidates-build`
- `strategy-idea-candidates-ai-packet-build`
- `strategy-idea-candidates-ai-import`
- `strategy-idea-candidates-perp-estimate`
- `strategy-model-run-record`
- `strategy-micro-live-plan`
- `strategy-next-scale-plan`
- `strategy-live-observation-ingest`
- `strategy-scale-decision`
- `strategy-workbench-viewer-build`
- `strategy-backtest-acceptance`
- `strategy-lifecycle-review`
- `strategy-paper-observation-cycle`
- `strategy-paper-observation-append`
- `strategy-paper-observation-status`

### Backtest / Strategy Review

- `strategy-backtest-suite`
- `strategy-backtest-compare`
- `strategy-backtest-data-availability`
- `strategy-backtest-baseline-compare`
- `strategy-backtest-no-lookahead-diff`
- `strategy-backtest-execution-sim`
- `strategy-backtest-assumption-ledger`
- `strategy-backtest-trial-ledger`
- `strategy-backtest-portfolio-compare`
- `strategy-backtest-metric-extension`
- `strategy-backtest-report-extension`
- `strategy-backtest-html-report`
- `strategy-backtest-stress`
- `strategy-backtest-regime-split`
- `strategy-backtest-rolling-stability`
- `strategy-backtest-benchmark-relative`
- `strategy-backtest-adapter-spike`
- `strategy-backtest-external-run`
- `strategy-backtest-framework-run`
- `strategy-backtest-microstructure-readiness`
- `strategy-backtest-qstrader-contract`
- `strategy-backtest-portfolio-validation-contract`
- `strategy-backtest-pybroker-contract`
- `strategy-backtest-constraint-breaker-decision`
- `strategy-backtest-framework-smoke`
- `strategy-backtest-adapter-selection`
- `strategy-backtest-adapter-contract`
- `strategy-backtest-pack`
- `strategy-backtest-pack-validate`
- `strategy-backtest-artifact-summary`
- `strategy-review-build`
- `strategy-review-record`

### Crypto Perp Truth-Cycle MVP

- `crypto-perp-config-validate`
- `crypto-perp-probe`
- `crypto-perp-probe-audit`
- `crypto-perp-raw-refresh`
- `crypto-perp-refresh`
- `crypto-perp-watchdeck`
- `crypto-perp-decision-record`
- `crypto-perp-outcome-record`
- `crypto-perp-account-probe`
- `crypto-perp-order-preview`
- `crypto-perp-profit-readiness-inventory`
- `crypto-perp-profit-readiness-plan`
- `crypto-perp-profit-readiness-run-local`
- `crypto-perp-source-availability`
- `crypto-perp-replay-slice`
- `crypto-perp-feature-pack`
- `crypto-perp-edge-score`
- `crypto-perp-tournament-rows-v2`
- `crypto-perp-bias-guard`
- `crypto-perp-cash-ledger`
- `crypto-perp-actual-cash-rows-build`
- `crypto-perp-actual-cash-report-gate`
- `crypto-perp-tiny-live-review-packet`
- `crypto-perp-tiny-live-shadow-readiness`
- `crypto-perp-tiny-live-shadow`
- `crypto-perp-tiny-live-measurement`
- `crypto-perp-tournament-gate`
- `crypto-perp-tournament-report`
- `crypto-perp-tournament-rows-preview`
- `crypto-perp-truth-cycle-dogfood-pack`
- `crypto-perp-truth-cycle-status`

M10 の cash ledger、execution replay、calibration と M11 の Workbench bridge は Python/schema artifact surface です。M11 の hypothesis tournament は `crypto-perp-tournament-report` で同一event setのactual cash比較reportを生成できます。profit-readiness 追加層は `crypto-perp-profit-readiness-inventory`、`crypto-perp-profit-readiness-plan`、`crypto-perp-profit-readiness-run-local`、`crypto-perp-source-availability`、`crypto-perp-replay-slice`、`crypto-perp-feature-pack`、`crypto-perp-edge-score`、`crypto-perp-tournament-rows-v2`、`crypto-perp-bias-guard`、`crypto-perp-cash-ledger`、`crypto-perp-actual-cash-rows-build`、`crypto-perp-actual-cash-report-gate`、`crypto-perp-tiny-live-review-packet`、`crypto-perp-tiny-live-shadow-readiness`、`crypto-perp-tiny-live-shadow` で local artifact を作ります。`crypto-perp-tournament-gate` は report を読んで next action を分けるlocal gateであり、live order permissionではありません。`crypto-perp-truth-cycle-status` は既存artifactから次に欠けているlocal stepとstop reasonを出すだけで、network / order / live permissionではありません。`crypto-perp-truth-cycle-dogfood-pack` は fixture-only の status / Daily Brief / Workbench Viewer pack を生成するlocal確認入口です。

### Trade[XYZ] / Quotes / Data Readiness

- `collect-trade-xyz-ws`
- `build-trade-xyz-ws-quality`
- `build-trade-xyz-rest-parity`
- `collect-trade-xyz-quotes`
- `collect-trade-xyz-data-cycle`
- `normalize-quotes`
- `normalize-trade-xyz-ws-quotes`
- `build-trade-xyz-quote-coverage`
- `build-trade-xyz-reference-data`
- `collect-trade-xyz-real-market-reference`
- `collect-trade-xyz-signal-candles`
- `collect-trade-xyz-account-fee`
- `collect-trade-xyz-historical-l2-archive`
- `collect-trade-xyz-historical-asset-ctxs-archive`
- `normalize-trade-xyz-historical-archive-quotes`
- `plan-trade-xyz-historical-archive-bulk`
- `check-trade-xyz-historical-archive-preflight`
- `execute-trade-xyz-historical-archive-bulk`
- `normalize-trade-xyz-historical-archive-bulk`
- `build-trade-xyz-session-state`
- `collect-trade-xyz-funding-history`
- `build-trade-xyz-funding-events-from-history`
- `build-trade-xyz-data-readiness`
- `trade-xyz-collection-status`
- `build-trade-xyz-data-bundle`
- `probe`

### Research Data / Feature Build

- `build-cost-matrix`
- `ingest-research-data`
- `build-event-calendar`
- `build-feature-panel`
- `build-signals`
- `alpaca-smoke`

### Execution / Paper / Bot

- `bot-preview`
- `execution-snapshot`
- `execution-venue-comparison`
- `execution-venue-diagnostics`
- `execution-read-only-surfaces`
- `order-status`
- `estimate-order`
- `balance-status`
- `bitget-demo-smoke`
- `venue-read-only-probe`
- `fill-status`
- `cancel-order`
- `close-position`
- `reconcile-positions`
- `healthcheck`
- `paper-step`
- `paper-from-intents`
- `paper-report`
- `paper-operations-cycle`

### Operations / Audit / Remediation / Runtime

- `daemon-manifest`
- `daemon-dry-run`
- `daemon-run`
- `export-state`
- `restore-state`
- `monitoring-status`
- `kill-switch`
- `schedule-run`
- `render-alert`
- `notification-outbox`
- `lifecycle-report`
- `comparison-report`
- `ops-review`
- `operations-dashboard`
- `paper-operations-runbook`
- `paper-cycle-history`
- `execution-gap-history`
- `execution-state-comparison-history`
- `execution-snapshot-drift-history`
- `execution-drift-overview`
- `phase-gate-review`
- `operations-bundle`
- `operations-timeline`
- `operations-audit-pack`
- `audit-timeline`
- `audit-dashboard`
- `audit-bundle`
- `audit-bundle-history`
- `current-state-index`
- `readiness-snapshot`
- `remediation-planner`
- `remediation-execution-plan`
- `remediation-session`
- `remediation-session-checkpoint`
- `remediation-evidence-ingest`
- `remediation-scoreboard`
- `remediation-evaluator`
- `remediation-evidence`
- `remediation-command-results`
- `weekly-review`
- `refresh-operations-artifacts`
- `build-backtest`
- `check-halt-policy`
- `check-go-no-go`
- `build-evidence-card`
- `implementation-status`
- `check-timeframe`
- `market-session`
- `next-live-window`
- `validate-artifacts`
- `diagnose-quotes`
