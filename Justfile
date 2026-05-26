set shell := ["bash", "-cu"]

check:
    ./scripts/check

probe-gtrade-vars:
    cd sidecars/gtrade && bun run probe

probe-ostium:
    cd sidecars/ostium && bun run probe:pairs
    uv run sis probe ostium --read-only-live

refresh-gtrade-once:
    cd sidecars/gtrade && bun run probe
    uv run sis log-quotes --venue gtrade --replace
    uv run sis normalize-quotes
    uv run sis build-cost-matrix
    uv run sis build-backtest
    uv run sis check-go-no-go
    uv run sis build-evidence-card

collect-gtrade-window:
    cd sidecars/gtrade && bun run collect:window -- --duration-minutes 120 --metadata-interval-seconds 60

status:
    uv run sis implementation-status
    uv run sis check-go-no-go
