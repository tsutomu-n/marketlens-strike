# marketlens-strike

Research-only venue probe for deciding whether `gTrade` and `Ostium` can support
QQQ, SPY, and XAU swing research on 4h to 3d timeframes.

This is not a trading bot. The implementation logs venue data, preserves
raw payload references, builds cost/report artifacts, and blocks short-term
scalping timeframes.

## Setup

```bash
uv sync --dev
uv run sis --help
```

## Current Phase And Handoff Docs

For current project status and handoff interpretation, read these first:

1. [docs/ACCEPTANCE_AUDIT.md](/home/tn/projects/marketlens-strike/docs/ACCEPTANCE_AUDIT.md)
2. [docs/IMPLEMENTATION_STATUS.md](/home/tn/projects/marketlens-strike/docs/IMPLEMENTATION_STATUS.md)
3. [docs/CURRENT_PHASE_STATUS_AND_NEXT_GATE.md](/home/tn/projects/marketlens-strike/docs/CURRENT_PHASE_STATUS_AND_NEXT_GATE.md)
4. [docs/ENGINEERING_HANDOFF_NOTE.md](/home/tn/projects/marketlens-strike/docs/ENGINEERING_HANDOFF_NOTE.md)
5. [docs/PHASE2_COMPLETION_DEFINITION.md](/home/tn/projects/marketlens-strike/docs/PHASE2_COMPLETION_DEFINITION.md)
6. [docs/PHASE_PROGRESSION_CRITERIA.md](/home/tn/projects/marketlens-strike/docs/PHASE_PROGRESSION_CRITERIA.md)

Use them as follows:

- `ACCEPTANCE_AUDIT.md`: current validation state and latest Go/No-Go
- `IMPLEMENTATION_STATUS.md`: what is already implemented in this repo
- `CURRENT_PHASE_STATUS_AND_NEXT_GATE.md`: what phase the repo is operationally in now
- `ENGINEERING_HANDOFF_NOTE.md`: how to interpret the engineering handoff ZIP
- `PHASE2_COMPLETION_DEFINITION.md`: what must be true before Phase 2 is considered complete
- `PHASE_PROGRESSION_CRITERIA.md`: the formal gate for moving from one phase to the next

## Operations And Audit Fast Path

When resuming the repo, use this shortest artifact path first:

1. [docs/ACCEPTANCE_AUDIT.md](/home/tn/projects/marketlens-strike/docs/ACCEPTANCE_AUDIT.md)
2. [docs/IMPLEMENTATION_STATUS.md](/home/tn/projects/marketlens-strike/docs/IMPLEMENTATION_STATUS.md)
3. `data/ops/execution_snapshot_summary.json`
4. `data/ops/execution_venue_comparison_summary.json`
5. `data/ops/execution_gap_history_summary.json`
6. `data/ops/execution_state_comparison_history_summary.json`
7. `data/ops/execution_snapshot_drift_history_summary.json`
8. `data/ops/execution_drift_overview_summary.json`
9. `data/ops/operations_dashboard_summary.json`
10. `data/ops/audit_dashboard_summary.json`
11. `data/ops/operations_bundle_manifest.json`
12. `data/ops/audit_bundle_manifest.json`

If those files are stale or missing, refresh the full operations/audit view with:

```bash
uv run sis refresh-operations-artifacts
```

That refresh also regenerates `data/reports/phase_gate_review.md` and
`data/ops/phase_gate_review_summary.json`.

If you need the shortest Phase 1 gate recheck summary artifact:

```bash
uv run sis phase-gate-review
```

If you need the paper execution path plus all downstream operations/audit artifacts:

```bash
uv run sis paper-operations-cycle
```

That cycle also refreshes the latest phase gate review artifact.

If you want the most compact human-readable restart artifacts, open these next:

- `data/reports/operations_dashboard.md`
- `data/reports/execution_venue_comparison.md`
- `data/reports/execution_gap_history.md`
- `data/reports/execution_state_comparison_history.md`
- `data/reports/execution_snapshot_drift_history.md`
- `data/reports/audit_dashboard.md`
- `data/reports/phase_gate_review.md`
- `data/reports/operations_audit_pack.md`
- `data/reports/paper_operations_runbook.md`
- `data/reports/live_evidence_followup_*.md`

## Command Prefix

Some project notes use `rtk` as a local command wrapper. If `rtk` is unavailable,
run the same command without it.

