#!/usr/bin/env bash
set -euo pipefail

DURATION_MINUTES="${1:-120}"
METADATA_INTERVAL_SECONDS="${2:-60}"

cd "$(dirname "$0")/.."

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

if ! is_positive_int "${DURATION_MINUTES}"; then
  echo "Duration minutes must be a positive integer: ${DURATION_MINUTES}" >&2
  exit 2
fi

if ! is_positive_int "${METADATA_INTERVAL_SECONDS}"; then
  echo "Metadata interval seconds must be a positive integer: ${METADATA_INTERVAL_SECONDS}" >&2
  exit 2
fi

log_step() {
  printf '\n[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

log_step "Preflight: gTrade live windows"
uv run sis next-live-window --venue gtrade --symbol QQQ
uv run sis next-live-window --venue gtrade --symbol SPY
uv run sis next-live-window --venue gtrade --symbol XAU

log_step "Collecting gTrade window: duration=${DURATION_MINUTES}min metadata_interval=${METADATA_INTERVAL_SECONDS}s"
bun run gtrade:collect-window -- --duration-minutes "${DURATION_MINUTES}" --metadata-interval-seconds "${METADATA_INTERVAL_SECONDS}"

log_step "Rebuilding quote evidence"
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis diagnose-quotes
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis validate-artifacts --strict

log_step "Live evidence refresh completed"
