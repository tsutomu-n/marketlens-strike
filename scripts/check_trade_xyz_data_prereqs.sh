#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

REQUIRE_ARCHIVE_PREFLIGHT="${SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT:-1}"
REQUIRE_ACCOUNT_FEE="${SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE:-1}"

status_command=(uv run sis trade-xyz-collection-status)

printf 'require_archive_preflight=%s\n' "${REQUIRE_ARCHIVE_PREFLIGHT}"
printf 'require_account_fee=%s\n' "${REQUIRE_ACCOUNT_FEE}"
printf 'account_fee_user_address_configured=%s\n' "$([[ -n "${SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS:-}" ]] && echo true || echo false)"

if [[ "${REQUIRE_ARCHIVE_PREFLIGHT}" == "1" ]]; then
  printf 'archive_preflight_setup_hint=%s\n' 'configure AWS credentials or set SIS_AWS_COMMAND="aws --profile <profile>"'
  uv run sis check-trade-xyz-historical-archive-preflight
  status_command+=(--fail-on-archive-preflight)
fi

if [[ "${REQUIRE_ACCOUNT_FEE}" == "1" ]]; then
  if [[ -z "${SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS:-}" ]]; then
    printf 'account_fee_setup_hint=%s\n' 'export SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...'
  else
    printf 'account_fee_collection=enabled\n'
    printf 'account_fee_command=%s\n' 'uv run sis collect-trade-xyz-account-fee --user-address <redacted>'
    uv run sis collect-trade-xyz-account-fee --user-address "${SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS}"
  fi
  status_command+=(--fail-on-account-fee-missing)
fi

printf 'after_prereqs_command=%s\n' 'scripts/collect_trade_xyz_data_until_ready.sh'
printf 'continue_quote_collection_without_archive_or_account_fee_command=%s\n' 'SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0 SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0 scripts/collect_trade_xyz_data_until_ready.sh'
printf 'final_readiness_command=%s\n' 'uv run sis trade-xyz-collection-status --strict --fail-on-not-ready'

printf 'status_command='
printf '%q ' "${status_command[@]}"
printf '\n'
"${status_command[@]}"
