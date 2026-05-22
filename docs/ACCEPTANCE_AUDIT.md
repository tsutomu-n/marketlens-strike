# Acceptance Audit

Last audited: 2026-05-22

## Result

The handoff implementation is operational, but the full zip goal is not complete until the remaining live-evidence blockers are cleared.

## Passed Acceptance Commands

```bash
rtk uv run sis --help
rtk uv run sis probe gtrade
rtk bun run gtrade:probe
rtk uv run sis log-quotes --venue gtrade
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

- Ostium liquidation reference requires an open-position sidecar from a trader address with real open positions:

```bash
rtk bun run ostium:probe:positions -- --user 0xYourTraderAddress
rtk uv run sis check-go-no-go
```

- Current quote evidence does not satisfy the Go/No-Go stale/tradable thresholds. The quote window must be recollected with sufficient freshness and tradable coverage, then normalized and re-evaluated.

## Current Decision

`CONDITIONAL_GO`
