#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

POLL_SECONDS="${SIS_TRADE_XYZ_UNTIL_READY_POLL_SECONDS:-300}"
MAX_CYCLES="${SIS_TRADE_XYZ_UNTIL_READY_MAX_CYCLES:-0}"
LOG_DIR="${SIS_TRADE_XYZ_UNTIL_READY_LOG_DIR:-logs/trade_xyz_data_cycle}"
LOCK_DIR="${SIS_TRADE_XYZ_UNTIL_READY_LOCK_DIR:-.tmp/trade_xyz_data_until_ready.lock}"
STALE_AFTER_MINUTES="${SIS_TRADE_XYZ_UNTIL_READY_STALE_AFTER_MINUTES:-180}"
FAIL_ON_RUNNING_STALE="${SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_RUNNING_STALE:-1}"
FAIL_ON_LOCK_STALE="${SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_LOCK_STALE:-1}"
ALLOW_KNOWN_GAPS="${SIS_TRADE_XYZ_UNTIL_READY_ALLOW_KNOWN_GAPS:-0}"
REQUIRE_ARCHIVE_PREFLIGHT="${SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT:-1}"
REQUIRE_ACCOUNT_FEE="${SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE:-1}"

is_nonnegative_int() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

if ! is_positive_int "${POLL_SECONDS}"; then
  echo "SIS_TRADE_XYZ_UNTIL_READY_POLL_SECONDS must be a positive integer: ${POLL_SECONDS}" >&2
  exit 2
fi

if ! is_nonnegative_int "${MAX_CYCLES}"; then
  echo "SIS_TRADE_XYZ_UNTIL_READY_MAX_CYCLES must be a non-negative integer: ${MAX_CYCLES}" >&2
  exit 2
fi

if ! is_positive_int "${STALE_AFTER_MINUTES}"; then
  echo "SIS_TRADE_XYZ_UNTIL_READY_STALE_AFTER_MINUTES must be a positive integer: ${STALE_AFTER_MINUTES}" >&2
  exit 2
fi

mkdir -p "${LOG_DIR}"
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
        echo "Trade[XYZ] until-ready supervisor lock exists and could not be recovered: ${LOCK_DIR}" >&2
        exit 3
      fi
    else
      echo "Trade[XYZ] until-ready supervisor is already running or stale lock exists: ${LOCK_DIR}" >&2
      echo "If no supervisor process is running, remove the lock directory manually after checking logs." >&2
      exit 3
    fi
  else
    # Recover only an empty stale lock directory. Non-empty locks require manual inspection.
    rmdir "${LOCK_DIR}" 2>/dev/null || true
    if mkdir "${LOCK_DIR}" 2>/dev/null; then
      :
    else
      echo "Trade[XYZ] until-ready supervisor is already running or stale lock exists: ${LOCK_DIR}" >&2
      echo "If no supervisor process is running, remove the lock directory manually after checking logs." >&2
      exit 3
    fi
  fi
fi
printf '%s\n' "$$" > "${LOCK_DIR}/pid"
if [[ ! -f "${LOCK_DIR}/pid" ]]; then
  echo "Trade[XYZ] until-ready supervisor is already running or stale lock exists: ${LOCK_DIR}" >&2
  echo "If no supervisor process is running, remove the lock directory manually after checking logs." >&2
  exit 3
fi
trap 'rm -f "${LOCK_DIR}/pid" 2>/dev/null || true; rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT

stamp="$(date -u '+%Y%m%d_%H%M%S')"
log_path="${LOG_DIR}/trade_xyz_data_until_ready_${stamp}.log"
cycle_count=0

