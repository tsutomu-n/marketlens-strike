#!/usr/bin/env bash
set -euo pipefail

DURATION_MINUTES="${1:-120}"
METADATA_INTERVAL_SECONDS="${2:-60}"

cd "$(dirname "$0")/.."

cd sidecars/gtrade
bun run collect:window -- --duration-minutes "${DURATION_MINUTES}" --metadata-interval-seconds "${METADATA_INTERVAL_SECONDS}"
cd ../..

uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis diagnose-quotes
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis validate-artifacts --strict
