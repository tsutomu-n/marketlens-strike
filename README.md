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
uv run sis check-timeframe 1m
uv run sis build-cost-matrix
uv run sis check-go-no-go
uv run sis build-evidence-card
```

The gTrade sidecar lives in `sidecars/gtrade`:

```bash
cd sidecars/gtrade
bun install
bun run typecheck
bun run probe
```

`sis probe ostium --read-only-live` performs a GET-only Builder API price probe,
writes the resolved registry, preserves the raw price payload, and emits
normalized quote JSONL under `data/raw/quotes/ostium/`.

## Source Handoff

The implementation handoff package is preserved under
`docs/sis_venue_probe_handoff/`.
