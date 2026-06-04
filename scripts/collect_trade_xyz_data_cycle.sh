#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DURATION_MINUTES="${SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES:-1440}"
INTERVAL_SECONDS="${SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS:-60}"
COLLECTION_CONFIG="${SIS_TRADE_XYZ_COLLECTION_CONFIG:-configs/trade_xyz_data_collection.yaml}"
SYMBOLS="${SIS_TRADE_XYZ_CYCLE_SYMBOLS:-}"
LOG_DIR="${SIS_TRADE_XYZ_CYCLE_LOG_DIR:-logs/trade_xyz_data_cycle}"
DRY_RUN="${SIS_TRADE_XYZ_CYCLE_DRY_RUN:-0}"
LOCK_DIR="${SIS_TRADE_XYZ_CYCLE_LOCK_DIR:-.tmp/trade_xyz_data_cycle.lock}"
ACCOUNT_FEE_USER_ADDRESS="${SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS:-}"
ALLOW_KNOWN_GAPS="${SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS:-0}"
REFRESH_REGISTRY="${SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY:-1}"
REGISTRY_SEED_PATH="${SIS_TRADE_XYZ_CYCLE_REGISTRY_SEED_PATH:-configs/instrument_registry.seed.json}"
COLLECT_SIGNAL_CANDLES="${SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES:-1}"
SIGNAL_CANDLE_INTERVALS="${SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_INTERVALS:-}"
SIGNAL_CANDLE_PERIOD_DAYS="${SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_PERIOD_DAYS:-}"
SIGNAL_CANDLE_MAX_AGE_HOURS="${SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS:-}"
SIGNAL_CANDLE_REQUEST_DELAY_SECONDS="${SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS:-}"

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

if ! is_positive_int "${DURATION_MINUTES}"; then
  echo "SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES must be a positive integer: ${DURATION_MINUTES}" >&2
  exit 2
fi

if ! is_positive_int "${INTERVAL_SECONDS}"; then
  echo "SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS must be a positive integer: ${INTERVAL_SECONDS}" >&2
  exit 2
fi

if [[ -n "${SIGNAL_CANDLE_PERIOD_DAYS}" ]] && ! is_positive_int "${SIGNAL_CANDLE_PERIOD_DAYS}"; then
  echo "SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_PERIOD_DAYS must be a positive integer: ${SIGNAL_CANDLE_PERIOD_DAYS}" >&2
  exit 2
fi

if [[ -n "${SIGNAL_CANDLE_MAX_AGE_HOURS}" ]] && ! is_positive_int "${SIGNAL_CANDLE_MAX_AGE_HOURS}"; then
  echo "SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS must be a positive integer: ${SIGNAL_CANDLE_MAX_AGE_HOURS}" >&2
  exit 2
fi

if [[ -n "${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS}" ]] && ! [[ "${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS}" =~ ^([1-9][0-9]*|0)(\.[0-9]+)?$ ]]; then
  echo "SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS must be a non-negative number: ${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS}" >&2
  exit 2
fi

if (( DURATION_MINUTES * 60 < INTERVAL_SECONDS )); then
  echo "duration minutes * 60 must be >= interval seconds" >&2
  exit 2
fi

stamp="$(date -u '+%Y%m%d_%H%M%S')"
mkdir -p "${LOG_DIR}"
log_path="${LOG_DIR}/trade_xyz_data_cycle_${stamp}.log"
mkdir -p "$(dirname "${LOCK_DIR}")"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  if [[ -f "${LOCK_DIR}/pid" ]]; then
    existing_pid="$(cat "${LOCK_DIR}/pid" 2>/dev/null || true)"
    if [[ "${existing_pid}" =~ ^[0-9]+$ ]] && ! kill -0 "${existing_pid}" 2>/dev/null; then
      rm -f "${LOCK_DIR}/pid" 2>/dev/null || true
      rmdir "${LOCK_DIR}" 2>/dev/null || true
      if mkdir "${LOCK_DIR}" 2>/dev/null; then
        :
      else
        echo "Trade[XYZ] data cycle lock exists and could not be recovered: ${LOCK_DIR}" >&2
        exit 3
      fi
    else
      echo "Trade[XYZ] data cycle is already running or stale lock exists: ${LOCK_DIR}" >&2
      echo "If no process is running, remove the lock directory manually after checking logs." >&2
      exit 3
    fi
  else
    # Recover only an empty stale lock directory. Non-empty locks require manual inspection.
    rmdir "${LOCK_DIR}" 2>/dev/null || true
    if mkdir "${LOCK_DIR}" 2>/dev/null; then
      :
    else
      echo "Trade[XYZ] data cycle is already running or stale lock exists: ${LOCK_DIR}" >&2
      echo "If no process is running, remove the lock directory manually after checking logs." >&2
      exit 3
    fi
  fi
