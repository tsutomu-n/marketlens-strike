param(
  [Parameter(Position = 0)]
  [ValidateRange(1, 2147483647)]
  [int]$DurationMinutes = 120,

  [Parameter(Position = 1)]
  [ValidateRange(1, 2147483647)]
  [int]$MetadataIntervalSeconds = 60,

  [switch]$DryRun,
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataDir = if ($env:SIS_DATA_DIR) { $env:SIS_DATA_DIR } else { "data" }
$todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$metadataPath = Join-Path $dataDir "raw/sidecar/gtrade/$todayUtc.jsonl"
$pricingPath = Join-Path $dataDir "raw/sidecar/gtrade-pricing/$todayUtc.jsonl"
$quotePath = Join-Path $dataDir "raw/quotes/gtrade/$todayUtc.jsonl"
$normalizedPath = Join-Path $dataDir "normalized/quotes.parquet"
$costMatrixPath = Join-Path $dataDir "research/venue_cost_matrix.csv"
$backtestMetricsPath = Join-Path $dataDir "research/backtest_metrics.json"
$goNoGoPath = Join-Path $dataDir "research/go_no_go_report.md"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host ("[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"), $Message)
}

function Assert-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

function Get-RowCount {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    return 0
  }
  return (Get-Content -Path $Path | Measure-Object -Line).Lines
}

function ConvertTo-KeyValueMap {
  param([string[]]$Lines)
  $map = @{}
  foreach ($line in $Lines) {
    if ($line -match "^[^=]+=") {
      $parts = $line -split "=", 2
      $map[$parts[0]] = $parts[1]
    }
  }
  return $map
}

function Invoke-NextLiveWindow {
  param([string]$Symbol)
  Write-Step "Preflight: next live window $Symbol"
  $output = uv run sis next-live-window --venue gtrade --symbol $Symbol
  $output | ForEach-Object { Write-Host $_ }
  $map = ConvertTo-KeyValueMap $output
  if (-not $map.ContainsKey("now_jst") -or -not $map.ContainsKey("recommended_start_jst") -or -not $map.ContainsKey("recommended_end_jst")) {
    throw "Failed to parse next-live-window output for $Symbol"
  }
  $now = [datetimeoffset]::Parse($map["now_jst"])
  $start = [datetimeoffset]::Parse($map["recommended_start_jst"])
  $end = [datetimeoffset]::Parse($map["recommended_end_jst"])
  return [pscustomobject]@{
    Symbol = $Symbol
    Output = $output
    OutsideWindow = ($now -lt $start -or $now -gt $end)
  }
}

function Get-LatestEvidencePath {
  $evidenceDir = Join-Path $dataDir "evidence"
  if (-not (Test-Path $evidenceDir)) {
    return ""
  }
  $files = Get-ChildItem -Path $evidenceDir -Filter "evidence_card_*.json" | Sort-Object Name
  if (-not $files) {
    return ""
  }
  return $files[-1].FullName
}

$expectedSnapshots = [Math]::Floor(($DurationMinutes * 60) / $MetadataIntervalSeconds)
if ($expectedSnapshots -lt 1) {
  $expectedSnapshots = 1
}
$minMetadataRows = [Math]::Ceiling($expectedSnapshots * 0.8)

