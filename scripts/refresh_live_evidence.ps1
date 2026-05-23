param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ArgsList
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
  & uv run python scripts/run_live_evidence.py @ArgsList
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
