param(
  [int]$DurationMinutes = 120,
  [int]$MetadataIntervalSeconds = 60
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

Push-Location "sidecars/gtrade"
bun run collect:window -- --duration-minutes $DurationMinutes --metadata-interval-seconds $MetadataIntervalSeconds
Pop-Location

uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis diagnose-quotes
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis validate-artifacts --strict

Pop-Location
