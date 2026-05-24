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
uv run sis build-backtest
uv run sis build-backtest --signals-path data/research/signals.csv
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
