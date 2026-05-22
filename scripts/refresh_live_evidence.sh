#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/refresh_live_evidence.sh [duration_minutes] [metadata_interval_seconds] [--dry-run] [--force]
EOF
}

DURATION_MINUTES="120"
METADATA_INTERVAL_SECONDS="60"
DRY_RUN=0
FORCE=0
POSITIONAL=()

while (($#)); do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --force)
      FORCE=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      POSITIONAL+=("$1")
      ;;
  esac
  shift
done

if ((${#POSITIONAL[@]} > 2)); then
  echo "Expected at most 2 positional arguments, got ${#POSITIONAL[@]}" >&2
  usage >&2
  exit 2
fi

if ((${#POSITIONAL[@]} >= 1)); then
  DURATION_MINUTES="${POSITIONAL[0]}"
fi
if ((${#POSITIONAL[@]} == 2)); then
  METADATA_INTERVAL_SECONDS="${POSITIONAL[1]}"
fi

cd "$(dirname "$0")/.."

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

log_step() {
  printf '\n[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

extract_value() {
  local key="$1"
  local content="$2"
  awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1); exit }' <<<"$content"
}

row_count() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo 0
    return
  fi
  awk 'END { print NR + 0 }' "$path"
}

assert_positive_int() {
  local name="$1"
  local value="$2"
  if ! is_positive_int "$value"; then
    echo "${name} must be a positive integer: ${value}" >&2
    exit 2
  fi
}

assert_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Required command not found: ${name}" >&2
    exit 2
  fi
}

assert_positive_int "Duration minutes" "${DURATION_MINUTES}"
assert_positive_int "Metadata interval seconds" "${METADATA_INTERVAL_SECONDS}"

DATA_DIR="${SIS_DATA_DIR:-data}"
TODAY_UTC="$(date -u +%F)"
METADATA_PATH="${DATA_DIR}/raw/sidecar/gtrade/${TODAY_UTC}.jsonl"
PRICING_PATH="${DATA_DIR}/raw/sidecar/gtrade-pricing/${TODAY_UTC}.jsonl"
QUOTE_PATH="${DATA_DIR}/raw/quotes/gtrade/${TODAY_UTC}.jsonl"
COST_MATRIX_PATH="${DATA_DIR}/research/venue_cost_matrix.csv"
GO_NO_GO_PATH="${DATA_DIR}/research/go_no_go_report.md"
NORMALIZED_PATH="${DATA_DIR}/normalized/quotes.parquet"
BACKTEST_METRICS_PATH="${DATA_DIR}/research/backtest_metrics.json"
EXPECTED_SNAPSHOTS=$((DURATION_MINUTES * 60 / METADATA_INTERVAL_SECONDS))
if ((EXPECTED_SNAPSHOTS < 1)); then
  EXPECTED_SNAPSHOTS=1
fi
MIN_METADATA_ROWS=$((((EXPECTED_SNAPSHOTS * 8) + 9) / 10))

MODE="execute"
if ((DRY_RUN == 1)); then
  MODE="dry-run"
fi

log_step "Live evidence refresh configuration"
printf 'mode=%s\n' "${MODE}"
printf 'duration_minutes=%s\n' "${DURATION_MINUTES}"
printf 'metadata_interval_seconds=%s\n' "${METADATA_INTERVAL_SECONDS}"
printf 'force=%s\n' "${FORCE}"
printf 'data_dir=%s\n' "${DATA_DIR}"

log_step "Preflight: command availability"
assert_command uv
assert_command bun

declare -A WINDOW_OUTPUTS
declare -A WINDOW_OUTSIDE
for symbol in QQQ SPY XAU; do
  log_step "Preflight: next live window ${symbol}"
  output="$(uv run sis next-live-window --venue gtrade --symbol "${symbol}")"
  printf '%s\n' "${output}"
  WINDOW_OUTPUTS["${symbol}"]="${output}"

  now_jst="$(extract_value "now_jst" "${output}")"
  recommended_start_jst="$(extract_value "recommended_start_jst" "${output}")"
  recommended_end_jst="$(extract_value "recommended_end_jst" "${output}")"

  if [[ -z "${now_jst}" || -z "${recommended_start_jst}" || -z "${recommended_end_jst}" ]]; then
    echo "Failed to parse next-live-window output for ${symbol}" >&2
    exit 2
  fi

  if [[ "${now_jst}" < "${recommended_start_jst}" || "${now_jst}" > "${recommended_end_jst}" ]]; then
    WINDOW_OUTSIDE["${symbol}"]=1
  else
    WINDOW_OUTSIDE["${symbol}"]=0
  fi
done

if ((DRY_RUN == 1)); then
  log_step "Dry run complete"
  echo "No data collection performed."
  exit 0
fi

outside_symbols=()
for symbol in QQQ SPY XAU; do
  if ((WINDOW_OUTSIDE["${symbol}"] == 1)); then
    outside_symbols+=("${symbol}")
  fi
done

if ((${#outside_symbols[@]} > 0)); then
  if ((FORCE == 0)); then
    printf 'ERROR:\n' >&2
    printf 'Current time is outside recommended gTrade live window for: %s\n' "${outside_symbols[*]}" >&2
    printf 'Use --force to collect anyway.\n' >&2
    exit 2
  fi
  log_step "Continuing outside recommended window because --force was set"
  printf 'outside_window_symbols=%s\n' "${outside_symbols[*]}"
fi

metadata_rows_before="$(row_count "${METADATA_PATH}")"
pricing_rows_before="$(row_count "${PRICING_PATH}")"

log_step "Collecting gTrade window: duration=${DURATION_MINUTES}min metadata_interval=${METADATA_INTERVAL_SECONDS}s"
bun run gtrade:collect-window -- --duration-minutes "${DURATION_MINUTES}" --metadata-interval-seconds "${METADATA_INTERVAL_SECONDS}"

metadata_rows_after="$(row_count "${METADATA_PATH}")"
pricing_rows_after="$(row_count "${PRICING_PATH}")"
metadata_rows_delta=$((metadata_rows_after - metadata_rows_before))
pricing_rows_delta=$((pricing_rows_after - pricing_rows_before))

log_step "Checking collected sidecar rows"
printf 'metadata_path=%s\n' "${METADATA_PATH}"
printf 'metadata_rows_before=%s\n' "${metadata_rows_before}"
printf 'metadata_rows_after=%s\n' "${metadata_rows_after}"
printf 'metadata_rows_delta=%s\n' "${metadata_rows_delta}"
printf 'metadata_rows_required=%s\n' "${MIN_METADATA_ROWS}"
printf 'pricing_path=%s\n' "${PRICING_PATH}"
printf 'pricing_rows_before=%s\n' "${pricing_rows_before}"
printf 'pricing_rows_after=%s\n' "${pricing_rows_after}"
printf 'pricing_rows_delta=%s\n' "${pricing_rows_delta}"

if ((metadata_rows_delta < MIN_METADATA_ROWS)); then
  printf 'ERROR:\n' >&2
  printf 'Insufficient gTrade metadata rows. Expected at least %s new rows, got %s.\n' "${MIN_METADATA_ROWS}" "${metadata_rows_delta}" >&2
  exit 2
fi

if ((pricing_rows_delta <= 0)); then
  printf 'ERROR:\n' >&2
  printf 'Insufficient gTrade pricing rows. Expected > 0 new rows, got %s.\n' "${pricing_rows_delta}" >&2
  exit 2
fi

log_step "Rebuilding quote evidence"
uv run sis log-quotes --venue gtrade --replace

quote_rows="$(row_count "${QUOTE_PATH}")"
printf 'quote_path=%s\n' "${QUOTE_PATH}"
printf 'quote_rows=%s\n' "${quote_rows}"

if ((quote_rows <= 0)); then
  printf 'ERROR:\n' >&2
  printf 'Insufficient gTrade quote rows. Expected > 0 rows, got %s.\n' "${quote_rows}" >&2
  exit 2
fi

uv run sis normalize-quotes
uv run sis build-cost-matrix

declare -A DIAG_OUTPUTS
for symbol in QQQ SPY XAU; do
  log_step "Diagnostics: ${symbol}"
  diag_output="$(uv run sis diagnose-quotes --venue gtrade --symbol "${symbol}")"
  printf '%s\n' "${diag_output}"
  DIAG_OUTPUTS["${symbol}"]="${diag_output}"
done

uv run sis build-backtest

log_step "Go/No-Go"
GO_NO_GO_OUTPUT="$(uv run sis check-go-no-go)"
printf '%s\n' "${GO_NO_GO_OUTPUT}"

uv run sis build-evidence-card
uv run sis validate-artifacts --strict

latest_evidence_path=""
shopt -s nullglob
evidence_files=("${DATA_DIR}"/evidence/evidence_card_*.json)
shopt -u nullglob
if ((${#evidence_files[@]} > 0)); then
  IFS=$'\n' sorted_evidence=($(printf '%s\n' "${evidence_files[@]}" | sort))
  unset IFS
  latest_evidence_path="${sorted_evidence[${#sorted_evidence[@]}-1]}"
fi

decision="$(printf '%s\n' "${GO_NO_GO_OUTPUT}" | tail -n 1)"

log_step "Live Evidence Refresh Summary"
printf 'quotes=%s\n' "${QUOTE_PATH}"
printf 'normalized=%s\n' "${NORMALIZED_PATH}"
printf 'cost_matrix=%s\n' "${COST_MATRIX_PATH}"
printf 'backtest_metrics=%s\n' "${BACKTEST_METRICS_PATH}"
printf 'go_no_go=%s\n' "${GO_NO_GO_PATH}"
printf 'evidence=%s\n' "${latest_evidence_path}"
printf 'decision=%s\n' "${decision}"
printf 'force=%s\n' "${FORCE}"

for symbol in QQQ SPY XAU; do
  diag_output="${DIAG_OUTPUTS[${symbol}]}"
  stale_rate="$(extract_value "stale_rate" "${diag_output}")"
  tradable_rate="$(extract_value "tradable_rate" "${diag_output}")"
  missing_mark_price_rate="$(extract_value "missing_mark_price_rate" "${diag_output}")"
  printf '%s stale_rate=%s tradable_rate=%s missing_mark_price_rate=%s\n' \
    "${symbol}" "${stale_rate}" "${tradable_rate}" "${missing_mark_price_rate}"
done

log_step "Live evidence refresh completed"
