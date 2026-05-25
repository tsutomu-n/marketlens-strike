# Architecture And Phases

この文書は、現在のコード構成と phase の読み方をまとめます。古い handoff spec は archive にありますが、現行設計の正本ではありません。

## Subsystems

- `sidecars/gtrade`, `sidecars/ostium`: venue read-only collection and metadata sidecars
- `src/sis/storage`: quote normalization and JSON/Parquet persistence
- `src/sis/reports`: generated reports, summaries, dashboards, remediation artifacts
- `src/sis/research`: research market/macro/event/feature/signal artifacts
- `src/sis/backtest`: signal and quote based backtest bridge
- `src/sis/core` and `src/sis/risk`: decision logs, risk gates, halt policies
- `src/sis/paper`: local paper orders, fills, positions, PnL
- `src/sis/execution`: read-only adapter interfaces and local snapshot readers
- `src/sis/ops`: healthcheck, scheduler, alerts, daemon manifests, operation chain
- `scripts`: live evidence runner and scheduling helpers

## Phase Interpretation

Phase は「コードがあるか」だけではなく、再生成可能な artifact と gate で判断します。

- Phase 1: venue evidence and Go/No-Go gate
- Phase 2: research layer artifacts
- Phase 3: decision and backtest integration
- Phase 4: paper trading and operations loop
- Phase 5: read-only execution adapter and reconciliation
- Phase 6: live execution integration
- Phase 7: persistent daemon and external operations integration

現在の repo は Phase 2 以降のコード surface も多く持ちます。ただし Phase 1 の live evidence gate が再確認されるまでは、運用上の進行判断を引き上げません。

## Data Boundaries

- research price と venue execution price は分ける。
- `yfinance` / macro providers は research layer 用で、venue execution price の代替にしない。
- `data/` は runtime artifact であり git 管理外。
- tracked docs は判断導線を説明する。最新 runtime state は generated artifact を読む。

## Execution Boundary

現行 execution adapter は read-only と local artifact aggregation が中心です。

- balance / fills / order status / positions / reconciliation は local snapshot と sidecar を読める。
- `gtrade` positions は `data/paper/positions.parquet` 由来。
- `ostium` positions と balance fallback は positions sidecar 由来。
- live order placement, balance API integration, fill parser integration は未完了。

## Generated Report Chain

主要な generated chain:

```txt
execution snapshot
-> venue comparison
-> venue diagnostics
-> gap/state/drift histories
-> operations dashboard
-> current-state index
-> readiness snapshot
-> phase-gate review
-> remediation chain
```

restart 時は `uv run sis refresh-operations-artifacts` でこの chain を再生成します。

