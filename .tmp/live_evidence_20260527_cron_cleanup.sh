#!/usr/bin/env bash
set -euo pipefail

TAG="marketlens-live-evidence-20260527-recovery"
tmpfile="$(mktemp)"
trap 'rm -f "${tmpfile}" "${tmpfile}.new"' EXIT

if crontab -l >"${tmpfile}" 2>/dev/null; then
  sed "/${TAG}/d" "${tmpfile}" >"${tmpfile}.new"
  crontab "${tmpfile}.new"
fi