json_value() {
  uv run python - "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path("data/ops/trade_xyz_collection_status.json")
payload = json.loads(path.read_text(encoding="utf-8"))
value = payload
for part in sys.argv[1].split("."):
    value = value[part]
if isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

{
  printf '[%s] Trade[XYZ] until-ready supervisor starting\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'poll_seconds=%s\n' "${POLL_SECONDS}"
  printf 'max_cycles=%s\n' "${MAX_CYCLES}"
  printf 'stale_after_minutes=%s\n' "${STALE_AFTER_MINUTES}"
  printf 'fail_on_running_stale=%s\n' "${FAIL_ON_RUNNING_STALE}"
  printf 'fail_on_lock_stale=%s\n' "${FAIL_ON_LOCK_STALE}"
  printf 'allow_known_gaps=%s\n' "${ALLOW_KNOWN_GAPS}"
  printf 'require_archive_preflight=%s\n' "${REQUIRE_ARCHIVE_PREFLIGHT}"
  printf 'require_account_fee=%s\n' "${REQUIRE_ACCOUNT_FEE}"
  printf 'log_path=%s\n' "${log_path}"
  printf 'lock_dir=%s\n' "${LOCK_DIR}"

  while true; do
    status_command=(
      uv run sis trade-xyz-collection-status
      --stale-after-minutes "${STALE_AFTER_MINUTES}"
    )
    if [[ "${ALLOW_KNOWN_GAPS}" != "1" ]]; then
      status_command+=(--strict)
    fi
    "${status_command[@]}"
    ready="$(json_value backtest_data_ready)"
    decision="$(json_value decision)"
    collector_running="$(json_value collector_process.running)"
    latest_file_stale="$(json_value latest_file_stale)"
    cycle_lock_stale="$(json_value locks.cycle.stale)"
    supervisor_lock_stale="$(json_value locks.supervisor.stale)"
    printf '[%s] decision=%s backtest_data_ready=%s collector_running=%s latest_file_stale=%s cycle_lock_stale=%s supervisor_lock_stale=%s cycle_count=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      "${decision}" \
      "${ready}" \
      "${collector_running}" \
      "${latest_file_stale}" \
      "${cycle_lock_stale}" \
      "${supervisor_lock_stale}" \
      "${cycle_count}"

    if [[ "${collector_running}" != "true" ]]; then
      prerequisite_status_command=(
        uv run sis trade-xyz-collection-status
        --stale-after-minutes "${STALE_AFTER_MINUTES}"
      )
      if [[ "${ALLOW_KNOWN_GAPS}" != "1" ]]; then
        prerequisite_status_command+=(--strict)
      fi
      if [[ "${REQUIRE_ARCHIVE_PREFLIGHT}" == "1" ]]; then
        prerequisite_status_command+=(--fail-on-archive-preflight)
      fi
      if [[ "${REQUIRE_ACCOUNT_FEE}" == "1" ]]; then
        prerequisite_status_command+=(--fail-on-account-fee-missing)
      fi
      "${prerequisite_status_command[@]}"
    else
      if [[ "${REQUIRE_ARCHIVE_PREFLIGHT}" == "1" || "${REQUIRE_ACCOUNT_FEE}" == "1" ]]; then
        printf '[%s] collector is running; external prerequisite failures are reported but do not stop organic quote collection\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      fi
    fi

    if [[ "${FAIL_ON_LOCK_STALE}" == "1" && "${supervisor_lock_stale}" == "true" ]]; then
      printf '[%s] supervisor lock is stale; manual inspection required\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      exit 6
    fi

    if [[ "${FAIL_ON_LOCK_STALE}" == "1" && "${collector_running}" == "true" && "${cycle_lock_stale}" == "true" ]]; then
      printf '[%s] collector is running but cycle lock is stale; manual inspection required\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      exit 6
    fi

    if [[ "${FAIL_ON_RUNNING_STALE}" == "1" && "${collector_running}" == "true" && "${latest_file_stale}" == "true" ]]; then
      printf '[%s] collector is running but latest raw quote file is stale\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      exit 5
    fi

    if [[ "${ready}" == "true" ]]; then
      printf '[%s] Trade[XYZ] data readiness reached\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      exit 0
    fi

    if [[ "${collector_running}" == "true" ]]; then
      sleep "${POLL_SECONDS}"
      continue
    fi

    if (( MAX_CYCLES > 0 && cycle_count >= MAX_CYCLES )); then
      printf '[%s] max cycles reached before readiness\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      exit 4
    fi

    cycle_count=$((cycle_count + 1))
    printf '[%s] starting one Trade[XYZ] data cycle\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS="${ALLOW_KNOWN_GAPS}" \
      scripts/collect_trade_xyz_data_cycle.sh
  done
} 2>&1 | tee -a "${log_path}"
