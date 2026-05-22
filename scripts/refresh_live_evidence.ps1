param(
  [ValidateRange(1, [int]::MaxValue)]
  [int]$DurationMinutes = 120,
  [ValidateRange(1, [int]::MaxValue)]
  [int]$MetadataIntervalSeconds = 60
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host ("[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"), $Message)
}

Push-Location $repoRoot
try {
  Write-Step "Preflight: gTrade live windows"
  uv run sis next-live-window --venue gtrade --symbol QQQ
  uv run sis next-live-window --venue gtrade --symbol SPY
  uv run sis next-live-window --venue gtrade --symbol XAU

  Write-Step "Collecting gTrade window: duration=${DurationMinutes}min metadata_interval=${MetadataIntervalSeconds}s"
  bun run gtrade:collect-window -- --duration-minutes $DurationMinutes --metadata-interval-seconds $MetadataIntervalSeconds

  Write-Step "Rebuilding quote evidence"
  uv run sis log-quotes --venue gtrade --replace
  uv run sis normalize-quotes
  uv run sis build-cost-matrix
  uv run sis build-backtest
  uv run sis diagnose-quotes
  uv run sis check-go-no-go
  uv run sis build-evidence-card
  uv run sis validate-artifacts --strict

  Write-Step "Live evidence refresh completed"
}
finally {
  Pop-Location
}
