<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_20:47 JST
-->

# Implementation Tasks

## T1: Add Venue Capability Contract

Add `src/sis/venues/capabilities.py`.

Minimum model:

- `venue_id`
- `venue_family`
- `asset_universe`
- `schema_enabled`
- `strategy_lab_signal_enabled`
- `strategy_lab_evaluation_plan_enabled`
- `paper_candidate_enabled`
- `paper_intent_enabled`
- `read_only_network_enabled`
- `credentialed_read_only_enabled`
- `paper_execution_enabled`
- `live_execution_enabled`
- `requires_credentials`
- `external_api_default_allowed`
- `exchange_write_default_allowed`
- `notes`
- `block_reasons`

Initial values:

- `trade_xyz`: current implemented proxy/read-only surface
- `bitget_demo`: current execution-venue schema-enabled demo fixture, no
  external write, `strategy_lab_evaluation_plan_enabled=false`
- `bitget_futures`: disabled, catalog-only
- `hyperliquid_perp`: disabled, catalog-only

## T2: Add Capability Tests

Add tests that assert:

- current `VenueId` remains `trade_xyz`, `bitget_demo`
- `bitget_futures` and `hyperliquid_perp` are capability-known but
  schema-disabled
- `bitget_demo` remains demo-only and non-writing
- `hyperliquid_perp` does not imply Trade[XYZ] direct trading
- NDX/QQQ family remains paper-path blocked

## T3: Add Docs

Add `docs/venues/bitget_hyperliquid_capability_gate.md`.

The doc must state:

- Bitget demo is not production Bitget.
- Hyperliquid direct perp is not Trade[XYZ].
- `VenueId` widening requires schema and evaluation-plan changes together.
- Live trading remains out of scope.

## T4: Add CLI Read-Only Surface Planning Only

Do not add a network command yet. Define the future commands in docs only:

- `bitget-futures-read-only-smoke`
- `hyperliquid-perp-read-only-smoke`

Both future commands must default to no external write and no order placement.

## T5: Update Handoff

Refresh `.ai_memory/HANDOFF.md` after the plan is added.

The handoff must not claim the design gate is implemented if only plan docs were
created.
