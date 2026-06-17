<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_20:47 JST
-->

# Schema And Artifact Contract

## Current Schema State

Current schemas:

- `strategy_signal.v1.schema.json`: `execution_venue` allows `trade_xyz`, `bitget_demo`
- `trade_candidate.v1.schema.json`: `execution_venue` allows `trade_xyz`, `bitget_demo`
- `paper_intent_preview.v1.schema.json`: `execution_venue` allows `trade_xyz`, `bitget_demo`
- `evaluation_plan.mls.v1.schema.json`: `target_venue` is fixed to `trade_xyz`

Therefore, `schema_enabled=true` in the capability gate only means the
execution-venue artifact schemas accept the venue. It does not mean the venue is
enabled as an `evaluation_plan.mls.v1` `target_venue`. Track that separately as
`strategy_lab_evaluation_plan_enabled`.

## Required Future Widening

Do not widen one schema alone.

If a future slice enables `bitget_futures` or `hyperliquid_perp`, it must update
and test these together:

- `src/sis/venues/ids.py`
- Strategy Lab Pydantic models using `VenueId`
- `strategy_signal.v1.schema.json`
- `trade_candidate.v1.schema.json`
- `paper_intent_preview.v1.schema.json`
- `evaluation_plan.mls.v1.schema.json`
- capability and suitability tests
- paper fee/cost config if paper execution is enabled

## Artifact Requirements

Any future venue-readiness artifact must include:

- `venue_id`
- `venue_family`
- `schema_enabled`
- `strategy_lab_evaluation_plan_enabled`
- `read_only_network_probe`
- `credential_status`
- `external_write_enabled=false`
- `exchange_write_used=false`
- `wallet_used=false`
- `paper_execution_enabled`
- `live_execution_enabled=false`
- `generated_at`
- source command

## Explicit Non-Claims

The following must not be claimed from this design gate:

- Bitget production readiness
- Hyperliquid direct trading readiness
- paper trading readiness for future venues
- live trading readiness
- account readiness
- wallet readiness
- exchange-write readiness