Push-Location $repoRoot
try {
  Write-Step "Live evidence refresh configuration"
  Write-Host ("mode={0}" -f ($(if ($DryRun) { "dry-run" } else { "execute" })))
  Write-Host ("duration_minutes={0}" -f $DurationMinutes)
  Write-Host ("metadata_interval_seconds={0}" -f $MetadataIntervalSeconds)
  Write-Host ("force={0}" -f $Force.IsPresent.ToString().ToLowerInvariant())
  Write-Host ("data_dir={0}" -f $dataDir)

  Write-Step "Preflight: command availability"
  Assert-Command uv
  Assert-Command bun

  $windows = @()
  foreach ($symbol in @("QQQ", "SPY", "XAU")) {
    $windows += Invoke-NextLiveWindow -Symbol $symbol
  }

  if ($DryRun) {
    Write-Step "Dry run complete"
    Write-Host "No data collection performed."
    exit 0
  }

  $outside = $windows | Where-Object { $_.OutsideWindow }
  if ($outside) {
    $outsideSymbols = ($outside | ForEach-Object { $_.Symbol }) -join " "
    if (-not $Force) {
      Write-Error "Current time is outside recommended gTrade live window for: $outsideSymbols`nUse -Force to collect anyway."
      exit 2
    }
    Write-Step "Continuing outside recommended window because -Force was set"
    Write-Host ("outside_window_symbols={0}" -f $outsideSymbols)
  }

  $metadataRowsBefore = Get-RowCount $metadataPath
  $pricingRowsBefore = Get-RowCount $pricingPath

  Write-Step "Collecting gTrade window: duration=$DurationMinutes min metadata_interval=$MetadataIntervalSeconds s"
  bun run gtrade:collect-window -- --duration-minutes $DurationMinutes --metadata-interval-seconds $MetadataIntervalSeconds

  $metadataRowsAfter = Get-RowCount $metadataPath
  $pricingRowsAfter = Get-RowCount $pricingPath
  $metadataRowsDelta = $metadataRowsAfter - $metadataRowsBefore
  $pricingRowsDelta = $pricingRowsAfter - $pricingRowsBefore

  Write-Step "Checking collected sidecar rows"
  Write-Host ("metadata_path={0}" -f $metadataPath)
  Write-Host ("metadata_rows_before={0}" -f $metadataRowsBefore)
  Write-Host ("metadata_rows_after={0}" -f $metadataRowsAfter)
  Write-Host ("metadata_rows_delta={0}" -f $metadataRowsDelta)
  Write-Host ("metadata_rows_required={0}" -f $minMetadataRows)
  Write-Host ("pricing_path={0}" -f $pricingPath)
  Write-Host ("pricing_rows_before={0}" -f $pricingRowsBefore)
  Write-Host ("pricing_rows_after={0}" -f $pricingRowsAfter)
  Write-Host ("pricing_rows_delta={0}" -f $pricingRowsDelta)

  if ($metadataRowsDelta -lt $minMetadataRows) {
    throw "Insufficient gTrade metadata rows. Expected at least $minMetadataRows new rows, got $metadataRowsDelta."
  }
  if ($pricingRowsDelta -le 0) {
    throw "Insufficient gTrade pricing rows. Expected more than 0 new rows, got $pricingRowsDelta."
  }

  Write-Step "Rebuilding quote evidence"
  uv run sis log-quotes --venue gtrade --replace
  $quoteRows = Get-RowCount $quotePath
  Write-Host ("quote_path={0}" -f $quotePath)
  Write-Host ("quote_rows={0}" -f $quoteRows)
  if ($quoteRows -le 0) {
    throw "Insufficient gTrade quote rows. Expected more than 0 rows, got $quoteRows."
  }

  uv run sis normalize-quotes
  uv run sis build-cost-matrix

  $diagOutputs = @{}
  foreach ($symbol in @("QQQ", "SPY", "XAU")) {
    Write-Step "Diagnostics: $symbol"
    $diagOutput = uv run sis diagnose-quotes --venue gtrade --symbol $symbol
    $diagOutput | ForEach-Object { Write-Host $_ }
    $diagOutputs[$symbol] = ConvertTo-KeyValueMap $diagOutput
  }

  uv run sis build-backtest

  Write-Step "Go/No-Go"
  $goNoGoOutput = uv run sis check-go-no-go
  $goNoGoOutput | ForEach-Object { Write-Host $_ }

  uv run sis build-evidence-card
  uv run sis validate-artifacts --strict

  Write-Step "Live Evidence Refresh Summary"
  Write-Host ("quotes={0}" -f $quotePath)
  Write-Host ("normalized={0}" -f $normalizedPath)
  Write-Host ("cost_matrix={0}" -f $costMatrixPath)
  Write-Host ("backtest_metrics={0}" -f $backtestMetricsPath)
  Write-Host ("go_no_go={0}" -f $goNoGoPath)
  Write-Host ("evidence={0}" -f (Get-LatestEvidencePath))
  Write-Host ("decision={0}" -f (@($goNoGoOutput)[-1]))
  Write-Host ("force={0}" -f $Force.IsPresent.ToString().ToLowerInvariant())

  foreach ($symbol in @("QQQ", "SPY", "XAU")) {
    $diag = $diagOutputs[$symbol]
    Write-Host ("{0} stale_rate={1} tradable_rate={2} missing_mark_price_rate={3}" -f `
      $symbol, `
      $diag["stale_rate"], `
      $diag["tradable_rate"], `
      $diag["missing_mark_price_rate"])
  }

  Write-Step "Live evidence refresh completed"
}
finally {
  Pop-Location
}