fi
printf '%s\n' "$$" > "${LOCK_DIR}/pid"
trap 'rm -f "${LOCK_DIR}/pid" 2>/dev/null || true; rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT

command=(
  uv run sis collect-trade-xyz-data-cycle
  --collection-config "${COLLECTION_CONFIG}"
  --duration-minutes "${DURATION_MINUTES}"
  --interval-seconds "${INTERVAL_SECONDS}"
  --seed-path "${REGISTRY_SEED_PATH}"
)

if [[ -n "${SYMBOLS}" ]]; then
  command+=(--symbols "${SYMBOLS}")
fi

if [[ -n "${SIGNAL_CANDLE_INTERVALS}" ]]; then
  command+=(--signal-candle-intervals "${SIGNAL_CANDLE_INTERVALS}")
fi

if [[ -n "${SIGNAL_CANDLE_PERIOD_DAYS}" ]]; then
  command+=(--signal-candle-period-days "${SIGNAL_CANDLE_PERIOD_DAYS}")
fi

if [[ -n "${SIGNAL_CANDLE_MAX_AGE_HOURS}" ]]; then
  command+=(--signal-candle-max-age-hours "${SIGNAL_CANDLE_MAX_AGE_HOURS}")
fi

if [[ -n "${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS}" ]]; then
  command+=(--signal-candle-request-delay-seconds "${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS}")
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  command+=(--dry-run)
fi

if [[ -n "${ACCOUNT_FEE_USER_ADDRESS}" ]]; then
  command+=(--account-fee-user-address "${ACCOUNT_FEE_USER_ADDRESS}")
fi

if [[ "${ALLOW_KNOWN_GAPS}" != "1" ]]; then
  command+=(--strict)
fi

if [[ "${REFRESH_REGISTRY}" != "1" ]]; then
  command+=(--use-existing-registry)
fi

if [[ "${COLLECT_SIGNAL_CANDLES}" != "1" ]]; then
  command+=(--skip-signal-candles)
fi

printf 'duration_minutes=%s\n' "${DURATION_MINUTES}"
printf 'interval_seconds=%s\n' "${INTERVAL_SECONDS}"
printf 'collection_config=%s\n' "${COLLECTION_CONFIG}"
printf 'symbols=%s\n' "${SYMBOLS:-<collection-config>}"
printf 'log_path=%s\n' "${log_path}"
printf 'dry_run=%s\n' "${DRY_RUN}"
printf 'lock_dir=%s\n' "${LOCK_DIR}"
printf 'account_fee_user_address_provided=%s\n' "$([[ -n "${ACCOUNT_FEE_USER_ADDRESS}" ]] && echo true || echo false)"
printf 'allow_known_gaps=%s\n' "${ALLOW_KNOWN_GAPS}"
printf 'refresh_registry=%s\n' "${REFRESH_REGISTRY}"
printf 'registry_seed_path=%s\n' "${REGISTRY_SEED_PATH}"
printf 'collect_signal_candles=%s\n' "${COLLECT_SIGNAL_CANDLES}"
printf 'signal_candle_intervals=%s\n' "${SIGNAL_CANDLE_INTERVALS:-<collection-config>}"
printf 'signal_candle_period_days=%s\n' "${SIGNAL_CANDLE_PERIOD_DAYS:-<collection-config>}"
printf 'signal_candle_max_age_hours=%s\n' "${SIGNAL_CANDLE_MAX_AGE_HOURS:-<collection-config>}"
printf 'signal_candle_request_delay_seconds=%s\n' "${SIGNAL_CANDLE_REQUEST_DELAY_SECONDS:-<collection-config>}"

{
  printf '[%s] Trade[XYZ] data cycle starting\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'command='
  printf '%q ' "${command[@]}"
  printf '\n'
  "${command[@]}"
  if [[ "${DRY_RUN}" != "1" ]]; then
    uv run sis trade-xyz-collection-status
  fi
  printf '[%s] Trade[XYZ] data cycle finished\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} 2>&1 | tee -a "${log_path}"
