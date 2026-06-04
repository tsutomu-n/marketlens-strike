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
STATE_PATH="${SIS_TRADE_XYZ_UNTIL_READY_STATE_PATH:-data/ops/trade_xyz_until_ready_supervisor_state.json}"

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
mkdir -p "$(dirname "${STATE_PATH}")"
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

json_csv() {
  uv run python - "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path("data/ops/trade_xyz_collection_status.json")
payload = json.loads(path.read_text(encoding="utf-8"))
value = payload
for part in sys.argv[1].split("."):
    value = value[part]
if value is None:
    print("")
elif isinstance(value, list):
    print(",".join(str(item) for item in value))
else:
    print(value)
PY
}

write_state() {
  uv run python - "${STATE_PATH}" "$1" "${log_path}" "${LOCK_DIR}" "${cycle_count}" "${POLL_SECONDS}" "${MAX_CYCLES}" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

state_path = Path(sys.argv[1])
event = sys.argv[2]
log_path = sys.argv[3]
lock_dir = sys.argv[4]
cycle_count = int(sys.argv[5])
poll_seconds = int(sys.argv[6])
max_cycles = int(sys.argv[7])
status_path = Path("data/ops/trade_xyz_collection_status.json")
status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
readiness_requirements = status.get("readiness_requirements") or {}
collector_process = status.get("collector_process") or {}
locks = status.get("locks") or {}
raw_inventory = status.get("raw_quote_inventory") or {}
progress = status.get("progress_since_previous_status") or {}
payload = {
    "schema_version": "trade_xyz_until_ready_supervisor_state.v1",
    "generated_at": datetime.now(UTC).isoformat(),
    "event": event,
    "log_path": log_path,
    "lock_dir": lock_dir,
    "cycle_count": cycle_count,
    "poll_seconds": poll_seconds,
    "max_cycles": max_cycles,
    "status_path": str(status_path),
    "decision": status.get("decision"),
    "backtest_data_ready": status.get("backtest_data_ready"),
    "failing_requirements": readiness_requirements.get("fail") or [],
    "known_gap_requirements": readiness_requirements.get("known_gap") or [],
    "collector_running": collector_process.get("running"),
    "collector_process_count": collector_process.get("process_count"),
    "latest_file_stale": status.get("latest_file_stale"),
    "latest_file_age_seconds": raw_inventory.get("latest_file_age_seconds"),
    "cycle_lock_stale": (locks.get("cycle") or {}).get("stale"),
    "supervisor_lock_stale": (locks.get("supervisor") or {}).get("stale"),
    "progress_status": progress.get("status"),
}
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
  printf 'state_path=%s\n' "${STATE_PATH}"

  while true; do
    status_command=(
      uv run sis trade-xyz-collection-status
      --stale-after-minutes "${STALE_AFTER_MINUTES}"
      --no-refresh-coverage
      --no-refresh-readiness
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
    failing_requirements="$(json_csv readiness_requirements.fail)"
    known_gap_requirements="$(json_csv readiness_requirements.known_gap)"
    write_state "monitor"
    printf '[%s] monitor decision=%s backtest_data_ready=%s collector_running=%s latest_file_stale=%s cycle_lock_stale=%s supervisor_lock_stale=%s failing_requirements=%s known_gap_requirements=%s cycle_count=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      "${decision}" \
      "${ready}" \
      "${collector_running}" \
      "${latest_file_stale}" \
      "${cycle_lock_stale}" \
      "${supervisor_lock_stale}" \
      "${failing_requirements}" \
      "${known_gap_requirements}" \
      "${cycle_count}"

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

    if [[ "${collector_running}" == "true" ]]; then
      if [[ "${REQUIRE_ARCHIVE_PREFLIGHT}" == "1" || "${REQUIRE_ACCOUNT_FEE}" == "1" ]]; then
        printf '[%s] collector is running; external prerequisites do not stop organic quote collection during monitor polling\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      fi
      sleep "${POLL_SECONDS}"
      continue
    fi

    refresh_status_command=(
      uv run sis trade-xyz-collection-status
      --stale-after-minutes "${STALE_AFTER_MINUTES}"
    )
    if [[ "${ALLOW_KNOWN_GAPS}" != "1" ]]; then
      refresh_status_command+=(--strict)
    fi
    "${refresh_status_command[@]}"
    ready="$(json_value backtest_data_ready)"
    decision="$(json_value decision)"
    collector_running="$(json_value collector_process.running)"
    latest_file_stale="$(json_value latest_file_stale)"
    cycle_lock_stale="$(json_value locks.cycle.stale)"
    supervisor_lock_stale="$(json_value locks.supervisor.stale)"
    failing_requirements="$(json_csv readiness_requirements.fail)"
    known_gap_requirements="$(json_csv readiness_requirements.known_gap)"
    write_state "refreshed"
    printf '[%s] refreshed decision=%s backtest_data_ready=%s collector_running=%s latest_file_stale=%s cycle_lock_stale=%s supervisor_lock_stale=%s failing_requirements=%s known_gap_requirements=%s cycle_count=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      "${decision}" \
      "${ready}" \
      "${collector_running}" \
      "${latest_file_stale}" \
      "${cycle_lock_stale}" \
      "${supervisor_lock_stale}" \
      "${failing_requirements}" \
      "${known_gap_requirements}" \
      "${cycle_count}"

    if [[ "${FAIL_ON_LOCK_STALE}" == "1" && "${supervisor_lock_stale}" == "true" ]]; then
      printf '[%s] supervisor lock is stale after refresh; manual inspection required\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      exit 6
    fi

    if [[ "${collector_running}" == "true" ]]; then
      sleep "${POLL_SECONDS}"
      continue
    fi

    if [[ "${ready}" == "true" ]]; then
      printf '[%s] Trade[XYZ] data readiness reached\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      write_state "ready"
      exit 0
    fi

    if [[ "${failing_requirements}" != "quote_coverage" ]]; then
      printf '[%s] refusing to start next cycle because failing_requirements=%s; manual inspection required\n' \
        "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        "${failing_requirements}" >&2
      write_state "blocked_non_quote_failure"
      exit 7
    fi

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

    if (( MAX_CYCLES > 0 && cycle_count >= MAX_CYCLES )); then
      printf '[%s] max cycles reached before readiness\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
      write_state "max_cycles_reached"
      exit 4
    fi

    cycle_count=$((cycle_count + 1))
    printf '[%s] starting one Trade[XYZ] data cycle\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    write_state "starting_cycle"
    SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS="${ALLOW_KNOWN_GAPS}" \
      scripts/collect_trade_xyz_data_cycle.sh
  done
} 2>&1 | tee -a "${log_path}"
