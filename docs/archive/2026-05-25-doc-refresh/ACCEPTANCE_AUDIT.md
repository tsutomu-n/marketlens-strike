# Acceptance Audit

Last audited: 2026-05-22

## Result

The handoff implementation is operational. The current Go/No-Go remains conditional until live quote evidence clears the remaining threshold blockers.

## Command Prefix

This repository may show examples with `rtk`. If `rtk` is unavailable, run the same command without it.

Example: `rtk uv run pytest` = `uv run pytest`.

## Latest Verification Snapshot

- Latest full Python verification: `rtk uv run pytest` -> 44 passed.
- Latest Python lint verification: `rtk uv run ruff check .` -> passed.
- Latest sidecar verification: `rtk bun run gtrade:typecheck && rtk bun run gtrade:test && rtk bun run ostium:typecheck && rtk bun run ostium:test` -> passed.
- Latest live-evidence refresh command chain: `rtk bun run gtrade:probe && rtk uv run sis log-quotes --venue gtrade --replace && rtk uv run sis normalize-quotes && rtk uv run sis build-cost-matrix && rtk uv run sis build-backtest && rtk uv run sis check-go-no-go && rtk uv run sis build-evidence-card`.
- Latest Go/No-Go decision: `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`.

## Passed Acceptance Commands

```bash
rtk uv run sis --help
rtk uv run sis probe gtrade
rtk bun run gtrade:probe
rtk uv run sis log-quotes --venue gtrade
rtk uv run sis log-quotes --venue gtrade --replace
rtk uv run sis normalize-quotes
rtk uv run sis build-cost-matrix
rtk uv run sis build-backtest
rtk uv run sis check-go-no-go
rtk uv run sis build-evidence-card
rtk uv run sis check-timeframe 1m
rtk uv run sis check-timeframe 5m
rtk bun run ostium:probe:pairs
rtk uv run pytest
rtk uv run ruff check .
rtk bun run gtrade:typecheck
rtk bun run gtrade:test
rtk bun run ostium:typecheck
rtk bun run ostium:test
```

## Verified Artifacts

- `data/registry/gtrade_instrument_registry.json`
- `data/registry/ostium_instrument_registry.json`
- `data/raw/quotes/gtrade/YYYY-MM-DD.jsonl`
- `data/raw/quotes/ostium/YYYY-MM-DD.jsonl`
- `data/normalized/quotes.parquet`
- `data/normalized/sis.duckdb`
- `data/research/venue_cost_matrix.csv`
- `data/research/backtest_report.md`
- `data/research/backtest_metrics.json`
- `data/research/go_no_go_report.md`
- `data/evidence/evidence_card_*.json`

## Remaining Blockers

- Current quote evidence does not satisfy the Go/No-Go `stale_rate` threshold. gTrade rows now preserve the venue `lastRefreshed` timestamp as `oracle_ts_ms`, and the latest captured window is stale against the current threshold.
- Current quote evidence does not satisfy the Go/No-Go `tradable_rate` threshold. The quote window must be recollected during tradable sessions, then normalized and re-evaluated.

## Refresh Command

```bash
rtk bun run gtrade:probe
rtk uv run sis log-quotes --venue gtrade --replace
rtk uv run sis normalize-quotes
rtk uv run sis build-cost-matrix
rtk uv run sis build-backtest
rtk uv run sis check-go-no-go
rtk uv run sis build-evidence-card
```

## Current Decision

`CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
