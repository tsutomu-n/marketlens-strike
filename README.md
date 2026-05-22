# marketlens-strike

Research-only venue probe for deciding whether `gTrade` and `Ostium` can support
QQQ, SPY, and XAU swing research on 4h to 3d timeframes.

This is not a trading bot. The initial implementation logs venue data, preserves
raw payload references, builds cost/report artifacts, and blocks short-term
scalping timeframes.

## Setup

```bash
uv sync --dev
uv run sis --help
```

## Main Commands

```bash
uv run sis probe gtrade
uv run sis probe ostium
uv run sis probe ostium --read-only-live
uv run sis probe ostium --read-only-live --pairs-metadata-path data/raw/sidecar/ostium/pairs_YYYY-MM-DD.json
uv run sis check-timeframe 1m
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis implementation-status --write
```

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
```

`sis probe ostium --read-only-live` performs a GET-only Builder API price probe,
writes the resolved registry, preserves the raw price payload, and emits
normalized quote JSONL under `data/raw/quotes/ostium/`.

The handoff zip is not fully implemented yet. Run
`uv run sis implementation-status --write` to refresh `docs/IMPLEMENTATION_STATUS.md`.

## Source Handoff

The implementation handoff package is preserved under
`docs/sis_venue_probe_handoff/`.
