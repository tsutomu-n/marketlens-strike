<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Artifact Contract

## Output Paths

The CLI must write:

- `data/ops/venue_read_only_probe_summary.json`
- `data/reports/venue_read_only_probe.md`

Tests should use a temporary `SIS_DATA_DIR`.

## Summary Schema

Schema file:

- `schemas/venue_read_only_probe_summary.v1.schema.json`

Required top-level fields:

- `schema_version`: const `venue_read_only_probe_summary.v1`
- `generated_at`: string
- `status`: enum `blocked`, `not_configured`, `fixture_only`
- `external_api_used`: const false
- `credentials_used`: const false
- `wallet_used`: const false
- `exchange_write_used`: const false
- `live_order_submitted`: const false
- `venue_count`: integer
- `venues`: array

Required per-venue fields:

- `venue_id`
- `venue_family`
- `asset_universe`
- `capability_known`
- `suitability_known`
- `schema_enabled`
- `strategy_lab_signal_enabled`
- `strategy_lab_evaluation_plan_enabled`
- `paper_candidate_enabled`
- `paper_intent_enabled`
- `read_only_network_enabled`
- `credentialed_read_only_enabled`
- `paper_execution_enabled`
- `live_execution_enabled`
- `read_only_probe_status`
- `read_only_probe_mode`
- `credential_status`
- `external_api_used`
- `credentials_used`
- `exchange_write_used`
- `wallet_used`
- `live_order_submitted`
- `block_reasons`
- `next_action`

## Allowed Values

`read_only_probe_status`:

- `local_capability_only`
- `blocked_by_capability`
- `not_configured`

`read_only_probe_mode`:

- `fixture_only`

`credential_status`:

- `not_required`
- `not_checked`

Do not use `ready`, `approved`, `connected`, `account_ready`, or
`live_ready`.

## Expected Venue Rows

- `trade_xyz`
  - `read_only_probe_status=local_capability_only`
  - `read_only_network_enabled=true`
  - no credentials used
- `bitget_demo`
  - `read_only_probe_status=local_capability_only`
  - `read_only_network_enabled=false`
  - `credential_status=not_checked`
- `bitget_futures`
  - `read_only_probe_status=blocked_by_capability`
  - `schema_enabled=false`
  - `read_only_network_enabled=false`
- `hyperliquid_perp`
  - `read_only_probe_status=blocked_by_capability`
  - `schema_enabled=false`
  - `read_only_network_enabled=false`

## Report Requirements

The Markdown report must include:

- generated timestamp
- top-level status
- one section per venue
- explicit non-claims:
  - no external API used
  - no credentials used
  - no wallet used
  - no exchange write used
  - no live order submitted
- next action for each venue

