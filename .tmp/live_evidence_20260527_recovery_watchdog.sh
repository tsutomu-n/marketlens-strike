#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/tn/projects/marketlens-strike"
CHECK_LABEL="${1:?check label is required}"
DURATION_MINUTES="${2:?duration minutes is required}"
METADATA_INTERVAL_SECONDS="${3:-60}"
RUN_ID="20260527_${CHECK_LABEL}_recovery"
TARGET_DISPLAY="2026-05-27 ${CHECK_LABEL:0:2}:${CHECK_LABEL:2:2}:00 JST recovery watchdog"
LOG_PATH="logs/live_evidence/live_evidence_${RUN_ID}.log"
MANIFEST_PATH="logs/live_evidence/manifests/live_evidence_${RUN_ID}.json"
WATCHDOG_LOG="logs/live_evidence/live_evidence_${RUN_ID}_watchdog.out"
WATCHDOG_LOCK="logs/live_evidence/locks/live_evidence_${RUN_ID}_watchdog.lock"

cd "${ROOT}"
mkdir -p logs/live_evidence/locks logs/live_evidence/manifests

exec 9>"${WATCHDOG_LOCK}"
if ! flock -n 9; then
  printf '[%s] watchdog already active: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${RUN_ID}" | tee -a "${WATCHDOG_LOG}"
  exit 0
fi

{
  printf '[%s] recovery watchdog checking: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${RUN_ID}"
  printf 'target_display=%s\n' "${TARGET_DISPLAY}"
  printf 'duration_minutes=%s\n' "${DURATION_MINUTES}"
  printf 'metadata_interval_seconds=%s\n' "${METADATA_INTERVAL_SECONDS}"

  if pgrep -af "scripts/run_live_evidence.py|sis.live_evidence_runner" >/dev/null; then
    printf 'active_runner=present\n'
    exit 0
  fi
  printf 'active_runner=absent\n'

  if uv run python - <<'PY'
import json
from pathlib import Path

success_statuses = {"completed", "completed_with_retries"}
paths = [
    Path("logs/live_evidence/manifests/live_evidence_20260526_2245.json"),
    Path("logs/live_evidence/manifests/live_evidence_20260526_2245_backup.json"),
    Path("logs/live_evidence/manifests/live_evidence_20260527_0110_recovery.json"),
    Path("logs/live_evidence/manifests/live_evidence_20260527_0300_recovery.json"),
]

for path in paths:
    if not path.exists():
        continue
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = payload.get("status")
    row_counts = payload.get("row_counts") or {}
    rows = max(
        int(row_counts.get("raw_quotes") or 0),
        int(row_counts.get("pricing_rows_delta") or 0),
        int(row_counts.get("sidecar_pricing") or 0),
    )
    print(f"manifest={path} status={status} rows={rows}")
    if status in success_statuses and rows > 0:
        raise SystemExit(0)

raise SystemExit(1)
PY
  then
    printf 'recovery_needed=false\n'
    exit 0
  fi

  printf 'recovery_needed=true\n'
  printf '[%s] recovery run starting\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  uv run python scripts/run_live_evidence.py \
    --duration-minutes "${DURATION_MINUTES}" \
    --metadata-interval-seconds "${METADATA_INTERVAL_SECONDS}" \
    --run-id "${RUN_ID}" \
    --requested-schedule-jst "${TARGET_DISPLAY}" \
    --log-path "${LOG_PATH}" \
    --manifest-path "${MANIFEST_PATH}"
} 2>&1 | tee -a "${WATCHDOG_LOG}"
