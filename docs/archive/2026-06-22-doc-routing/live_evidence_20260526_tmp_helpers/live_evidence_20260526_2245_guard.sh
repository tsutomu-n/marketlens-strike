#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/tn/projects/marketlens-strike"
TARGET_DISPLAY="2026-05-26 22:45:00 JST"
GUARD_DISPLAY="2026-05-26 22:50:00 JST"
DURATION_MINUTES="120"
METADATA_INTERVAL_SECONDS="60"
PRIMARY_RUN_ID="20260526_2245"
BACKUP_RUN_ID="20260526_2245_backup"
PRIMARY_LOG="logs/live_evidence/live_evidence_${PRIMARY_RUN_ID}.log"
BACKUP_LOG="logs/live_evidence/live_evidence_${BACKUP_RUN_ID}.log"
PRIMARY_MANIFEST="logs/live_evidence/manifests/live_evidence_${PRIMARY_RUN_ID}.json"
BACKUP_MANIFEST="logs/live_evidence/manifests/live_evidence_${BACKUP_RUN_ID}.json"
GUARD_LOCK="logs/live_evidence/locks/live_evidence_${PRIMARY_RUN_ID}_guard.lock"

cd "${ROOT}"
mkdir -p "$(dirname "${GUARD_LOCK}")"

exec 9>"${GUARD_LOCK}"
if ! flock -n 9; then
  printf '[%s] another guard is already active\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  exit 0
fi

printf '[%s] guard started\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'primary_run_id=%s\n' "${PRIMARY_RUN_ID}"
printf 'backup_run_id=%s\n' "${BACKUP_RUN_ID}"
printf 'guard_jst=%s\n' "${GUARD_DISPLAY}"

guard_epoch="$(TZ=Asia/Tokyo date -d "${GUARD_DISPLAY% JST}" +%s)"
now_epoch="$(TZ=Asia/Tokyo date +%s)"
wait_seconds=$((guard_epoch - now_epoch))

if (( wait_seconds > 0 )); then
  printf 'wait_seconds=%s\n' "${wait_seconds}"
  sleep "${wait_seconds}"
else
  printf 'wait_seconds=0\n'
fi

printf '[%s] guard checking primary run\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

if [[ -s "${PRIMARY_LOG}" ]] && grep -q "Scheduled live evidence run starting" "${PRIMARY_LOG}"; then
  printf 'primary_status=started_from_log\n'
  exit 0
fi

if [[ -s "${PRIMARY_MANIFEST}" ]]; then
  printf 'primary_status=manifest_exists\n'
  exit 0
fi

printf 'primary_status=missing\n'
printf 'backup_status=starting\n'

{
  printf '\n[%s] Backup live evidence run starting\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  uv run python scripts/run_live_evidence.py \
    --duration-minutes "${DURATION_MINUTES}" \
    --metadata-interval-seconds "${METADATA_INTERVAL_SECONDS}" \
    --run-id "${BACKUP_RUN_ID}" \
    --requested-schedule-jst "${TARGET_DISPLAY}; backup guard ${GUARD_DISPLAY}" \
    --log-path "${BACKUP_LOG}" \
    --manifest-path "${BACKUP_MANIFEST}"
} 2>&1 | tee -a "${BACKUP_LOG}"
