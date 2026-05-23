#!/usr/bin/env bash
set -euo pipefail

TARGET_TIME_JST="${1:-22:45}"
DURATION_MINUTES="${2:-120}"
METADATA_INTERVAL_SECONDS="${3:-60}"
LOG_DIR="${4:-logs/live_evidence}"

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

now_epoch="$(TZ=Asia/Tokyo date +%s)"

if [[ "${TARGET_TIME_JST}" =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]]; then
  today_jst="$(TZ=Asia/Tokyo date +%F)"
  target_epoch="$(TZ=Asia/Tokyo date -d "${today_jst} ${TARGET_TIME_JST}:00" +%s)"
  if (( target_epoch <= now_epoch )); then
    target_epoch=$((target_epoch + 86400))
  fi
elif [[ "${TARGET_TIME_JST}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}[T\ ][0-9]{2}:[0-9]{2}(:[0-9]{2})?$ ]]; then
  normalized_target="${TARGET_TIME_JST/T/ }"
  target_epoch="$(TZ=Asia/Tokyo date -d "${normalized_target}" +%s)"
  if (( target_epoch <= now_epoch )); then
    echo "Absolute JST target must be in the future: ${TARGET_TIME_JST}" >&2
    exit 2
  fi
else
  echo "Target time must be HH:MM or YYYY-MM-DDTHH:MM in JST: ${TARGET_TIME_JST}" >&2
  exit 2
fi

target_stamp="$(TZ=Asia/Tokyo date -d "@${target_epoch}" '+%Y%m%d_%H%M')"
target_display="$(TZ=Asia/Tokyo date -d "@${target_epoch}" '+%Y-%m-%d %H:%M:%S JST')"
wait_seconds=$((target_epoch - now_epoch))

mkdir -p "${LOG_DIR}"
log_path="${LOG_DIR}/live_evidence_${target_stamp}.log"

printf 'target_jst=%s\n' "${target_display}"
printf 'wait_seconds=%s\n' "${wait_seconds}"
printf 'duration_minutes=%s\n' "${DURATION_MINUTES}"
printf 'metadata_interval_seconds=%s\n' "${METADATA_INTERVAL_SECONDS}"
printf 'log_path=%s\n' "${log_path}"

if [[ "${SCHEDULE_LIVE_EVIDENCE_DRY_RUN:-0}" == "1" ]]; then
  exit 0
fi

sleep "${wait_seconds}"

{
  printf '\n[%s] Scheduled live evidence run starting\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  bash scripts/refresh_live_evidence.sh "${DURATION_MINUTES}" "${METADATA_INTERVAL_SECONDS}"
} 2>&1 | tee -a "${log_path}"
