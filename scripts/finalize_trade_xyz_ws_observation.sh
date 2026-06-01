#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PID="${1:-${SIS_TRADE_XYZ_WS_OBSERVATION_PID:-}}"
RAW_WS_ROOT="${SIS_TRADE_XYZ_WS_FINALIZE_RAW_ROOT:-data/raw/ws/trade_xyz}"
SYMBOLS="${SIS_TRADE_XYZ_WS_FINALIZE_SYMBOLS:-SP500,XYZ100,NVDA}"
LOG_PATH="${SIS_TRADE_XYZ_WS_FINALIZE_LOG_PATH:-.tmp/trade_xyz_ws_24h_logs/collect_3symbols_20260601_2205.log}"
RECV_GAP_SECONDS="${SIS_TRADE_XYZ_WS_FINALIZE_RECV_GAP_SECONDS:-60}"
SOURCE_GAP_SECONDS="${SIS_TRADE_XYZ_WS_FINALIZE_SOURCE_GAP_SECONDS:-60}"

if [[ -z "${PID}" ]]; then
  echo "Usage: $0 <completed-observation-pid>" >&2
  echo "Or set SIS_TRADE_XYZ_WS_OBSERVATION_PID." >&2
  exit 2
fi

if ! [[ "${PID}" =~ ^[0-9]+$ ]]; then
  echo "PID must be numeric: ${PID}" >&2
  exit 2
fi

if kill -0 "${PID}" 2>/dev/null; then
  echo "Observation process is still running; refusing to finalize manifests." >&2
  ps -p "${PID}" -o pid,ppid,etime,stat,command >&2 || true
  exit 3
fi

if [[ ! -d "${RAW_WS_ROOT}" ]]; then
  echo "Raw WS root does not exist: ${RAW_WS_ROOT}" >&2
  exit 4
fi

echo "== Observation process =="
ps -p "${PID}" -o pid,ppid,etime,stat,command || true

echo "== Observation log tail =="
if [[ -f "${LOG_PATH}" ]]; then
  tail -n 80 "${LOG_PATH}"
else
  echo "log_path_missing=${LOG_PATH}"
fi

echo "== WS quality =="
uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root "${RAW_WS_ROOT}" \
  --recv-gap-threshold-seconds "${RECV_GAP_SECONDS}" \
  --source-gap-threshold-seconds "${SOURCE_GAP_SECONDS}"

echo "== REST parity =="
uv run sis build-trade-xyz-rest-parity \
  --symbols "${SYMBOLS}" \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book

echo "== Capture manifest =="
jq '{row_count,bytes_written,connection_count,reconnect_count,error_count,heartbeat_sent_count,pong_count,subscription_response_count,raw_paths}' \
  data/manifests/trade_xyz_ws_capture_manifest.json

echo "== Quality manifest =="
jq '{status,row_count,gap_count,source_ts_gap_count,trade_gap_count,trade_source_ts_gap_count,malformed_payload_count,unknown_symbol_count,bbo_bid_ask_inversion_count,duplicate_payload_count,subscription_counts,symbol_counts}' \
  data/manifests/trade_xyz_ws_quality_manifest.json

echo "== REST parity manifest =="
jq '{status,request_error_count,missing_ws_symbols,missing_rest_symbols,mismatched_symbols,known_gap_count}' \
  data/manifests/trade_xyz_rest_parity_manifest.json

echo "== Disk usage =="
du -sh "${RAW_WS_ROOT}"

echo "== Raw WS partitions =="
find "${RAW_WS_ROOT}" -type f -name '*.jsonl' -print | sort
