<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_20:47 JST
-->

# Bitget / Hyperliquid Capability Gate

This document records the implemented fixture-first capability gate for future
Bitget and Hyperliquid support.

The code source of truth is `src/sis/venues/capabilities.py`.

## Current Decision

- `VenueId` remains `trade_xyz`, `bitget_demo`.
- `strategy_signal`, `trade_candidate`, and `paper_intent_preview` execution
  venue schemas remain `trade_xyz`, `bitget_demo`.
- `evaluation_plan.mls.v1` remains `target_venue=trade_xyz`; `bitget_demo` is
  not enabled for evaluation-plan target venue.
- `bitget_futures` is capability-known but schema-disabled.
- `hyperliquid_perp` is capability-known but schema-disabled.
- `bitget_demo` remains demo/local fixture and paper-only. It is not production
  Bitget futures.
- `hyperliquid_perp` is future direct Hyperliquid perp. It is not Trade[XYZ].
- Live execution is disabled for every venue in this capability gate.

## Current Capability Matrix

| Venue | Execution-venue schema | Evaluation-plan target | Paper enabled | Read-only network enabled | Live enabled | Meaning |
|---|---:|---:|---:|---:|---:|---|
| `trade_xyz` | yes | yes | yes | yes | no | implemented proxy/research/read-only surface |
| `bitget_demo` | yes | no | yes | no | no | demo fixture surface; local credentials only do not prove network readiness |
| `bitget_futures` | no | no | no | no | no | future Bitget futures venue |
| `hyperliquid_perp` | no | no | no | no | no | future direct Hyperliquid perp venue |

## Why This Gate Exists

Adding a venue to `VENUE_SUITABILITY_CATALOG` does not mean Strategy Lab schemas
accept it. Widening only `VenueId` is also insufficient because
`schemas/evaluation_plan.mls.v1.schema.json` still has `target_venue` fixed to
`trade_xyz`.

The capability gate makes those states explicit:

- known but schema-disabled
- execution-venue schema enabled but evaluation-plan disabled
- schema-enabled but network-disabled
- paper-enabled but live-disabled
- default external API disabled
- exchange write disabled

## Non-Claims

Do not infer any of these from this gate:

- Bitget production readiness
- Hyperliquid direct trading readiness
- credentialed account readiness
- paper readiness for future venues
- wallet readiness
- exchange-write readiness
- live trading readiness

## Future Widening Requirements

If a future slice enables `bitget_futures` or `hyperliquid_perp`, it must update
these together:

- `src/sis/venues/ids.py`
- Strategy Lab Pydantic models that use `VenueId`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- venue capability tests
- venue suitability tests
- paper fee/cost config, only if paper execution is enabled

## Stop Conditions

Stop if a change:

- treats `bitget_demo` as production Bitget
- treats Trade[XYZ] as generic `hyperliquid_perp`
- widens `VenueId` without schema and evaluation-plan updates
- enables live execution
- calls external APIs in default tests
- uses credentials from tracked files
- submits, cancels, or closes real orders