```bash
rtk uv run pytest
uv run pytest
```

## Main Commands

```bash
uv run sis probe gtrade
uv run sis probe ostium
uv run sis probe ostium --read-only-live
uv run sis probe ostium --read-only-live --pairs-metadata-path data/raw/sidecar/ostium/pairs_YYYY-MM-DD.json
bun run ostium:probe:positions -- --user 0xYourTraderAddress
bun run ostium:probe:positions -- --user ALL --limit 20
uv run sis check-timeframe 1m
uv run sis log-quotes --venue gtrade
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis build-backtest
uv run sis build-backtest --signals-path data/research/signals.csv
uv run sis paper-step
uv run sis paper-report
uv run sis estimate-order --venue gtrade --symbol QQQ --side long
uv run sis balance-status --venue gtrade
uv run sis fill-status --venue gtrade --limit 20
uv run sis execution-snapshot --venue gtrade --fills-limit 5 --order-limit 5
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-gap-history
uv run sis execution-state-comparison-history
uv run sis execution-snapshot-drift-history
uv run sis execution-drift-overview
uv run sis order-status --venue gtrade --order-id ord-1
uv run sis cancel-order --venue gtrade --order-id ord-1
uv run sis close-position --venue ostium --symbol SPY --side long
uv run sis reconcile-positions --venue ostium
uv run sis healthcheck
uv run sis kill-switch --enable --reason manual
uv run sis schedule-run --run-type paper --command "uv run sis paper-step" --every-minutes 30
uv run sis render-alert --level warn --title "Stale" --body "recollect live evidence"
uv run sis weekly-review
uv run sis daemon-manifest --mode paper
uv run sis daemon-dry-run --mode paper --command "uv run sis paper-step" --every-minutes 30
uv run sis export-state
uv run sis restore-state --snapshot-path data/state/state_snapshot.json
uv run sis lifecycle-report
uv run sis monitoring-status
uv run sis comparison-report
uv run sis ops-review
uv run sis operations-dashboard
uv run sis paper-operations-runbook
uv run sis paper-cycle-history
uv run sis operations-bundle
uv run sis operations-timeline
uv run sis operations-audit-pack
uv run sis audit-timeline
uv run sis audit-dashboard
uv run sis audit-bundle
uv run sis audit-bundle-history
uv run sis phase-gate-review
uv run sis refresh-operations-artifacts
uv run sis paper-operations-cycle
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis implementation-status --write
```

## Refresh Live Evidence

Use `--replace` when replaying the current gTrade sidecar into the daily quote
JSONL; ingestion and normalization are idempotent, but replacing the generated
daily quote file avoids carrying rows produced by an older parser.

```bash
bun run gtrade:probe
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
```

The current implementation is complete, but the latest Go/No-Go remains
`CONDITIONAL_GO_NEEDS_LIVE_WINDOW` until collected live evidence satisfies both
`stale_rate` and `tradable_rate` thresholds.

The gTrade sidecar lives in `sidecars/gtrade`:

```bash
cd sidecars/gtrade
bun install
bun run typecheck
bun run probe
```

The Ostium read-only metadata sidecar lives in `sidecars/ostium`:

```bash
cd sidecars/ostium
bun install
bun run typecheck
bun run probe:pairs
bun run probe:positions -- --user 0xYourTraderAddress
```

`sis probe ostium --read-only-live` performs a GET-only Builder API price probe,
writes the resolved registry, preserves the raw price payload, and emits
normalized quote JSONL under `data/raw/quotes/ostium/`.

`bun run ostium:probe:positions -- --user 0xYourTraderAddress` is read-only and
writes `data/raw/sidecar/ostium/positions_*.json`; Go/No-Go uses that artifact
to verify Ostium `liquidationPx` references when real open positions exist.
The SDK also supports `--user ALL --limit N` for a bounded read-only sample
across all traders.

Signal-driven backtests accept CSV files shaped like
`templates/research_signals.template.csv`. When no signal CSV is present,
`build-backtest` uses quote-to-quote virtual execution as a fallback.

The handoff implementation status is tracked in `docs/IMPLEMENTATION_STATUS.md`.
Run `uv run sis implementation-status --write` to refresh it. The latest
acceptance-command audit and remaining live-evidence condition are tracked in
`docs/ACCEPTANCE_AUDIT.md`.

## Source Handoff

The implementation handoff package is preserved under
`docs/sis_venue_probe_handoff/`.
