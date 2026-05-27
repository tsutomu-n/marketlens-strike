set shell := ["bash", "-cu"]

check:
    ./scripts/check

refresh-trade-xyz-once:
    uv run sis probe trade-xyz
    uv run sis collect-trade-xyz-quotes
    uv run sis normalize-quotes
    uv run sis build-cost-matrix
    uv run sis build-backtest
    uv run sis check-go-no-go
    uv run sis build-evidence-card

status:
    uv run sis implementation-status
    uv run sis check-go-no-go
