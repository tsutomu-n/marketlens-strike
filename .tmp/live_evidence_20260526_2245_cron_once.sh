#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/tn/projects/marketlens-strike"
TAG="marketlens-live-evidence-20260526-2245-cron"

cd "${ROOT}"

cleanup_cron() {
  if crontab -l >/tmp/${TAG}.crontab 2>/dev/null; then
    sed "/${TAG}/d" "/tmp/${TAG}.crontab" | crontab -
    rm -f "/tmp/${TAG}.crontab"
  fi
}

if [[ "$(TZ=Asia/Tokyo date +%F)" != "2026-05-26" ]]; then
  cleanup_cron
  exit 0
fi

bash .tmp/live_evidence_20260526_2245_guard.sh

cleanup_cron
